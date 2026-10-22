"""Canonical evidence JSON streaming; public documents are unchanged."""
import gzip
import hashlib
import json
import os
from pathlib import Path
import tempfile
import zlib

from ._trajectory_store import EvidenceList, TrajectorySpool


def canonical_chunks(value):
    if isinstance(value, dict):
        yield b'{'
        for index, key in enumerate(sorted(value)):
            if index:
                yield b','
            encoded_key = (json.dumps(key, allow_nan=False) if isinstance(key, str)
                           else json.dumps({key: 0}, allow_nan=False,
                                           separators=(',', ':'))[1:-3])
            yield encoded_key.encode('utf-8')
            yield b':'
            yield from canonical_chunks(value[key])
        yield b'}'
    elif isinstance(value, EvidenceList):
        yield b'['
        for index, row in enumerate(value):
            if index:
                yield b','
            yield json.dumps(row, sort_keys=True, separators=(',', ':'),
                             allow_nan=False).encode('utf-8')
        yield b']'
    else:
        yield json.dumps(value, sort_keys=True, separators=(',', ':'),
                         allow_nan=False).encode('utf-8')


def canonical_digest(value, *, newline=False):
    digest = hashlib.sha256()
    for chunk in canonical_chunks(value):
        digest.update(chunk)
    if newline:
        digest.update(b'\n')
    return digest.hexdigest()


def write_primary_atomic(path, primary, *, maximum_bytes, newline=True):
    """Write the conventional deterministic gzip without a full JSON buffer."""
    path = Path(path)
    quarantine_orphan_writes(path)
    descriptor, temporary = tempfile.mkstemp(prefix=f'{path.name}.{os.getpid()}.',
                                            suffix='.tmp', dir=path.parent)
    digest = hashlib.sha256()
    size = 0
    try:
        with os.fdopen(descriptor, 'wb') as stream:
            compressor = zlib.compressobj(6, zlib.DEFLATED, 31)
            for chunk in canonical_chunks(primary):
                digest.update(chunk)
                packed = compressor.compress(chunk)
                size += len(packed)
                if size > maximum_bytes:
                    raise OSError('primary artifact budget exceeded')
                stream.write(packed)
            if newline:
                digest.update(b'\n')
                packed = compressor.compress(b'\n')
                size += len(packed)
                if size > maximum_bytes:
                    raise OSError('primary artifact budget exceeded')
                stream.write(packed)
            packed = compressor.flush()
            size += len(packed)
            if size > maximum_bytes:
                raise OSError('primary artifact budget exceeded')
            stream.write(packed)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        return {'primary_sha256': digest.hexdigest(), 'compressed_bytes': size}
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def quarantine_orphan_writes(path):
    """Preserve dead writers' incomplete files; never infer a valid result.

    Owner liveness must be verifiable. A live or reused PID fails closed;
    different workers must never write the same primary concurrently.
    """
    path = Path(path)
    candidates = list(path.parent.glob(path.name+'.*.tmp'))
    if not candidates:
        return
    try:
        import psutil
    except ImportError as error:
        raise RuntimeError('psutil required to verify orphan evidence writer') from error
    quarantine = path.parent/'_incomplete_evidence'
    if quarantine.is_symlink():
        raise ValueError('unsafe evidence quarantine')
    for candidate in candidates:
        owner = candidate.name[len(path.name)+1:].split('.', 1)[0]
        if candidate.is_symlink() or not owner.isdecimal():
            raise ValueError('unknown evidence temporary owner')
        if psutil.pid_exists(int(owner)):
            raise RuntimeError('evidence temporary has a live or unverifiable owner')
        quarantine.mkdir(exist_ok=True)
        target = quarantine/candidate.name
        if target.exists():
            raise FileExistsError(target)
        os.replace(candidate, target)


def read_primary(path, *, maximum_record_bytes=64 * 1024 * 1024,
                 expected_sha256=None, newline=True):
    """Read standard gzip JSON with only its trajectory moved to a private spool.

    Non-trajectory metadata is bounded separately. Every row uses JSONDecoder;
    incomplete documents/rows and unexpected trailing bytes are rejected.
    """
    import io
    with gzip.open(path, 'rb') as binary, io.TextIOWrapper(binary, encoding='utf-8', newline='') as source:
        reader = _Reader(source, maximum_record_bytes)
        value = reader.object()
        if reader.peek() is not None:
            raise ValueError('trailing primary JSON data')
        observed = reader.raw_digest.hexdigest()
        if expected_sha256 is not None and observed != expected_sha256:
            raise ValueError('primary artifact hash mismatch')
        if canonical_digest(value, newline=newline) != observed:
            raise ValueError('primary artifact is not canonical JSON')
        return value


class _Reader:
    def __init__(self, stream, maximum):
        self.stream, self.maximum = stream, maximum
        self.buffer, self.eof = '', False
        self.raw_digest = hashlib.sha256()
        self.decoder = json.JSONDecoder(parse_constant=self._invalid_constant)

    @staticmethod
    def _invalid_constant(value):
        raise ValueError('nonfinite evidence JSON')

    def more(self):
        chunk = self.stream.read(65536)
        self.raw_digest.update(chunk.encode('utf-8'))
        if not chunk:
            self.eof = True
        self.buffer += chunk

    def peek(self):
        while True:
            self.buffer = self.buffer.lstrip()
            if self.buffer:
                return self.buffer[0]
            if self.eof:
                return None
            self.more()

    def take(self, expected):
        if self.peek() != expected:
            raise ValueError('incomplete or invalid evidence JSON')
        self.buffer = self.buffer[1:]

    def value(self):
        self.peek()
        while True:
            try:
                value, end = self.decoder.raw_decode(self.buffer)
                if end > self.maximum:
                    raise ValueError('oversized evidence value')
                if end == len(self.buffer) and not self.eof:
                    self.more()
                    continue
                if end < len(self.buffer) and self.buffer[end] not in ' \t\r\n,]}:':
                    if not self.eof and self.buffer[end] in 'eE.+-0123456789':
                        self.more()
                        continue
                    raise ValueError('invalid evidence value delimiter')
                self.buffer = self.buffer[end:]
                return value
            except json.JSONDecodeError as error:
                if self.eof or len(self.buffer) >= self.maximum:
                    raise ValueError('incomplete or oversized evidence value') from error
                self.more()

    def object(self):
        self.take('{')
        result = {}
        first = True
        while self.peek() != '}':
            if not first:
                self.take(',')
            key = self.value()
            if not isinstance(key, str) or key in result:
                raise ValueError('invalid or duplicate primary key')
            self.take(':')
            if key == 'trajectory':
                store = TrajectorySpool()
                try:
                    self.take('[')
                    first_row = True
                    while self.peek() != ']':
                        if not first_row:
                            self.take(',')
                        row = self.value()
                        if not isinstance(row, dict):
                            raise ValueError('invalid trajectory row')
                        store.append(row)
                        first_row = False
                    self.take(']')
                    result[key] = store.freeze(normalize=False)
                finally:
                    store.close()
            else:
                result[key] = self.value()
            first = False
        self.take('}')
        return result

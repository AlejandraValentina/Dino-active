"""Private, process-local lossless trajectory spool (not an artifact format).

Only checkpoints/primaries exported by the engine are restart evidence. The
temporary spool is deleted on close, including OS handle cleanup after a crash.
Records use marshal's built-in numeric/container types, never executable pickle.
"""
from array import array
import hashlib
import marshal
import os
import struct
import tempfile
import zlib


class TrajectorySpool:
    def __init__(self, directory=None):
        self.directory = directory
        self._file = tempfile.TemporaryFile(mode='w+b', prefix='dino-trace-', dir=directory)
        self._offsets = array('Q')
        self.failed = False
        self._end = 0

    def __len__(self):
        return len(self._offsets)

    @property
    def storage_bytes(self):
        return self._end

    @property
    def index_bytes(self):
        return self._offsets.buffer_info()[1] * self._offsets.itemsize

    def append(self, row):
        if self.failed:
            raise OSError('trajectory spool is incomplete; restore a valid checkpoint')
        # One record only: no retained state references, no whole-history copy.
        payload = zlib.compress(marshal.dumps(row), level=1)
        header = struct.pack('<Q', len(payload)) + hashlib.sha256(payload).digest()
        try:
            self._file.seek(self._end)
            if self._file.write(header + payload) != len(header) + len(payload):
                raise OSError('short trajectory record write')
            self._offsets.append(self._end)
            self._end += len(header) + len(payload)
        except BaseException:
            self.failed = True
            # Do not guess whether the partial tail can be recovered.
            raise

    def sync(self):
        if self.failed:
            raise OSError('trajectory spool is incomplete')
        try:
            self._file.flush()
            os.fsync(self._file.fileno())
        except BaseException:
            self.failed = True
            raise

    def _read(self, index):
        self._file.seek(self._offsets[index])
        header = self._file.read(40)
        if len(header) != 40:
            raise ValueError('incomplete trajectory record header')
        size = struct.unpack('<Q', header[:8])[0]
        # A damaged length must not request arbitrary memory or another record.
        stop = self._offsets[index + 1] if index + 1 < len(self) else self._end
        if size != stop - self._offsets[index] - 40:
            raise ValueError('invalid trajectory record length')
        payload = self._file.read(size)
        if len(payload) != size or hashlib.sha256(payload).digest() != header[8:]:
            raise ValueError('incomplete or corrupt trajectory record')
        row = marshal.loads(zlib.decompress(payload))
        if not isinstance(row, dict):
            raise ValueError('invalid trajectory record')
        return row

    def __getitem__(self, index):
        if isinstance(index, slice):
            return [self[i] for i in range(*index.indices(len(self)))]
        if index < 0:
            index += len(self)
        if not 0 <= index < len(self):
            raise IndexError(index)
        if self.failed:
            raise OSError('trajectory spool is incomplete')
        try:
            return self._read(index)
        except BaseException:
            self.failed = True
            raise

    def __iter__(self):
        for index in range(len(self)):
            yield self[index]

    def close(self):
        self._file.close()

    def __del__(self):
        if hasattr(self, '_file'):
            self.close()

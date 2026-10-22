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
from copy import deepcopy


class TrajectorySpool:
    def __init__(self, directory=None):
        self.directory = directory
        self._file = tempfile.TemporaryFile(mode='w+b', prefix='dino-trace-', dir=directory)
        self._offsets = array('Q')
        self.failed = False
        self._end = 0
        self._leases = 0
        self._owner_closed = False

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
        self._owner_closed = True
        if not self._leases:
            self._file.close()

    def freeze(self, *, normalize=True):
        self.sync()
        return FrozenTrajectory(self, len(self), normalize=normalize)

    def __del__(self):
        if hasattr(self, '_file'):
            self.close()


class EvidenceList(list):
    """Read-only lazy JSON array. Explicit deepcopy materializes legacy lists.

    Canonical streaming consumers iterate; no placeholder array is allocated.
    Do not use list's storage-level operations on this internal representation.
    """
    def __iter__(self):
        for index in range(len(self)):
            yield self[index]

    def __getitem__(self, index):
        if isinstance(index, slice):
            return EvidenceSlice(self, range(len(self))[index])
        if index < 0:
            index += len(self)
        if not 0 <= index < len(self):
            raise IndexError(index)
        return self._get(index)

    def __deepcopy__(self, memo):
        return [deepcopy(row, memo) for row in self]

    def __eq__(self, other):
        return (isinstance(other, (tuple, list)) and len(self) == len(other)
                and all(a == b for a, b in zip(self, other)))

    def __ne__(self, other):
        return not self == other

    def _immutable(self, *args, **kwargs):
        raise TypeError('sealed evidence is read-only; materialize to edit')

    append = extend = insert = clear = pop = remove = sort = reverse = _immutable
    __setitem__ = __delitem__ = __iadd__ = __imul__ = _immutable


class EvidenceSlice(EvidenceList):
    def __init__(self, parent, indices):
        self.parent, self.indices = parent, indices

    def __len__(self):
        return len(self.indices)

    def _get(self, index):
        return self.parent[self.indices[index]]


class EvidencePrefix(EvidenceList):
    def __init__(self, count, rows):
        self.count, self.rows = count, rows

    def __len__(self):
        return self.count + len(self.rows)

    def _get(self, index):
        return None if index < self.count else self.rows[index-self.count]


def _json_row(value):
    if isinstance(value, (tuple, list)):
        return [_json_row(v) for v in value]
    if isinstance(value, dict):
        return {k: _json_row(v) for k, v in value.items()}
    return value


class FrozenTrajectory(EvidenceList):
    def __init__(self, spool, count, *, normalize=True):
        self.spool, self.count = spool, count
        self.normalize = normalize
        spool._leases += 1

    def __len__(self):
        return self.count

    def _get(self, index):
        # A failed later append must not invalidate a previously fsynced prefix.
        # _read still verifies the committed frame's length and checksum.
        row = self.spool._read(index)
        return _json_row(row) if self.normalize else row

    def __del__(self):
        if hasattr(self, 'spool'):
            self.spool._leases -= 1
            if self.spool._owner_closed and not self.spool._leases:
                self.spool._file.close()

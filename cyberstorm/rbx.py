"""Strict, seek-based reader for the observed GOG 1.1 RBX envelope."""

from dataclasses import dataclass
from pathlib import Path
import re
import struct

MAGIC = b'\x9e\x9a\xa9\x0b'
MAX_RESOURCE_BYTES = 32 * 1024 * 1024


def read_exact(source, size):
    data = source.read(size)
    if len(data) != size:
        raise ValueError('truncated RBX input')
    return data


@dataclass(frozen=True)
class Entry:
    name: str
    offset: int  # RBX length envelope, not embedded resource start.
    size: int

    @property
    def payload_offset(self):
        return self.offset + 4


class Archive:
    """Use as a context manager. Construction reads only the index and lengths.

    The open file must not be modified during use. Reads are bounded within one
    resource; exact, case-sensitive lookup avoids guessing an archive name.
    """

    def __init__(self, path):
        self.path = Path(path)
        self._source = self.path.open('rb')
        try:
            self._parse()
        except BaseException:
            self.close()
            raise

    def _parse(self):
        source = self._source
        source.seek(0, 2)
        self.byte_size = source.tell()
        source.seek(0)
        magic, count = struct.unpack('<4sI', read_exact(source, 8))
        if magic != MAGIC:
            raise ValueError('unsupported RBX signature')
        self.index_end = 8 + count * 16
        if not count or count > 100_000 or self.index_end > self.byte_size:
            raise ValueError('invalid RBX index count')
        index = []
        names = set()
        for _ in range(count):
            raw_name, offset = struct.unpack('<12sI', read_exact(source, 16))
            name_bytes = raw_name.rstrip(b'\0')
            if not re.fullmatch(rb'[A-Za-z0-9_]{1,8}\.[A-Za-z0-9_]{1,3}', name_bytes):
                raise ValueError('unsupported RBX entry name')
            name = name_bytes.decode('ascii')
            if name.upper() in names:
                raise ValueError('duplicate RBX entry name')
            names.add(name.upper())
            if not self.index_end <= offset <= self.byte_size - 4:
                raise ValueError('RBX offset outside payload area')
            index.append((name, offset))
        sizes = {}
        expected = self.index_end
        for name, offset in sorted(index, key=lambda item: item[1]):
            if offset != expected:
                raise ValueError('unsupported gap, overlap, or duplicate RBX offset')
            source.seek(offset)
            size, = struct.unpack('<I', read_exact(source, 4))
            if size > self.byte_size - offset - 4:
                raise ValueError('RBX payload extends beyond file')
            sizes[name] = size
            expected = offset + 4 + size
        if expected != self.byte_size:
            raise ValueError('unsupported trailing RBX data')
        self.entries = tuple(Entry(name, off, sizes[name]) for name, off in index)
        self._by_name = {e.name: e for e in self.entries}

    def lookup(self, name):
        try:
            return self._by_name[name]
        except KeyError:
            raise ValueError(f'RBX resource not found (exact name required): {name}') from None

    def read(self, name, *, offset=0, size=None, limit=MAX_RESOURCE_BYTES):
        entry = self.lookup(name)
        if size is None:
            size = entry.size - offset
        if offset < 0 or size < 0 or offset + size > entry.size:
            raise ValueError('RBX resource slice outside bounds')
        if size > limit:
            raise ValueError('RBX resource read exceeds byte limit')
        self._source.seek(entry.payload_offset + offset)
        return read_exact(self._source, size)

    def close(self):
        self._source.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

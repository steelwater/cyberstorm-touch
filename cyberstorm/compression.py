"""Bounded PKX codecs independently verified against supplied GOG 1.1 data."""

import struct

MAX_OUTPUT = 32 * 1024 * 1024
PKX_MAGIC = b'PKX:' + struct.pack('<II', 0x10011966, 0x9BAEBACF)


class Cursor:
    def __init__(self, data):
        self.data = memoryview(data)
        self.pos = 0

    def take(self, size):
        if size < 0 or self.pos + size > len(self.data):
            raise ValueError(f'truncated compressed input at byte {self.pos}')
        result = self.data[self.pos:self.pos + size]
        self.pos += size
        return result

    def number(self, size=1):
        return int.from_bytes(self.take(size), 'little')


def lz_decode(data, *, limit=MAX_OUTPUT):
    """Method 14: full token groups followed by low-three-bit partial count."""
    c = Cursor(data)
    header = c.number()
    partial = header & 7
    if header < 8:
        groups = c.number(2)
        if groups == 65535:
            groups = c.number(4)
    else:
        groups = (header >> 3) - 1
    # Each full group requires at least nine bytes, irrespective of expansion.
    if groups > (len(data) - c.pos) // 9:
        raise ValueError('LZ group count exceeds input')
    out = bytearray()
    for group in range(groups + bool(partial)):
        flags = c.number()
        tokens = 8 if group < groups else partial
        for bit in range(tokens):
            if flags & (128 >> bit):
                value = c.number(2)
                distance, count = (value >> 4) + 1, (value & 15) + 3
                if distance > len(out):
                    raise ValueError('LZ back-reference precedes output')
                if len(out) + count > limit:
                    raise ValueError('LZ output exceeds byte limit')
                for _ in range(count):
                    out.append(out[-distance])
            else:
                if len(out) >= limit:
                    raise ValueError('LZ output exceeds byte limit')
                out.append(c.number())
    if c.pos != len(data):
        raise ValueError('trailing LZ input')
    return bytes(out)


def rle_decode(data, size):
    """Method 1: literal/run packets and mandatory terminator; exact output."""
    if not 0 <= size <= MAX_OUTPUT:
        raise ValueError('RLE output exceeds byte limit')
    c = Cursor(data)
    out = bytearray()
    while True:
        control = c.number()
        count = control & 127
        if not count:
            break
        if len(out) + count > size:
            raise ValueError('RLE output exceeds declared size')
        if control & 128:
            out.extend(bytes([c.number()]) * count)
        else:
            out.extend(c.take(count))
    if len(out) != size:
        raise ValueError('RLE output does not match declared size')
    if c.pos != len(data):
        raise ValueError('trailing RLE input')
    return bytes(out)


def unwrap(data, *, limit=MAX_OUTPUT):
    if len(data) > MAX_OUTPUT:
        raise ValueError('resource exceeds input byte limit')
    if not data.startswith(b'PKX:'):
        if len(data) > limit:
            raise ValueError('resource exceeds output byte limit')
        return data
    if len(data) < 24:
        raise ValueError('truncated PKX header')
    if data[:12] != PKX_MAGIC:
        raise ValueError('unsupported PKX signature constants')
    method, stored, size = struct.unpack_from('<III', data, 12)
    if stored != len(data) - 24:
        raise ValueError('PKX stored size does not match payload')
    if not 0 < size <= min(limit, MAX_OUTPUT):
        raise ValueError('PKX declared output exceeds byte limit or is empty')
    if method == 14:
        out = lz_decode(data[24:], limit=size)
    elif method == 1:
        out = rle_decode(data[24:], size)
    else:
        raise ValueError(f'unsupported PKX method {method}')
    if len(out) != size:
        raise ValueError('PKX decoded size does not match declaration')
    return out

"""Observed 8-bit FNX glyph inspection, without game text-layout semantics."""

import struct
from .bitmap import Image
from .compression import unwrap


class Font:
    def __init__(self, data):
        self.data = unwrap(data)
        if len(self.data) < 40 or self.data[:4] != b'FNX:':
            raise ValueError('invalid or truncated FNX header')
        (self.format_word, self.unknown8, self.height, self.unknown16,
         self.first, self.count, offsets, widths, bitmap) = struct.unpack_from('<9I', self.data, 4)
        if self.format_word != 0x80000:
            raise ValueError('unsupported FNX format (only observed 8-bit glyphs)')
        if not 0 < self.height <= 256 or not 0 < self.count <= 256 or self.first + self.count > 256:
            raise ValueError('invalid FNX character range or height')
        if offsets != 40 or widths != offsets + self.count * 4 or bitmap != widths + 256:
            raise ValueError('unsupported FNX table layout')
        if bitmap > len(self.data):
            raise ValueError('truncated FNX tables')
        self.widths = self.data[widths:bitmap]
        self.offsets = struct.unpack_from(f'<{self.count}I', self.data, offsets)
        self.bitmap_offset = bitmap
        for i, offset in enumerate(self.offsets):
            width = self.widths[self.first + i]
            if bitmap + offset + width * self.height > len(self.data):
                raise ValueError('FNX glyph extends beyond bitmap data')

    def glyph(self, code):
        if not self.first <= code < self.first + self.count:
            raise ValueError('FNX character outside stored range')
        width = self.widths[code]
        if not width:
            raise ValueError('FNX glyph has zero width')
        start = self.bitmap_offset + self.offsets[code - self.first]
        return Image(width, self.height, self.data[start:start + width * self.height])

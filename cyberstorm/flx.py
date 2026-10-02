"""Narrow FLX frame/chunk inspection, supporting observed types 4/100/102/104.

Frames accumulate on a caller-selected zero baseline. Timing and game compositing
are deliberately not inferred from the stored fields.
"""

import struct
from .bitmap import Image
from .compression import Cursor, MAX_OUTPUT, lz_decode, unwrap


def apply_runs(data, pixels):
    c = Cursor(data)
    position = 0
    while True:
        control = c.number()
        value = None
        literal = False
        if 0 < control < 128:
            count, literal = control, True
        elif control == 0:
            count, value = c.number(), c.number()
        elif control == 128:
            word = c.number(2)
            if word == 0:
                break
            if word < 0x8000:
                count = word
            elif word < 0xC000:
                count, literal = word - 0x8000, True
            else:
                count, value = word - 0xC000, c.number()
        else:
            count = control & 127
        if position + count > len(pixels):
            raise ValueError('FLX run exceeds frame bounds')
        if literal:
            pixels[position:position + count] = c.take(count)
        elif value is not None:
            pixels[position:position + count] = bytes([value]) * count
        position += count
    if c.pos != len(data):
        raise ValueError('trailing FLX run data')


class Animation:
    def __init__(self, data):
        self.data = unwrap(data)
        if len(self.data) < 128:
            raise ValueError('truncated FLX header')
        size, magic, self.count, self.width, self.height, depth, self.flags = struct.unpack_from('<I6H', self.data)
        if size != len(self.data):
            raise ValueError('FLX declared size mismatch')
        if magic != 0xAF20 or depth != 8:
            raise ValueError('unsupported FLX signature or depth')
        if not self.count or not self.width or not self.height or self.width * self.height > MAX_OUTPUT:
            raise ValueError('invalid FLX count or dimensions')
        self.speed_word, = struct.unpack_from('<I', self.data, 16)
        self.offset_words = struct.unpack_from('<II', self.data, 80)
        self.frames = []
        at = 128
        while at < len(self.data):
            if len(self.data) - at < 16:
                raise ValueError('truncated FLX frame header')
            size, magic, count = struct.unpack_from('<IHH', self.data, at)
            end = at + size
            if size < 16 or end > len(self.data) or magic != 0xF1FA:
                raise ValueError('invalid or unsupported FLX frame')
            if any(self.data[at + 8:at + 16]):
                raise ValueError('unsupported FLX frame header fields')
            chunks = []
            pos = at + 16
            for _ in range(count):
                if pos + 6 > end:
                    raise ValueError('truncated FLX chunk header')
                length, kind = struct.unpack_from('<IH', self.data, pos)
                if length < 6 or pos + length > end:
                    raise ValueError('FLX chunk outside frame bounds')
                chunks.append((kind, pos + 6, pos + length))
                pos += length
            if pos != end:
                raise ValueError('trailing FLX frame data')
            self.frames.append(tuple(chunks))
            at = end
        if len(self.frames) not in (self.count, self.count + 1):
            raise ValueError('FLX stored frame count mismatch')

    def decode(self, palette):
        """Yield stored-order indexed frames and palette snapshots; omit extra frame."""
        if len(palette) != 256:
            raise ValueError('FLX requires 256 baseline colors')
        colors = list(palette)
        pixels = bytearray(self.width * self.height)
        for chunks in self.frames[:self.count]:
            for kind, start, end in chunks:
                data = self.data[start:end]
                if kind == 4:
                    c = Cursor(data)
                    count = c.number(2)
                    index = 0
                    for _ in range(count):
                        index += c.number()
                        length = c.number() or 256
                        if index + length > 256:
                            raise ValueError('FLX palette packet outside bounds')
                        for i in range(length):
                            colors[index + i] = tuple(c.take(3))
                        index += length
                    if c.pos != len(data):
                        raise ValueError('trailing FLX palette data')
                elif kind in (100, 104):
                    if kind == 104:
                        data = lz_decode(data)
                    apply_runs(data, pixels)
                elif kind == 102:
                    if len(data) != 16:
                        raise ValueError('invalid FLX rectangle length')
                    x, y, w, h = struct.unpack('<4I', data)
                    if x + w > self.width or y + h > self.height:
                        raise ValueError('FLX rectangle outside dimensions')
                else:
                    raise ValueError(f'unsupported FLX chunk type {kind}')
            top_down = b''.join(pixels[y * self.width:(y + 1) * self.width]
                                for y in range(self.height - 1, -1, -1))
            yield Image(self.width, self.height, top_down), tuple(colors)

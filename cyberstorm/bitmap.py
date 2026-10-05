"""Narrow BMX/ANX frame-table reader; no playback or transparency semantics."""

from dataclasses import dataclass
import struct
from .compression import MAX_OUTPUT, rle_decode, unwrap


@dataclass(frozen=True)
class Image:
    width: int
    height: int
    pixels: bytes

    def __post_init__(self):
        if not 0 < self.width * self.height <= MAX_OUTPUT:
            raise ValueError('invalid image dimensions')
        if self.width <= 0 or self.height <= 0 or len(self.pixels) != self.width * self.height:
            raise ValueError('image dimensions do not match pixel bytes')


class Sprite:
    def __init__(self, data):
        self.data = unwrap(data)
        if len(self.data) < 4:
            raise ValueError('truncated sprite header')
        self.count, = struct.unpack_from('<I', self.data)
        table_end = 4 + self.count * 12
        if not 0 < self.count <= 4096 or table_end > len(self.data):
            raise ValueError('invalid sprite frame count')
        frames = []
        for i in range(self.count):
            at = 4 + i * 12
            off, w, h, unknown, method, tail = struct.unpack_from('<iHHBBH', self.data, at)
            start = at + off
            if not table_end <= start < len(self.data):
                raise ValueError('sprite frame offset outside pixel area')
            if not w or not h or w * h > MAX_OUTPUT:
                raise ValueError('invalid sprite dimensions')
            frames.append((start, w, h, method, unknown, tail))
        self.frames = tuple(frames)
        starts = sorted({f[0] for f in frames})
        self._ends = dict(zip(starts, starts[1:] + [len(self.data)]))

    def frame(self, index):
        if not 0 <= index < self.count:
            raise ValueError('sprite frame index outside range')
        start, w, h, method, _, _ = self.frames[index]
        stream = self.data[start:self._ends[start]]
        if method == 0:
            if len(stream) != w * h:
                raise ValueError('raw sprite frame size mismatch')
            pixels = stream
        elif method == 1:
            pixels = rle_decode(stream, w * h)
        else:
            raise ValueError(f'unsupported sprite compression method {method}')
        return Image(w, h, pixels)

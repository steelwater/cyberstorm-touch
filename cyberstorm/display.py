"""Small dependency-free PNG encoder for local inspection, not game rendering."""

import struct
import zlib


def png_bytes(image, palette):
    if len(palette) != 256 or any(len(c) != 3 or any(not 0 <= v <= 255 for v in c) for c in palette):
        raise ValueError('expected 256 RGB palette entries')
    def chunk(kind, data):
        return struct.pack('>I', len(data)) + kind + data + struct.pack('>I', zlib.crc32(kind + data))
    rows = b''.join(b'\0' + image.pixels[y * image.width:(y + 1) * image.width]
                    for y in range(image.height))
    header = struct.pack('>2I5B', image.width, image.height, 8, 3, 0, 0, 0)
    return (b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', header)
            + chunk(b'PLTE', bytes(v for color in palette for v in color))
            + chunk(b'IDAT', zlib.compress(rows)) + chunk(b'IEND', b''))

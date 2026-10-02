"""Regular 256-record PLX palettes; fourth-byte semantics remain unknown."""


def decode_palette(data):
    if len(data) != 1024:
        raise ValueError('unsupported PLX shape: expected exactly 1024 bytes; BGMPALS is separate')
    if any(data[3::4]):
        raise ValueError('unsupported PLX fourth-byte values (only zero verified)')
    return tuple(tuple(data[i:i + 3]) for i in range(0, 1024, 4))

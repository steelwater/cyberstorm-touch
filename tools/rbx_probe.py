"""Read the observed CyberStorm GOG 1.1 RBX layout; emit metadata only."""

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import struct

MAGIC = b'\x9e\x9a\xa9\x0b'


def read_exact(source, size):
    data = source.read(size)
    if len(data) != size:
        raise ValueError('truncated RBX input')
    return data


def probe(path):
    with path.open('rb') as source:
        source.seek(0, 2)
        file_size = source.tell()
        source.seek(0)
        magic, count = struct.unpack('<4sI', read_exact(source, 8))
        if magic != MAGIC:
            raise ValueError('unsupported RBX signature')
        index_end = 8 + count * 16
        if not count or index_end > file_size:
            raise ValueError('invalid RBX index count')
        entries = []
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
            if not index_end <= offset <= file_size - 4:
                raise ValueError('RBX offset outside payload area')
            entries.append({'name': name, 'offset': offset})

        # This strict probe accepts only the contiguous layout observed in GOG 1.1.
        # Physical order differs from filename index order.
        expected_offset = index_end
        for entry in sorted(entries, key=lambda item: item['offset']):
            offset = entry['offset']
            if offset != expected_offset:
                raise ValueError('unsupported gap, overlap, or duplicate RBX offset')
            source.seek(offset)
            size, = struct.unpack('<I', read_exact(source, 4))
            if size > file_size - offset - 4:
                raise ValueError('RBX payload extends beyond file')
            entry['stored_size'] = size
            expected_offset = offset + 4 + size
            digest = hashlib.sha256()
            header = b''
            remaining = size
            while remaining:
                block = read_exact(source, min(1024 * 1024, remaining))
                if not header:
                    header = block[:24]
                digest.update(block)
                remaining -= len(block)
            entry['sha256'] = digest.hexdigest()
            entry['pkx_wrapper'] = header.startswith(b'PKX:')
            if entry['pkx_wrapper']:
                if size < 24:
                    raise ValueError('truncated PKX wrapper')
                entry['pkx_header_u32'] = list(struct.unpack('<5I', header[4:24]))
            if entry['name'].endswith('.PLX'):
                # Only the regular single-palette shape; BGMPALS.PLX is different.
                if size == 1024:
                    source.seek(offset + 4)
                    palette = read_exact(source, size)
                    entry['palette_records'] = 256
                    entry['palette_record_bytes'] = 4
                    entry['palette_fourth_byte_zero'] = not any(palette[3::4])
            if entry['name'].endswith('.FLX') and not entry['pkx_wrapper'] and len(header) >= 16:
                length, magic, frames, width, height, depth, flags = struct.unpack('<I6H', header[:16])
                entry['flx_header_candidate'] = dict(length=length, magic=hex(magic),
                    frames=frames, width=width, height=height, depth=depth, flags=flags)
        if expected_offset != file_size:
            raise ValueError('unsupported trailing RBX data')
    return {'file': path.name, 'byte_size': file_size, 'entry_count': count,
            'index_end': index_end, 'contiguous_payloads': True,
            'extension_counts': dict(sorted(Counter(Path(e['name']).suffix for e in entries).items())),
            'entries': entries}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('archive', type=Path)
    args = parser.parse_args()
    try:
        result = probe(args.archive)
    except (OSError, ValueError) as error:
        parser.exit(1, f'rbx_probe: {error}\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()

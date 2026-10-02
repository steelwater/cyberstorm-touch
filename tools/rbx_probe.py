"""Read the observed CyberStorm GOG 1.1 RBX layout; emit metadata only."""

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import struct

# Permit both the historical script command and module invocation.
if __package__ in (None, ''):
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from cyberstorm.rbx import Archive, MAGIC


def probe(path):
    entries = []
    with Archive(path) as archive:
        for item in archive.entries:
            entry = dict(name=item.name, offset=item.offset, stored_size=item.size)
            digest = hashlib.sha256()
            header = archive.read(item.name, size=min(24, item.size))
            for offset in range(0, item.size, 1024 * 1024):
                digest.update(archive.read(item.name, offset=offset,
                              size=min(1024 * 1024, item.size - offset)))
            entry['sha256'] = digest.hexdigest()
            entry['pkx_wrapper'] = header.startswith(b'PKX:')
            if entry['pkx_wrapper']:
                if item.size < 24:
                    raise ValueError('truncated PKX wrapper')
                entry['pkx_header_u32'] = list(struct.unpack('<5I', header[4:24]))
            if item.name.endswith('.PLX') and item.size == 1024:
                palette = archive.read(item.name)
                entry.update(palette_records=256, palette_record_bytes=4,
                             palette_fourth_byte_zero=not any(palette[3::4]))
            if item.name.endswith('.FLX') and not entry['pkx_wrapper'] and len(header) >= 16:
                length, magic, frames, width, height, depth, flags = struct.unpack('<I6H', header[:16])
                entry['flx_header_candidate'] = dict(length=length, magic=hex(magic),
                    frames=frames, width=width, height=height, depth=depth, flags=flags)
            entries.append(entry)
        return {'file': archive.path.name, 'byte_size': archive.byte_size,
                'entry_count': len(entries), 'index_end': archive.index_end,
                'contiguous_payloads': True,
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

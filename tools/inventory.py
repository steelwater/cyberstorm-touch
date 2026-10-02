"""Emit deterministic, content-free metadata for a local research tree."""

import argparse
import csv
import hashlib
from pathlib import Path
import sys


def classify(path, header):
    """Conservative hints, not assertions about undocumented formats."""
    extension = path.suffix.lower()
    if header.startswith(b'MZ'):
        return 'DOS/PE candidate', 'executable/runtime'
    if header.startswith(b'RIFF'):
        kind = header[8:12].decode('ascii', errors='replace')
        return f'RIFF/{kind}', {'WAVE': 'audio/music', 'AVI ': 'animation',
                                 'PAL ': 'graphics/palette'}.get(kind, 'unknown')
    if header.startswith(b'OggS') or header.startswith(b'MThd'):
        return 'Ogg' if header.startswith(b'OggS') else 'MIDI', 'audio/music'
    if extension in {'.ini', '.cfg', '.conf', '.json'}:
        return 'configuration candidate (extension)', 'configuration'
    if extension == '.rbx':
        return 'RBX candidate (extension)', 'archive/container'
    if header.startswith(b'CYB:') and extension in {'.cbm', '.cbs'}:
        return 'CYB quick-start/map candidate', 'map/mission; saves candidate'
    if header.startswith(b'PKX:'):
        return 'PKX-wrapped resource', 'graphics/palette candidate'
    if extension in {'.png', '.jpg', '.ico', '.ttf'}:
        return 'image/font candidate (extension)', 'graphics/palette'
    if extension in {'.inf', '.set', '.info'}:
        return 'configuration candidate (extension)', 'configuration'
    if extension == '.zip':
        return 'ZIP candidate (extension)', 'archive/container'
    if extension in {'.txt', '.rtf', '.doc', '.pdf', '.xls'}:
        return 'documentation/reference (extension)', 'documentation'
    if extension == '.hashdb':
        return 'GOG hash database candidate', 'installer metadata'
    return 'unidentified', 'unknown'


def inventory(root):
    if not root.is_dir():
        raise ValueError('input must be an existing directory')
    for path in sorted(root.rglob('*')):
        if path.is_symlink():
            raise ValueError(f'symlink not supported: {path.relative_to(root)}')
        if path.is_dir():
            yield [path.relative_to(root).as_posix(), 'directory', '', '', '', '', '']
        elif path.is_file():
            digest = hashlib.sha256()
            size = 0
            with path.open('rb') as source:
                header = source.read(16)
                source.seek(0)
                for block in iter(lambda: source.read(1024 * 1024), b''):
                    digest.update(block)
                    size += len(block)
            guess, category = classify(path, header)
            yield [path.relative_to(root).as_posix(), 'file', size,
                   digest.hexdigest(), path.suffix.lower(), guess, category]
        else:
            raise ValueError(f'unsupported filesystem entry: {path.relative_to(root)}')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('root', type=Path)
    args = parser.parse_args()
    try:
        # Collect before output so failed reads cannot look like a complete manifest.
        rows = list(inventory(args.root))
    except (OSError, ValueError) as error:
        parser.exit(1, f'inventory: {error}\n')
    writer = csv.writer(sys.stdout, lineterminator='\n')
    writer.writerow(['relative_path', 'entry_kind', 'byte_size', 'sha256',
                     'extension', 'type_guess', 'classification'])
    writer.writerows(rows)


if __name__ == '__main__':
    main()

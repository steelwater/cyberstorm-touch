"""Identify the exact four supplied GOG 1.1 archives; do not guess variants."""

from contextlib import ExitStack
import hashlib
from pathlib import Path
from .rbx import Archive

EXPECTED = {'CYBDATA1.RBX': (4764886, '9d1f0dd01b8a957e71b65bca22057cd76afc3d7111002e58f2b4114970712538'),
 'CYBDATA2.RBX': (15306390, '8035fa63a058ab4dd38f7a375bc5a895340ae5974d47ec007b73573bed2f661d'),
 'CYBDATA3.RBX': (16805969, 'defc35b524bbab53dc058367ff256dc1111adc6ab8b8a572acf53d8cd11fe9a2'),
 'CYBDATA4.RBX': (165223668,
                  'db58a3d85db2ec1e4cd6956ae237853d9662aa79cc9837497be87bfa85c028e7')}


class Installation:
    def __init__(self, root):
        self.root = Path(root)
        self.archives = {}
        self._stack = ExitStack()
        try:
            if not self.root.is_dir():
                raise ValueError('installation must be an existing data directory')
            for name, (size, digest) in EXPECTED.items():
                path = self.root / name
                if not path.is_file() or path.is_symlink():
                    raise ValueError(f'missing or unsupported archive: {name}')
                archive = self._stack.enter_context(Archive(path))
                if archive.byte_size != size:
                    raise ValueError(f'unsupported GOG 1.1 archive size: {name}')
                with path.open('rb') as source:
                    actual = hashlib.file_digest(source, 'sha256').hexdigest()
                if actual != digest:
                    raise ValueError(f'unsupported GOG 1.1 archive checksum: {name}')
                self.archives[name] = archive
        except BaseException:
            self.close()
            raise

    def archive(self, name):
        try:
            return self.archives[name]
        except KeyError:
            raise ValueError(f'unknown archive: {name}') from None

    def close(self):
        self._stack.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

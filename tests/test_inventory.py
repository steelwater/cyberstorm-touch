import hashlib
from pathlib import Path
import tempfile
import unittest

from tools.inventory import inventory


class InventoryTests(unittest.TestCase):
    def test_records_nested_files_and_empty_directories(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'empty').mkdir()
            (root / 'data').mkdir()
            (root / 'data' / 'sample.bin').write_bytes(b'generated fixture')
            rows = list(inventory(root))
            self.assertEqual([row[0] for row in rows],
                             ['data', 'data/sample.bin', 'empty'])
            self.assertEqual(rows[1][2], 17)
            self.assertEqual(rows[1][3], hashlib.sha256(b'generated fixture').hexdigest())
            self.assertEqual(rows[2][1], 'directory')

    def test_rejects_missing_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ValueError):
                list(inventory(Path(directory) / 'missing'))

    def test_rejects_symlink_outside_research_tree(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'link').symlink_to('/etc/hosts')
            with self.assertRaisesRegex(ValueError, 'symlink'):
                list(inventory(root))


if __name__ == '__main__':
    unittest.main()

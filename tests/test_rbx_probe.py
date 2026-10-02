import hashlib
from pathlib import Path
import struct
import tempfile
import unittest

from tools.rbx_probe import MAGIC, probe


def fixture(entries):
    offset = 8 + 16 * len(entries)
    index = bytearray(MAGIC + struct.pack('<I', len(entries)))
    payloads = bytearray()
    for name, payload in entries:
        index.extend(struct.pack('<12sI', name.encode(), offset))
        payloads.extend(struct.pack('<I', len(payload)) + payload)
        offset += 4 + len(payload)
    return index + payloads


class RbxProbeTests(unittest.TestCase):
    def read(self, data):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'generated.rbx'
            path.write_bytes(data)
            return probe(path)

    def test_reads_independent_payloads_and_hashes(self):
        result = self.read(fixture([('A.DAT', b'abc'), ('B.DAT', b'xy')]))
        self.assertEqual(result['entry_count'], 2)
        self.assertEqual(result['entries'][0]['sha256'], hashlib.sha256(b'abc').hexdigest())
        self.assertEqual(result['entries'][1]['offset'], 47)
        self.assertEqual(result['entries'][1]['stored_size'], 2)

    def test_accepts_index_order_different_from_payload_order(self):
        data = fixture([('A.DAT', b'abc'), ('B.DAT', b'xy')])
        data[8:40] = data[24:40] + data[8:24]
        result = self.read(data)
        self.assertEqual(result['entries'][0]['name'], 'B.DAT')

    def test_reads_generated_palette_structure(self):
        palette = bytes(value for i in range(256) for value in (i, i, i, 0))
        entry = self.read(fixture([('TEST.PLX', palette)]))['entries'][0]
        self.assertEqual(entry['palette_records'], 256)
        self.assertTrue(entry['palette_fourth_byte_zero'])

    def test_reports_pkx_without_claiming_decompression(self):
        payload = b'PKX:' + struct.pack('<5I', 1, 2, 3, 4, 5)
        entry = self.read(fixture([('TEST.BMX', payload)]))['entries'][0]
        self.assertTrue(entry['pkx_wrapper'])
        self.assertEqual(entry['pkx_header_u32'], [1, 2, 3, 4, 5])

    def test_rejects_truncated_files(self):
        valid = fixture([('A.DAT', b'abc')])
        for length in range(len(valid)):
            with self.subTest(length=length), self.assertRaises(ValueError):
                self.read(valid[:length])

    def test_rejects_corrupt_boundaries_names_and_headers(self):
        valid = fixture([('A.DAT', b'abc')])
        cases = []
        for offset, replacement in [(0, b'NOPE'), (4, struct.pack('<I', 0xffffffff)),
                                    (8, b'../BAD.DAT\0\0'), (20, struct.pack('<I', 8)),
                                    (24, struct.pack('<I', 0xffffffff))]:
            data = valid.copy()
            data[offset:offset + len(replacement)] = replacement
            cases.append(data)
        cases.extend([valid + b'x', fixture([('A.DAT', b'x'), ('A.DAT', b'y')]),
                      fixture([('A.BMX', b'PKX:')])])
        overlap = fixture([('A.DAT', b'abc'), ('B.DAT', b'xy')])
        overlap[36:40] = struct.pack('<I', 40)
        cases.append(overlap)
        for index, data in enumerate(cases):
            with self.subTest(case=index), self.assertRaises(ValueError):
                self.read(data)


if __name__ == '__main__':
    unittest.main()

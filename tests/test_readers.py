"""All binary inputs in this suite are generated, never original game assets."""

import hashlib
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import zlib

from cyberstorm.bitmap import Image, Sprite
from cyberstorm.compression import PKX_MAGIC, lz_decode, rle_decode, unwrap
from cyberstorm.display import png_bytes
from cyberstorm.flx import Animation, apply_runs
from cyberstorm.font import Font
from cyberstorm.installation import Installation
from cyberstorm.palette import decode_palette
from cyberstorm.rbx import Archive
from test_rbx_probe import fixture
from tools.asset_inspector import describe, render


def literals(data):
    groups, partial = divmod(len(data), 8)
    header = bytes([partial]) + struct.pack('<H', groups)
    return header + b''.join(b'\0' + data[i:i + 8] for i in range(0, len(data), 8))


def pkx(data):
    packed = literals(data)
    return PKX_MAGIC + struct.pack('<III', 14, len(packed), len(data)) + packed


def sprite(data=b'\x01\x02\x03\x04', method=0):
    return struct.pack('<IiHHBBH', 1, 12, 2, 2, 0, method, 0) + data


def chunk(kind, data):
    return struct.pack('<IH', len(data) + 6, kind) + data


def animation(frames):
    body = bytearray()
    for chunks in frames:
        payload = b''.join(chunks)
        body.extend(struct.pack('<IHH8x', len(payload) + 16, 0xF1FA, len(chunks)) + payload)
    header = bytearray(128)
    struct.pack_into('<I6H', header, 0, 128 + len(body), 0xAF20, len(frames), 2, 2, 8, 0)
    return header + body


def font():
    header = b'FNX:' + struct.pack('<9I', 0x80000, 0, 2, 0, 65, 1, 40, 44, 300)
    widths = bytearray(256)
    widths[65] = 2
    return header + struct.pack('<I', 0) + widths + bytes([0, 1, 2, 0])


class ArchiveTests(unittest.TestCase):
    def test_exact_lookup_and_slices_never_cross_resource_envelopes(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / 'sample.rbx'
            path.write_bytes(fixture([('A.DAT', b'abcdef'), ('B.DAT', b'xyz')]))
            with Archive(path) as archive:
                self.assertEqual(archive.read('A.DAT', offset=2, size=3), b'cde')
                self.assertEqual(archive.lookup('A.DAT').payload_offset, 44)
                for kwargs in [dict(offset=-1), dict(offset=7), dict(size=7), dict(limit=2)]:
                    with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                        archive.read('A.DAT', **kwargs)
                with self.assertRaisesRegex(ValueError, 'exact name'):
                    archive.lookup('a.dat')

    def test_listing_reads_only_index_and_length_words(self):
        import io
        class Tracked(io.BytesIO):
            total = 0
            def read(self, size=-1):
                self.total += size
                return super().read(size)
        source = Tracked(fixture([('A.DAT', bytes(10000))]))
        with patch.object(Path, 'open', return_value=source):
            with Archive('generated.rbx') as archive:
                self.assertEqual(len(archive.entries), 1)
                self.assertEqual(source.total, 28)

    def test_rejects_gaps_zero_counts_embedded_nuls_and_case_duplicates(self):
        cases = [fixture([('A.DAT', b'a'), ('a.dat', b'b')])]
        base = fixture([('A.DAT', b'abc')])
        for offset, value in [(4, struct.pack('<I', 0)), (8, b'A\0.DAT'),
                              (20, struct.pack('<I', 25))]:
            data = base.copy()
            data[offset:offset + len(value)] = value
            cases.append(data)
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / 'sample.rbx'
            for data in cases:
                path.write_bytes(data)
                with self.assertRaises(ValueError):
                    Archive(path)


class CompressionTests(unittest.TestCase):
    def test_literal_groups_cover_all_partial_lengths(self):
        for size in range(1, 33):
            data = bytes(range(size))
            self.assertEqual(unwrap(pkx(data)), data)

    def test_packed_and_extended_group_headers_and_overlapping_references(self):
        self.assertEqual(lz_decode(bytes([11, 32, 65, 66, 19, 0])), b'ABABABAB')
        self.assertEqual(lz_decode(b'\0\xff\xff\x01\0\0\0\0abcdefgh'), b'abcdefgh')
        self.assertEqual(lz_decode(b'\x10\0abcdefgh'), b'abcdefgh')

    def test_rejects_every_truncation_and_bad_sizes(self):
        data = pkx(b'generated fixture with multiple groups')
        # Missing PKX signature belongs to downstream format validation.
        for n in range(4, len(data)):
            with self.subTest(length=n), self.assertRaises(ValueError):
                unwrap(data[:n])
        for offset, word in [(4, 0), (12, 12), (16, 0), (20, 0), (20, 2**32 - 1), (20, 2)]:
            bad = bytearray(data)
            struct.pack_into('<I', bad, offset, word)
            with self.subTest(offset=offset, word=word), self.assertRaises(ValueError):
                unwrap(bad)
        with self.assertRaises(ValueError):
            unwrap(data, limit=2)
        with self.assertRaises(ValueError):
            lz_decode(b'\x09\x80\0\0')
        with self.assertRaises(ValueError):
            lz_decode(literals(b'abc') + b'x')
        with self.assertRaises(ValueError):
            lz_decode(bytes([11, 32, 65, 66, 19, 0]), limit=7)

    def test_rle_literals_runs_and_exact_termination(self):
        self.assertEqual(rle_decode(b'\x02ab\x83c\0', 5), b'abccc')
        self.assertEqual(rle_decode(b'\x81x\x80', 1), b'x')
        for data, size in [(b'\x81', 1), (b'\x02a', 2), (b'\x82a\0', 1),
                           (b'\x81a', 1), (b'\0', 1), (b'\0x', 0)]:
            with self.subTest(data=data), self.assertRaises(ValueError):
                rle_decode(data, size)
        data = b'\x83x\0'
        self.assertEqual(unwrap(PKX_MAGIC + struct.pack('<III', 1, len(data), 3) + data), b'xxx')


class VisualTests(unittest.TestCase):
    def test_palette_preserves_rgb_channels_without_inventing_alpha(self):
        data = bytes([10, 20, 30, 0]) * 256
        self.assertEqual(decode_palette(data)[0], (10, 20, 30))
        for invalid in [data[:-1], data + b'\0', bytes(13320), bytes([1, 2, 3, 4]) * 256]:
            with self.assertRaises(ValueError):
                decode_palette(invalid)

    def test_raw_and_wrapped_rle_frames_decode_row_major(self):
        expected = bytes([1, 2, 3, 4])
        self.assertEqual(Sprite(sprite()).frame(0), Image(2, 2, expected))
        self.assertEqual(Sprite(pkx(sprite(b'\x04' + expected + b'\0', 1))).frame(0).pixels, expected)
        with self.assertRaises(ValueError):
            Sprite(sprite()).frame(1)
        for data in [b'', struct.pack('<I', 0), sprite()[:-1], sprite(b'abcd', 13)]:
            with self.assertRaises(ValueError):
                Sprite(data).frame(0)
        bad = bytearray(sprite())
        struct.pack_into('<i', bad, 4, -4)
        with self.assertRaises(ValueError):
            Sprite(bad)

    def test_font_code_map_and_table_bounds(self):
        f = Font(pkx(font()))
        self.assertEqual(f.glyph(65).pixels, bytes([0, 1, 2, 0]))
        with self.assertRaises(ValueError):
            f.glyph(64)
        for n in range(len(font())):
            with self.subTest(n=n), self.assertRaises(ValueError):
                Font(font()[:n])
        for offset, value in [(4, 1), (12, 0), (20, 256), (24, 257), (28, 0), (40, 999)]:
            data = bytearray(font())
            struct.pack_into('<I', data, offset, value)
            with self.assertRaises(ValueError):
                Font(data)

    def test_flx_retains_delta_pixels_and_converts_bottom_up_rows(self):
        first = chunk(100, b'\x04\x01\x02\x03\x04\x80\0\0')
        second = chunk(104, literals(b'\x81\x01\x09\x80\0\0'))
        color = chunk(4, b'\x01\0\x01\x01\x0a\x14\x1e')
        frames = list(Animation(animation([[first, color], [second]])).decode([(0, 0, 0)] * 256))
        self.assertEqual(frames[0][0].pixels, bytes([3, 4, 1, 2]))
        self.assertEqual(frames[1][0].pixels, bytes([3, 4, 1, 9]))
        self.assertEqual(frames[1][1][1], (10, 20, 30))

    def test_flx_extended_runs_skips_and_bounds(self):
        pixels = bytearray(7)
        apply_runs(b'\0\x02\x07\x80\x01\0\x80\x02\x80ab\x80\x02\xc0c\x80\0\0', pixels)
        self.assertEqual(pixels, b'\x07\x07\0abcc')
        for stream in [b'\x80', b'\xff\x80\0\0', b'\x02a', b'\x80\0\0x']:
            with self.assertRaises(ValueError):
                apply_runs(stream, bytearray(4))

    def test_flx_rejects_truncation_unsupported_chunks_and_bad_rectangles(self):
        data = animation([[chunk(100, b'\x80\0\0')]])
        for n in range(len(data)):
            with self.subTest(n=n), self.assertRaises(ValueError):
                Animation(data[:n])
        for c in [chunk(999, b''), chunk(102, struct.pack('<4I', 1, 1, 2, 2)),
                  chunk(4, b'\x01\0\xff\x02' + bytes(6))]:
            with self.assertRaises(ValueError):
                list(Animation(animation([[c]])).decode([(0, 0, 0)] * 256))
        for offset, value in [(0, 1), (128, 15), (144, 9999)]:
            bad = data.copy()
            struct.pack_into('<I', bad, offset, value)
            with self.assertRaises(ValueError):
                Animation(bad)

    def test_png_preserves_dimensions_rgb_and_index_rows(self):
        png = png_bytes(Image(2, 2, bytes([1, 2, 3, 4])), [(10, 20, 30)] * 256)
        self.assertEqual(png[:8], b'\x89PNG\r\n\x1a\n')
        at = 8
        chunks = {}
        while at < len(png):
            size, = struct.unpack_from('>I', png, at)
            kind = png[at + 4:at + 8]
            data = png[at + 8:at + 8 + size]
            crc, = struct.unpack_from('>I', png, at + 8 + size)
            self.assertEqual(crc, zlib.crc32(kind + data))
            chunks[kind] = data
            at += 12 + size
        self.assertEqual(chunks[b'PLTE'][:3], bytes([10, 20, 30]))
        self.assertEqual(zlib.decompress(chunks[b'IDAT']), b'\0\x01\x02\0\x03\x04')


class InspectorTests(unittest.TestCase):
    def test_installation_validates_all_expected_archives_and_checksum(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / 'CYBDATA1.RBX'
            data = fixture([('A.BMX', sprite())])
            path.write_bytes(data)
            expected = {path.name: (len(data), hashlib.sha256(data).hexdigest())}
            with patch('cyberstorm.installation.EXPECTED', expected):
                with Installation(root) as installation:
                    self.assertEqual(describe(installation.archive(path.name), 'A.BMX')['frames'], 1)
                path.write_bytes(data[:-1] + b'x')
                with self.assertRaisesRegex(ValueError, 'checksum'):
                    Installation(root)
            with self.assertRaises(ValueError):
                Installation(root)

    def test_render_writes_only_to_local_research_and_reports_unsupported_data(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / 'sample.rbx'
            path.write_bytes(fixture([('A.BMX', sprite()), ('P.PLX', bytes(1024)), ('A.DAT', b'x')]))
            class Local:
                def archive(self, name):
                    return archive
            with Archive(path) as archive, patch('tools.asset_inspector.OUTPUT_ROOT', Path(root) / 'outputs'):
                output = render(Local(), 'sample.rbx', 'A.BMX', 'sample.rbx:P.PLX', 0, 1)
                self.assertTrue((output.parent / '0.png').is_file())
                self.assertIn('Stored index', output.read_text(encoding='utf-8'))
                for name, palette, first, count in [('A.DAT', 'x:P.PLX', 0, 1),
                      ('A.BMX', None, 0, 1), ('A.BMX', 'x:P.PLX', 0, 2)]:
                    with self.assertRaises(ValueError):
                        render(Local(), 'sample.rbx', name, palette, first, count)
                self.assertEqual(describe(archive, 'A.DAT')['decode_status'], 'unsupported resource type')

    def test_missing_installation_is_a_clear_cli_failure(self):
        with tempfile.TemporaryDirectory() as root:
            result = subprocess.run([sys.executable, '-m', 'tools.asset_inspector', root, 'verify'],
                                    capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(result.stdout, '')
        self.assertIn('missing or unsupported archive', result.stderr)
        self.assertNotIn('Traceback', result.stderr)

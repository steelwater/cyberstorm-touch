"""Generated fixtures only: no original game bytes, colors, or screenshots."""

import copy
import json
import math
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch

from cyberstorm.scene import assemble, load_scene
from cyberstorm.viewport import Timeline, Viewport, hex_origin, hex_outline


def bitmap(width=64, height=64, count=1):
    descriptors = []
    pixels = []
    for i in range(count):
        at = 4 + i * 12
        offset = 4 + count * 12 + i * width * height - at
        descriptors.append(struct.pack('<iHHBBH', offset, width, height, 0, 0, 0))
        pixels.append(bytes([i + 1]) * width * height)
    return struct.pack('<I', count) + b''.join(descriptors + pixels)


def animation():
    chunks = []
    # Two top-down outputs [2,1], then [2,3] from bottom-up accumulated rows.
    for value in (b'\x02\x01\x02\x80\x00\x00', b'\x01\x03\x81\x80\x00\x00'):
        chunk = struct.pack('<IH', len(value) + 6, 100) + value
        chunks.append(struct.pack('<IHH8x', 16 + len(chunk), 0xF1FA, 1) + chunk)
    header = bytearray(128)
    struct.pack_into('<I6H', header, 0, 128 + sum(map(len, chunks)), 0xAF20, 2, 1, 2, 8, 0)
    return bytes(header) + b''.join(chunks)


class FakeInstallation:
    def __init__(self):
        self.files = {'GROUND.BMX': bitmap(count=2), 'ACTOR.ANX': bitmap(2, 2, 2),
                      'CLIP.FLX': animation(),
                      'TEST.PLX': b''.join(bytes((i, 255 - i, i // 2, 0)) for i in range(256))}

    def archive(self, name):
        if name != 'TEST.RBX':
            raise ValueError('unknown archive')
        return self

    def read(self, name):
        if name not in self.files:
            raise ValueError('missing resource')
        return self.files[name]


def description():
    def asset(resource, frames, anchor):
        return dict(resource='TEST.RBX:' + resource, palette='TEST.RBX:TEST.PLX',
                    frames=frames, anchor=anchor, key=None, fps=10)
    return dict(version=1, title='Generated scene',
                camera=dict(center=[56, 48], reference=[112, 96]),
                assets={'ground': asset('GROUND.BMX', [0, 1], [0, 0]),
                        'actor': asset('ACTOR.ANX', [0, 1], [1, 2])},
                terrain=dict(asset='ground', columns=2, rows=1),
                objects=[dict(asset='actor', position=[30, 40], frame=None)])


class ViewportTests(unittest.TestCase):
    def test_required_aspect_ratios_keep_artwork_proportional_and_expand_the_view(self):
        widths = [960, 1280, 1152, 1680, 2560]  # 4:3, 16:9, 16:10, 21:9, 32:9
        for width in widths:
            with self.subTest(width=width):
                view = Viewport.fit((width, 720), (640, 480), (10, 20))
                self.assertEqual(view.scale, 1)
                self.assertEqual(view.screen((10, 20)), (width / 2, 360))
                self.assertEqual(view.rectangle((10, 20), (0, 0), (64, 64))[2:], (64, 64))
                self.assertLessEqual(view.hud_safe_rect[2], 1280)
                self.assertEqual(view.hud_safe_rect[0] * 2 + view.hud_safe_rect[2], width)

    def test_integer_scaling_and_small_window_fractional_fallback(self):
        self.assertEqual(Viewport.fit((1920, 1080), (640, 480), (0, 0)).scale, 2)
        self.assertEqual(Viewport.fit((320, 240), (640, 480), (0, 0)).scale, 0.5)
        self.assertEqual(Viewport.fit((960, 720), (640, 480), (0, 0), integer=False).scale, 1.5)
        self.assertEqual(Viewport.fit((640, 480), (640, 480), (0, 0), zoom=2).scale, 2)

    def test_anchor_placement_and_shared_edges_survive_fractional_scaling(self):
        view = Viewport.fit((701, 501), (640, 480), (320, 240), integer=False)
        x, y = view.screen((99, 198))
        self.assertEqual(view.rectangle((100, 200), (1, 2), (64, 64))[:2], (round(x), round(y)))
        left = view.rectangle((100, 200), (0, 0), (64, 64))
        right = view.rectangle((164, 200), (0, 0), (64, 64))
        self.assertEqual(left[0] + left[2], right[0])

    def test_high_dpi_uses_drawable_pixels_with_equal_axes(self):
        normal = Viewport.fit((640, 480), (640, 480), (0, 0))
        retina = Viewport.fit((1280, 960), (640, 480), (0, 0))
        self.assertEqual(retina.screen((12, 20)), tuple(x * 2 for x in normal.screen((12, 20))))

    def test_invalid_dimensions_zoom_and_camera_fail(self):
        for bad in (0, -1, math.inf, math.nan):
            with self.assertRaises(ValueError):
                Viewport.fit((bad, 100), (64, 64), (0, 0))
            with self.assertRaises(ValueError):
                Viewport.fit((100, 100), (64, 64), (0, 0), zoom=bad)
        with self.assertRaises(ValueError):
            Viewport.fit((100, 100), (64, 64), (math.inf, 0))

    def test_hexes_have_shared_vertices_and_staggered_columns(self):
        self.assertEqual(hex_origin(1, 0), (48, 32))
        self.assertEqual(hex_origin(2, 1), (96, 64))
        first = set(hex_outline(hex_origin(0, 0)))
        second = set(hex_outline(hex_origin(1, 0)))
        self.assertEqual(first & second, {(64, 32), (48, 64)})


class TimelineTests(unittest.TestCase):
    def test_stored_frames_loop_at_diagnostic_rate_independent_of_draw_calls(self):
        clock = Timeline()
        self.assertEqual(clock.frame(3, 10), 0)
        clock.advance(0.1)
        self.assertEqual(clock.frame(3, 10), 1)
        clock.advance(0.1)
        self.assertEqual(clock.frame(3, 10), 2)
        clock.advance(0.1)
        self.assertEqual(clock.frame(3, 10), 0)
        clock.paused = True
        clock.advance(50)
        self.assertAlmostEqual(clock.elapsed, 0.3)
        clock.paused = False
        clock.advance(0.1)
        self.assertEqual(clock.frame(3, 10), 1)

    def test_invalid_timeline_inputs_fail(self):
        for bad in (-1, math.inf, math.nan):
            with self.assertRaises(ValueError):
                Timeline().advance(bad)
        with self.assertRaises(ValueError):
            Timeline().frame(0, 10)
        with self.assertRaises(ValueError):
            Timeline().frame(2, 0)


class SceneTests(unittest.TestCase):
    def setUp(self):
        self.manifest = description()
        self.game = FakeInstallation()

    def test_scene_assembles_grid_and_explicit_anchors_without_changing_reader_pixels(self):
        scene = assemble(self.manifest, self.game)
        self.assertEqual(len(scene.terrain), 2)
        self.assertEqual(scene.terrain[1].position, (48, 32))
        self.assertEqual(scene.terrain[1].frame, 1)
        self.assertEqual(scene.assets['actor'].anchor, (1, 2))
        self.assertEqual(scene.assets['actor'].frames[0].image.pixels, b'\x01' * 4)
        self.assertIsNone(scene.assets['actor'].key)

    def test_flx_adapter_preserves_reader_delta_orientation_and_palette(self):
        self.manifest['assets']['actor']['resource'] = 'TEST.RBX:CLIP.FLX'
        asset = assemble(self.manifest, self.game).assets['actor']
        self.assertEqual([f.image.pixels for f in asset.frames], [b'\x02\x01', b'\x02\x03'])
        self.assertEqual(asset.frames[0].palette[1], (1, 254, 0))

    def test_missing_corrupt_and_unsupported_resources_name_the_failed_asset(self):
        for data, message in ((None, 'missing resource'), (b'broken', 'invalid sprite frame count'),
                              (bitmap(2, 2)[:13] + b'\x0d' + bitmap(2, 2)[14:], 'unsupported sprite')):
            with self.subTest(message=message):
                self.manifest['assets']['actor']['frames'] = [0]
                if data is None:
                    self.game.files.pop('ACTOR.ANX')
                else:
                    self.game.files['ACTOR.ANX'] = data
                with self.assertRaisesRegex(ValueError, 'asset actor:.*' + message):
                    assemble(self.manifest, self.game)

    def test_manifest_rejects_unknown_fields_invalid_shapes_and_placements(self):
        variants = []
        for key, value in [('version', 2), ('title', ''), ('objects', {}), ('assets', [])]:
            bad = copy.deepcopy(self.manifest)
            bad[key] = value
            variants.append(bad)
        for key, value in [('columns', 0), ('asset', 'absent'), ('rows', True)]:
            bad = copy.deepcopy(self.manifest)
            bad['terrain'][key] = value
            variants.append(bad)
        for key, value in [('frames', [1, 0]), ('frames', [0, 0]), ('frames', [99]),
                           ('key', 256), ('key', True), ('anchor', [0]), ('fps', 0), ('fps', 10 ** 1000),
                           ('resource', '../TEST.RBX:GROUND.BMX')]:
            bad = copy.deepcopy(self.manifest)
            bad['assets']['actor'][key] = value
            variants.append(bad)
        for key, value in [('frame', 2), ('asset', []), ('position', [0, math.nan])]:
            bad = copy.deepcopy(self.manifest)
            bad['objects'][0][key] = value
            variants.append(bad)
        bad = copy.deepcopy(self.manifest)
        bad['extra'] = 1
        variants.append(bad)
        for bad in variants:
            with self.subTest(manifest=bad), self.assertRaises(ValueError):
                assemble(bad, self.game)

    def test_scene_pixel_budget_is_checked_before_frame_decode(self):
        with patch('cyberstorm.scene.MAX_SCENE_PIXELS', 10), patch('cyberstorm.scene.Sprite.frame') as decode:
            with self.assertRaisesRegex(ValueError, 'pixel budget'):
                assemble(self.manifest, self.game)
            decode.assert_not_called()

    def test_manifest_size_and_invalid_json_fail_and_valid_file_loads(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'scene.json'
            path.write_text(json.dumps(self.manifest))
            self.assertEqual(load_scene(path, self.game).title, 'Generated scene')
            path.write_text('{')
            with self.assertRaisesRegex(ValueError, 'invalid scene JSON'):
                load_scene(path, self.game)
            path.write_bytes(b' ' * (256 * 1024 + 1))
            with self.assertRaisesRegex(ValueError, '256 KiB'):
                load_scene(path, self.game)


if __name__ == '__main__':
    unittest.main()

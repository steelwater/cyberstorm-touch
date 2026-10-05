"""Exercise SDL upload and composition using only generated pixels."""

import importlib.util
import os
import unittest

from cyberstorm.bitmap import Image
from cyberstorm.scene import Asset, Frame, Placement, Scene


@unittest.skipUnless(importlib.util.find_spec('pygame'), 'install requirements-renderer.txt for SDL checks')
class RendererTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.old_driver = os.environ.get('SDL_VIDEODRIVER')
        os.environ['SDL_VIDEODRIVER'] = 'dummy'
        import pygame
        from cyberstorm.pygame_renderer import BattlefieldWindow, image_surface
        cls.pg = pygame
        cls.window_type = BattlefieldWindow
        cls.surface = staticmethod(image_surface)

    @classmethod
    def tearDownClass(cls):
        if cls.old_driver is None:
            os.environ.pop('SDL_VIDEODRIVER', None)
        else:
            os.environ['SDL_VIDEODRIVER'] = cls.old_driver

    def setUp(self):
        self.palette = ((20, 30, 40), (20, 30, 40), (200, 80, 60)) + ((0, 0, 0),) * 253
        frames = (Frame(Image(2, 2, bytes([0, 1, 2, 2])), self.palette),
                  Frame(Image(2, 2, bytes([2, 2, 2, 2])), self.palette))
        self.scene = Scene('Generated pixels', {'actor': Asset(frames, (1, 1), 0, 10)}, (),
                           (Placement('actor', (4, 4), None),), (), (4, 4), (8, 8))
        self.window = self.window_type(self.scene, (8, 8), hidden=True, software=True)
        self.window.grid = False

    def tearDown(self):
        self.window.close()

    def test_palette_upload_distinguishes_transparent_index_from_same_rgb_opaque_index(self):
        frame = self.scene.assets['actor'].frames[0]
        surface = self.surface(frame.image, frame.palette, 0)
        self.assertEqual(tuple(surface.get_at((0, 0))), (20, 30, 40, 0))
        self.assertEqual(tuple(surface.get_at((1, 0))), (20, 30, 40, 255))
        self.assertEqual(self.surface(frame.image, frame.palette).get_at((0, 0)).a, 255)

    def test_bad_palette_and_key_fail_explicitly(self):
        frame = self.scene.assets['actor'].frames[0]
        for palette, key in ((self.palette[:10], None), (self.palette, 256),
                             (((-1, 0, 0),) * 256, None)):
            with self.assertRaises(ValueError):
                self.surface(frame.image, palette, key)

    def test_actual_texture_composition_respects_anchor_key_and_color_channels(self):
        self.window.draw()
        output = self.window.renderer.to_surface()
        self.assertEqual(tuple(output.get_at((3, 3)))[:3], (19, 24, 30))
        self.assertEqual(tuple(output.get_at((4, 3)))[:3], (20, 30, 40))
        self.assertEqual(tuple(output.get_at((3, 4)))[:3], (200, 80, 60))
        self.window.timeline.advance(0.1)
        self.window.draw()
        self.assertEqual(tuple(self.window.renderer.to_surface().get_at((3, 3)))[:3], (200, 80, 60))

    def test_nearest_integer_scaling_replicates_pixels_without_blending(self):
        self.window.window.size = (16, 16)
        self.pg.event.pump()
        self.assertEqual(self.window.draw().scale, 2)
        output = self.window.renderer.to_surface()
        self.assertEqual(output.get_size(), (16, 16))
        for y in (8, 9):
            for x in (6, 7):
                self.assertEqual(tuple(output.get_at((x, y)))[:3], (200, 80, 60))

    def test_fractional_resize_keeps_nearest_colors_and_camera_center(self):
        self.window.window.size = (12, 10)
        self.window.integer = False
        self.pg.event.pump()
        view = self.window.draw()
        self.assertEqual(view.scale, 1.25)
        self.assertEqual(view.screen((4, 4)), (6, 5))
        output = self.window.renderer.to_surface()
        colors = {tuple(output.get_at((x, y)))[:3] for y in range(10) for x in range(12)}
        self.assertEqual(colors, {(19, 24, 30), (20, 30, 40), (200, 80, 60)})

    def test_keyboard_controls_change_only_view_and_timeline(self):
        for key in (self.pg.K_PLUS, self.pg.K_i, self.pg.K_g, self.pg.K_SPACE):
            self.pg.event.post(self.pg.event.Event(self.pg.KEYDOWN, key=key))
        self.window.events()
        self.assertEqual(self.window.zoom, 2)
        self.assertFalse(self.window.integer)
        self.assertTrue(self.window.grid)
        self.assertTrue(self.window.timeline.paused)
        self.pg.event.post(self.pg.event.Event(self.pg.KEYDOWN, key=self.pg.K_0))
        self.pg.event.post(self.pg.event.Event(self.pg.KEYDOWN, key=self.pg.K_ESCAPE))
        self.window.events()
        self.assertEqual(self.window.zoom, 1)
        self.assertFalse(self.window.running)

    def test_fractionally_scaled_joined_hexes_leave_no_background_cracks(self):
        from cyberstorm.viewport import hex_origin
        # Original geometric fixture, generated from a hex footprint equation.
        pixels = bytearray(64 * 64)
        for y in range(64):
            inset = round(abs(y - 31.5) / 2)
            pixels[y * 64:(y + 1) * 64] = bytes([0] * inset + [2] * (64 - 2 * inset) + [0] * inset)
        asset = Asset((Frame(Image(64, 64, bytes(pixels)), self.palette),), (0, 0), 0, 10)
        terrain = tuple(Placement('ground', hex_origin(c, r), 0) for c in range(8) for r in range(8))
        scene = Scene('Generated hexes', {'ground': asset}, terrain, (), (), (160, 160), (256, 256))
        self.window.close()
        self.window = self.window_type(scene, (197, 183), hidden=True, software=True)
        self.window.grid = False
        self.window.integer = False
        self.window.draw()
        output = self.window.renderer.to_surface()
        for y in range(10, 173):
            for x in range(10, 187):
                self.assertEqual(tuple(output.get_at((x, y)))[:3], (200, 80, 60))


if __name__ == '__main__':
    unittest.main()

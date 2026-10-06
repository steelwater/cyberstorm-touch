"""Generated battlefield geometry: spatial rules and input sequences without SDL."""

import math
import unittest

from cyberstorm.camera import Camera
from cyberstorm.hexmap import Hex, HexMap
from cyberstorm.navigation import Navigation


RATIOS = ((800, 600), (960, 540), (960, 600), (1260, 540), (1536, 432))


class SpatialTests(unittest.TestCase):
    def setUp(self):
        self.grid = HexMap(Hex(c, r) for c in range(20) for r in range(16))

    def test_every_cell_center_and_interior_corner_resolves_in_both_staggers(self):
        for cell in self.grid.cells:
            x, y = cell.center
            self.assertEqual(self.grid.pick((x, y)), cell)
            for dx, dy in ((-30, 0), (30, 0), (-15, -30), (15, 30)):
                self.assertEqual(self.grid.pick((x + dx, y + dy)), cell)

    def test_edges_have_deterministic_ownership_and_empty_space_has_none(self):
        self.assertEqual(self.grid.pick((56, 48)), Hex(0, 0))
        for point in ((0, 0), (63, 0), (-0.01, 32), (32, -0.01), (9999, 9999),
                      (math.nan, 10), (math.inf, 0)):
            self.assertIsNone(self.grid.pick(point))
        self.assertIsNone(HexMap(()).pick((32, 32)))
        self.assertIsNone(HexMap((Hex(0, 0), Hex(2, 0))).pick(Hex(1, 0).center))
        self.assertEqual(HexMap((Hex(-1, -1),)).pick(Hex(-1, -1).center), Hex(-1, -1))

    def test_camera_round_trips_and_hex_selection_survive_pan_zoom_and_aspect_changes(self):
        for size in RATIOS:
            for integer in (False, True):
                with self.subTest(size=size, integer=integer):
                    camera = Camera((640, 480), (450, 450), self.grid.bounds, size)
                    camera.integer = integer
                    for zoom in (0.25, 0.75, 1, 2, 4):
                        camera.set_zoom(zoom)
                        camera.pan((200, 200), (170, 235))
                        for cell in (Hex(0, 0), Hex(7, 5), Hex(19, 15)):
                            world = camera.view.world(camera.view.screen(cell.center))
                            for actual, expected in zip(world, cell.center):
                                self.assertAlmostEqual(actual, expected)
                            self.assertEqual(self.grid.pick(world), cell)
                        # Equal world distances always have equal screen distances.
                        origin = camera.view.screen((0, 0))
                        x = camera.view.screen((64, 0))[0] - origin[0]
                        y = camera.view.screen((0, 64))[1] - origin[1]
                        self.assertAlmostEqual(x, y)

    def test_every_camera_corner_is_bounded_at_zoom_limits_and_after_resize(self):
        for size in RATIOS:
            camera = Camera((640, 480), (450, 450), self.grid.bounds, size)
            for zoom in (0.001, 100):
                camera.set_zoom(zoom)
                self.assertEqual(camera.zoom, 0.25 if zoom < 1 else 4)
                for x, y in ((-1e6, -1e6), (-1e6, 1e6), (1e6, -1e6), (1e6, 1e6)):
                    camera.pan((0, 0), (x, y))
                    self.assert_bounded(camera)
                camera.resize((size[0] * 2, size[1] * 2))
                self.assert_bounded(camera)
                camera.resize(size)
                self.assert_bounded(camera)

    def assert_bounded(self, camera):
        left, top, right, bottom = self.grid.bounds
        for center, low, high, extent in zip(camera.center, (left, top), (right, bottom), camera.size):
            half = extent / (2 * camera.view.scale)
            if 2 * half >= high - low:
                self.assertEqual(center, (low + high) / 2)
            else:
                self.assertGreaterEqual(center - half, low - 1e-9)
                self.assertLessEqual(center + half, high + 1e-9)

    def test_zoom_preserves_cursor_world_point_except_where_bounds_require_clamping(self):
        camera = Camera((640, 480), (450, 450), self.grid.bounds, (640, 480))
        camera.integer = False
        point = (250, 180)
        expected = camera.view.world(point)
        for zoom in (2, 4, 1.5, 1):
            camera.set_zoom(zoom, point)
            for actual, wanted in zip(camera.view.world(point), expected):
                self.assertAlmostEqual(actual, wanted)
        camera.set_zoom(0.25, point)
        self.assert_bounded(camera)

    def test_repeated_limit_zoom_does_not_move_camera_and_bad_zoom_fails(self):
        camera = Camera((640, 480), (450, 450), self.grid.bounds, (640, 480))
        for limit in (0.25, 4):
            camera.set_zoom(limit)
            center = camera.center
            for _ in range(10):
                camera.set_zoom(limit, (123, 234))
                self.assertEqual(camera.center, center)
        for bad in (0, -1, math.nan, math.inf):
            with self.assertRaises(ValueError):
                camera.set_zoom(bad)


class GestureTests(unittest.TestCase):
    def setUp(self):
        self.grid = HexMap(Hex(c, r) for c in range(30) for r in range(30))
        self.camera = Camera((640, 480), (700, 700), self.grid.bounds, (640, 480))
        self.camera.integer = False
        self.nav = Navigation(self.camera, self.grid, (640, 480))

    def click(self, point):
        self.nav.mouse_down(1, point)
        self.nav.mouse_up(1, point)

    def test_mouse_selection_after_repeated_pan_and_cursor_zoom(self):
        for _ in range(10):
            self.nav.mouse_down(1, (320, 240))
            self.nav.mouse_move((350, 255))
            self.nav.mouse_up(1, (350, 255))
            self.nav.wheel(1, (300, 200))
            expected = self.grid.pick(self.camera.view.world((300, 200)))
            self.click((300, 200))
            self.assertEqual(self.nav.selected, expected)
            self.assertEqual(self.nav.hover, expected)

    def test_small_mouse_jitter_selects_but_drag_out_and_back_never_selects(self):
        start = self.camera.center
        self.nav.mouse_down(1, (320, 240))
        self.nav.mouse_move((323, 243))
        self.nav.mouse_up(1, (323, 243))
        self.assertEqual(self.camera.center, start)
        selected = self.nav.selected
        self.nav.mouse_down(1, (320, 240))
        self.nav.mouse_move((420, 240))
        self.nav.mouse_move((320, 240))
        self.nav.mouse_up(1, (320, 240))
        self.assertEqual(self.nav.selected, selected)
        self.assertEqual(self.camera.center, start)
        for button in (2, 3):
            self.nav.mouse_down(button, (200, 200))
            self.nav.mouse_up(button, (300, 200))
            self.assertEqual(self.nav.selected, selected)

    def test_clicking_empty_margin_clears_selection_without_inventing_cells(self):
        self.click((320, 240))
        self.assertIsNotNone(self.nav.selected)
        self.camera.set_zoom(0.25)
        self.click((0, 0))
        self.assertIsNone(self.nav.selected)
        self.assertIsNone(self.nav.pick((-1, 40)))

    def test_touch_tap_and_pan_distinguish_jitter_and_never_select_on_drag(self):
        self.nav.finger_down(1, (320, 240))
        self.nav.finger_move(1, (322, 241))
        self.nav.finger_up(1, (322, 241))
        selected = self.nav.selected
        self.assertIsNotNone(selected)
        center = self.camera.center
        self.nav.finger_down(1, (320, 240))
        self.nav.finger_move(1, (420, 240))
        self.nav.finger_up(1, (450, 240))
        self.assertAlmostEqual(self.camera.center[0], center[0] - 130)
        self.assertEqual(self.nav.selected, selected)

    def test_pinch_preserves_moving_midpoint_and_lifted_finger_cannot_select(self):
        self.nav.finger_down(1, (250, 240))
        self.nav.finger_down(2, (390, 240))
        expected = self.camera.view.world((320, 240))
        self.nav.finger_move(1, (210, 250))
        self.nav.finger_move(2, (450, 250))
        self.assertAlmostEqual(self.camera.zoom, 240 / 140)
        for actual, wanted in zip(self.camera.view.world((330, 250)), expected):
            self.assertAlmostEqual(actual, wanted)
        self.nav.finger_up(2, (450, 250))
        self.nav.finger_move(1, (230, 250))
        self.nav.finger_up(1, (230, 250))
        self.assertIsNone(self.nav.selected)
        self.assertFalse(self.nav.fingers)
        self.nav.finger_down(1, (320, 240))
        self.nav.finger_up(1, (320, 240))
        self.assertIsNotNone(self.nav.selected)

    def test_zero_distance_extra_fingers_and_zoom_limits_remain_stable(self):
        for identifier in (1, 2):
            self.nav.finger_down(identifier, (320, 240))
        self.nav.finger_move(2, (321, 240))
        self.nav.finger_move(2, (600, 240))
        self.assertEqual(self.camera.zoom, 4)
        self.nav.finger_down(3, (400, 300))
        center = self.camera.center
        self.nav.finger_move(3, (500, 350))
        self.assertEqual(self.camera.center, center)
        self.nav.finger_up(1, (320, 240))
        self.nav.finger_move(3, (600, 350))
        for identifier, point in ((2, (600, 240)), (3, (600, 350))):
            self.nav.finger_up(identifier, point)
        self.assertIsNone(self.nav.selected)
        self.assertTrue(all(math.isfinite(v) for v in self.camera.center))

    def test_cancel_and_resize_discard_gestures_but_preserve_valid_selection(self):
        self.click((320, 240))
        selected = self.nav.selected
        self.nav.finger_down(1, (320, 240))
        self.nav.cancel()
        self.nav.finger_up(1, (320, 240))
        self.nav.mouse_down(1, (320, 240))
        self.nav.resize((960, 540), (1920, 1080))
        self.nav.mouse_up(1, (320, 240))
        self.assertEqual(self.nav.selected, selected)
        self.assertIsNone(self.nav.mouse)
        self.assertFalse(self.nav.fingers)

    def test_high_dpi_picking_and_drag_threshold_use_logical_points(self):
        self.nav.resize((640, 480), (1280, 960))
        cell = Hex(14, 10)
        screen = self.camera.view.screen(cell.center)
        logical = tuple(v / 2 for v in screen)
        self.click(logical)
        self.assertEqual(self.nav.selected, cell)
        center = self.camera.center
        self.nav.mouse_down(1, logical)
        self.nav.mouse_move((logical[0] + 5, logical[1]))
        self.assertEqual(self.camera.center, center)
        self.nav.mouse_move((logical[0] + 10, logical[1]))
        self.assertAlmostEqual(self.camera.center[0], center[0] - 10)


if __name__ == '__main__':
    unittest.main()

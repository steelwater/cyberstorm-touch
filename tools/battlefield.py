"""Launch the battlefield navigation viewer using user-supplied GOG 1.1 data."""

import argparse
from pathlib import Path
import time

from cyberstorm.installation import Installation
from cyberstorm.scene import load_scene

DEFAULT_SCENE = Path(__file__).resolve().parents[1] / 'scenes' / 'representative.json'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', type=Path)
    parser.add_argument('--scene', type=Path, default=DEFAULT_SCENE)
    parser.add_argument('--size', nargs=2, type=int, metavar=('WIDTH', 'HEIGHT'), default=(1024, 768))
    parser.add_argument('--check', action='store_true', help='validate and decode the complete scene without a window')
    args = parser.parse_args()
    if any(not 160 <= n <= 16384 for n in args.size):
        parser.error('window dimensions must be in 160..16384')
    start = time.perf_counter()
    try:
        with Installation(args.directory) as installation:
            scene = load_scene(args.scene, installation)
    except (ValueError, OSError) as error:
        parser.exit(1, f'battlefield: {error}\n')
    frames = [frame for asset in scene.assets.values() for frame in asset.frames]
    pixels = sum(len(frame.image.pixels) for frame in frames)
    print(f'Loaded {len(scene.terrain)} hexes, {len(scene.objects)} objects, {len(frames)} frames; '
          f'{pixels:,} indexed pixels ({pixels * 4:,} RGBA bytes), '
          f'{time.perf_counter() - start:.3f}s load.')
    if args.check:
        return
    try:
        from cyberstorm.pygame_renderer import BattlefieldWindow
    except ImportError as error:
        parser.exit(1, f'battlefield: install requirements-renderer.txt in a virtual environment ({error})\n')
    print('Controls: click/tap select, drag/one-finger pan, wheel/pinch zoom;\n'
          '+/- zoom, 0 reset zoom, I integer/fractional, G grid, '
          'Space pause, F desktop fullscreen/windowed, Esc quit.\n'
          'Authored diagnostic scene; playback rates and placement are not original gameplay rules.')
    try:
        BattlefieldWindow(scene, tuple(args.size)).run()
    except (RuntimeError, ValueError) as error:
        parser.exit(1, f'battlefield: renderer initialization or drawing failed: {error}\n')


if __name__ == '__main__':
    main()

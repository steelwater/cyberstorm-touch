"""Local-only milestone integration checks; outputs metadata, never assets."""

import argparse
import json
from pathlib import Path
import time

from cyberstorm.bitmap import Sprite
from cyberstorm.compression import unwrap
from cyberstorm.flx import Animation
from cyberstorm.font import Font
from cyberstorm.installation import Installation
from cyberstorm.palette import decode_palette
from tools.rbx_probe import probe


def verify(root):
    started = time.perf_counter()
    wrapped = palettes = fonts = resources = 0
    with Installation(root) as installation:
        for name, archive in installation.archives.items():
            # Prove promotion preserves every Milestone 0 metadata observation.
            baseline = Path(__file__).resolve().parents[1] / 'docs' / 'research' / 'gog-1.1' / (name[:-4] + '.metadata.json')
            if probe(archive.path) != json.loads(baseline.read_text()):
                raise ValueError(f'Milestone 0 metadata changed: {name}')
            for entry in archive.entries:
                data = archive.read(entry.name)
                resources += 1
                if data.startswith(b'PKX:'):
                    unwrap(data)
                    wrapped += 1
                if entry.name.endswith('.PLX') and entry.size == 1024:
                    decode_palette(data)
                    palettes += 1
                if entry.name.endswith('.FNX'):
                    font = Font(data)
                    for code in range(font.first, font.first + font.count):
                        if font.widths[code]:
                            font.glyph(code)
                    fonts += 1
        first = installation.archive('CYBDATA1.RBX')
        palette = decode_palette(first.read('S1P1.PLX'))
        examples = {}
        for name in ('DMGMIN16.BMX', 'HRC001B0.ANX'):
            sprite = Sprite(first.read(name))
            examples[name] = [(sprite.frame(i).width, sprite.frame(i).height)
                              for i in range(sprite.count)]
        for archive, name in [('CYBDATA2.RBX', 'HB_AMB1.FLX'), ('CYBDATA4.RBX', 'BGMSH25A.FLX'),
                              ('CYBDATA4.RBX', 'BGMS.FLX')]:
            animation = Animation(installation.archive(archive).read(name))
            count = sum(1 for _ in animation.decode(palette))
            if count != animation.count:
                raise ValueError('decoded FLX frame count differs')
            examples[name] = dict(frames=count, width=animation.width, height=animation.height)
        sim_palette = decode_palette(first.read('SIMGUI.PLX'))
        bgms = Animation(installation.archive('CYBDATA4.RBX').read('BGMS.FLX'))
        _, embedded = next(bgms.decode(tuple((0, 0, 0) for _ in range(256))))
        if embedded[10:246] != sim_palette[10:246]:
            raise ValueError('PLX/FLX central palette comparison differs')
    return dict(resources=resources, pkx=wrapped, regular_palettes=palettes, fonts=fonts,
                baseline_metadata='identical', palette_crosscheck='236 central RGB triples identical',
                examples=examples, seconds=round(time.perf_counter() - started, 3))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', type=Path)
    args = parser.parse_args()
    try:
        print(json.dumps(verify(args.directory), indent=2))
    except (OSError, ValueError) as error:
        parser.exit(1, f'verify_local: {error}\n')


if __name__ == '__main__':
    main()

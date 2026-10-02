"""Inspect supported GOG 1.1 assets locally. Run: python3 -m tools.asset_inspector."""

import argparse
from html import escape
import json
from pathlib import Path
import tempfile

from cyberstorm.bitmap import Sprite
from cyberstorm.compression import unwrap
from cyberstorm.display import png_bytes
from cyberstorm.flx import Animation
from cyberstorm.font import Font
from cyberstorm.installation import Installation
from cyberstorm.palette import decode_palette

OUTPUT_ROOT = Path(__file__).resolve().parents[1] / 'local-research' / 'inspector'


def describe(archive, name):
    entry = archive.lookup(name)
    data = archive.read(name)
    decoded = unwrap(data)
    result = dict(name=name, envelope_offset=entry.offset,
                  payload_offset=entry.payload_offset, stored_bytes=entry.size,
                  pkx=data.startswith(b'PKX:'), decoded_bytes=len(decoded))
    ext = Path(name).suffix
    if ext in ('.BMX', '.ANX'):
        sprite = Sprite(data)
        result.update(frames=sprite.count, descriptors=[dict(width=f[1], height=f[2],
                      method=f[3], unknown_byte=f[4], unknown_word=f[5]) for f in sprite.frames])
    elif ext == '.FNX':
        font = Font(data)
        result.update(first_character=font.first, glyphs=font.count, height=font.height)
    elif ext == '.FLX':
        animation = Animation(data)
        result.update(frames=animation.count, stored_frames=len(animation.frames),
                      width=animation.width, height=animation.height,
                      chunk_types=sorted({k for cs in animation.frames for k, _, _ in cs}),
                      speed_word_unresolved=animation.speed_word)
    elif ext == '.PLX':
        decode_palette(decoded)
        result.update(colors=256, channel_order='RGB', fourth_byte='zero; meaning unresolved')
    else:
        result['decode_status'] = 'unsupported resource type'
    return result


def render(installation, archive_name, name, palette_ref, first, count):
    if first < 0 or not 1 <= count <= 16:
        raise ValueError('choose a nonnegative frame/glyph index and 1–16 frames')
    archive = installation.archive(archive_name)
    data = archive.read(name)
    ext = Path(name).suffix
    if ext not in ('.BMX', '.ANX', '.FNX', '.FLX'):
        raise ValueError(f'unsupported visual resource type: {ext}')
    diagnostic = ext == '.FNX'
    if diagnostic:
        # Inspection mapping only: nonzero stored indices shown white.
        palette = tuple((255, 255, 255) if i else (0, 0, 0) for i in range(256))
    else:
        if not palette_ref or ':' not in palette_ref:
            raise ValueError('visual resource requires --palette ARCHIVE.RBX:NAME.PLX')
        pal_archive, pal_name = palette_ref.split(':', 1)
        palette = decode_palette(installation.archive(pal_archive).read(pal_name))
    images = []
    if ext in ('.BMX', '.ANX'):
        sprite = Sprite(data)
        if first + count > sprite.count:
            raise ValueError('requested frames exceed sprite count')
        images = [(sprite.frame(i), palette) for i in range(first, first + count)]
    elif ext == '.FNX':
        font = Font(data)
        if first + count > font.count:
            raise ValueError('requested glyphs exceed font count')
        images = [(font.glyph(font.first + i), palette) for i in range(first, first + count)]
    elif ext == '.FLX':
        animation = Animation(data)
        if first + count > animation.count:
            raise ValueError('requested frames exceed FLX count')
        for i, frame in enumerate(animation.decode(palette)):
            if i >= first:
                images.append(frame)
            if i + 1 == first + count:
                break
    # Fixed ignored destination, unique run; never overwrite previous research.
    # Refuse symlinks in every output component to keep assets inside this tree.
    for directory in (OUTPUT_ROOT.parent, OUTPUT_ROOT):
        if directory.is_symlink():
            raise ValueError('output directory must not be a symlink')
        directory.mkdir(exist_ok=True)
    directory = Path(tempfile.mkdtemp(prefix=f'{archive_name}-{name}-', dir=OUTPUT_ROOT))
    for i, (image, colors) in enumerate(images):
        (directory / f'{i}.png').write_bytes(png_bytes(image, colors))
    label = escape(f'{archive_name} / {name}')
    note = ('Diagnostic font contrast: nonzero indices are white; original colors unresolved.'
            if diagnostic else 'Stored palette colors, opaque pixels. Transparency and game lighting unresolved.')
    page = f'''<!doctype html><html lang="en"><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{label} — local asset inspector</title>
<style>body{{font:16px system-ui;background:#171b23;color:#eee;margin:24px;max-width:1100px}}
img{{image-rendering:pixelated;max-width:100%;height:auto;background:#000;border:1px solid #667}}
button,input{{font:inherit;padding:8px}} .controls{{display:flex;gap:12px;align-items:center;flex-wrap:wrap}}
p{{line-height:1.5}}a{{color:#9ce}}</style>
<h1>{label}</h1><p>Local proprietary research output — do not distribute.</p>
<p>{note} Frames are in stored order; no playback timing is implied.
FLX deltas start from a zero canvas and are displayed top-down.</p>
<div class="controls"><button id="prev">Previous</button>
<label>Frame / glyph <input id="frame" type="range" min="0" max="{len(images)-1}" value="0"></label>
<button id="next">Next</button><output id="status" aria-live="polite"></output></div>
<p><img id="image" src="0.png" alt="Decoded resource frame"></p>
<p><a href="../">Local inspection runs</a></p>
<script>
const slider=document.getElementById('frame'), picture=document.getElementById('image');
function show(n){{slider.value=Math.max(0,Math.min({len(images)-1},n));
picture.src=slider.value+'.png';
document.getElementById('status').textContent='Stored index '+(Number(slider.value)+{first})+' / '+{first+len(images)-1};}}
slider.oninput=()=>show(Number(slider.value));
document.getElementById('prev').onclick=()=>show(Number(slider.value)-1);
document.getElementById('next').onclick=()=>show(Number(slider.value)+1);show(0);
</script></html>'''
    path = directory / 'index.html'
    path.write_text(page, encoding='utf-8')
    return path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', type=Path)
    commands = parser.add_subparsers(dest='command', required=True)
    commands.add_parser('verify')
    listing = commands.add_parser('list')
    listing.add_argument('--archive')
    for cmd in ('info', 'render'):
        sub = commands.add_parser(cmd)
        sub.add_argument('archive')
        sub.add_argument('resource')
        if cmd == 'render':
            sub.add_argument('--palette')
            sub.add_argument('--first', type=int, default=0)
            sub.add_argument('--count', type=int, default=1)
    args = parser.parse_args()
    try:
        with Installation(args.directory) as installation:
            if args.command == 'verify':
                print('Verified exact GOG 1.1 archive set: 4 archives, 1787 resources')
            elif args.command == 'list':
                archives = ([installation.archive(args.archive)] if args.archive
                            else installation.archives.values())
                for archive in archives:
                    for entry in archive.entries:
                        print(f'{archive.path.name}\t{entry.name}\t{entry.size}')
            elif args.command == 'info':
                print(json.dumps(describe(installation.archive(args.archive), args.resource), indent=2))
            else:
                print(render(installation, args.archive, args.resource, args.palette, args.first, args.count))
    except (OSError, ValueError) as error:
        parser.exit(1, f'asset_inspector: {error}\n')


if __name__ == '__main__':
    main()

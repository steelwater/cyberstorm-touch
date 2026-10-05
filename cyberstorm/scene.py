"""Bounded renderer-facing scene assembly; no windowing or gameplay state."""

from dataclasses import dataclass
import json
import math
from pathlib import Path

from .bitmap import Image, Sprite
from .flx import Animation
from .palette import decode_palette
from .viewport import hex_origin, hex_outline

MAX_FRAME_PIXELS = 4 * 1024 * 1024
MAX_SCENE_PIXELS = 16 * 1024 * 1024  # At most 64 MiB of RGBA texture source data.


@dataclass(frozen=True)
class Frame:
    image: Image
    palette: tuple


@dataclass(frozen=True)
class Asset:
    frames: tuple[Frame, ...]
    anchor: tuple[float, float]
    key: int | None
    fps: float


@dataclass(frozen=True)
class Placement:
    asset: str
    position: tuple[float, float]
    frame: int | None  # None plays the asset's diagnostic timeline.


@dataclass(frozen=True)
class Scene:
    title: str
    assets: dict[str, Asset]
    terrain: tuple[Placement, ...]
    objects: tuple[Placement, ...]
    outlines: tuple
    center: tuple[float, float]
    reference: tuple[float, float]


def fields(value, required):
    if not isinstance(value, dict) or set(value) != set(required):
        raise ValueError(f'expected fields: {", ".join(required)}')


def number(value, label, low, high, integer=False):
    if (type(value) not in (int, float) or not low <= value <= high
            or not math.isfinite(value) or (integer and type(value) is not int)):
        raise ValueError(f'{label} must be {"an integer" if integer else "a number"} in {low}..{high}')
    return value


def pair(value, label, low=-100000, high=100000):
    if not isinstance(value, list) or len(value) != 2:
        raise ValueError(f'{label} must be a two-number array')
    return tuple(number(v, label, low, high) for v in value)


def reference(value):
    if not isinstance(value, str) or value.count(':') != 1:
        raise ValueError('resource reference must be ARCHIVE.RBX:RESOURCE.EXT')
    archive, resource = value.split(':')
    if not archive or not resource or any(c in value for c in '/\\'):
        raise ValueError('resource reference must use archive lookup names, not paths')
    return archive, resource


def load_scene(path, installation):
    """Load metadata only from JSON; proprietary bytes come from validated archives."""
    path = Path(path)
    with path.open('rb') as source:
        data = source.read(256 * 1024 + 1)
    if len(data) > 256 * 1024:
        raise ValueError('scene manifest exceeds 256 KiB')
    try:
        description = json.loads(data)
    except (ValueError, UnicodeError) as error:
        raise ValueError(f'invalid scene JSON: {error}') from error
    try:
        return assemble(description, installation)
    except (ValueError, OSError) as error:
        raise ValueError(f'{path.name}: {error}') from error


def assemble(description, installation):
    fields(description, ('version', 'title', 'camera', 'assets', 'terrain', 'objects'))
    if type(description['version']) is not int or description['version'] != 1:
        raise ValueError('unsupported scene version')
    title = description['title']
    if not isinstance(title, str) or not 1 <= len(title) <= 120:
        raise ValueError('scene title must be 1..120 characters')
    camera = description['camera']
    fields(camera, ('center', 'reference'))
    center = pair(camera['center'], 'camera center')
    view = pair(camera['reference'], 'reference size', 1, 16384)
    definitions = description['assets']
    if not isinstance(definitions, dict) or not 1 <= len(definitions) <= 32:
        raise ValueError('scene must define 1..32 assets')
    assets = {}
    total_pixels = 0
    for identifier, definition in definitions.items():
        if not isinstance(identifier, str) or not 1 <= len(identifier) <= 64:
            raise ValueError('asset identifier must be 1..64 characters')
        try:
            fields(definition, ('resource', 'palette', 'frames', 'anchor', 'key', 'fps'))
            archive, resource = reference(definition['resource'])
            pa, pn = reference(definition['palette'])
            indexes = definition['frames']
            if not isinstance(indexes, list) or not 1 <= len(indexes) <= 240:
                raise ValueError('asset must select 1..240 frames')
            for index in indexes:
                number(index, 'frame index', 0, 4095, integer=True)
            if len(set(indexes)) != len(indexes) or indexes != sorted(indexes):
                raise ValueError('frame indexes must be unique and in stored order')
            anchor = pair(definition['anchor'], 'anchor')
            key = definition['key']
            if key is not None:
                number(key, 'transparency index', 0, 255, integer=True)
            fps = number(definition['fps'], 'diagnostic fps', 0.1, 60)
            palette = decode_palette(installation.archive(pa).read(pn))
            raw = installation.archive(archive).read(resource)
            if resource.endswith(('.BMX', '.ANX')):
                sprite = Sprite(raw)
                if indexes[-1] >= sprite.count:
                    raise ValueError('selected frame exceeds sprite count')
                sizes = [sprite.frames[i][1] * sprite.frames[i][2] for i in indexes]
                decoder = ((sprite.frame(i), palette) for i in indexes)
            elif resource.endswith('.FLX'):
                animation = Animation(raw)
                if indexes[-1] >= animation.count:
                    raise ValueError('selected frame exceeds FLX count')
                if indexes[-1] >= 240:
                    raise ValueError('FLX decode prefix exceeds 240 frames')
                sizes = [animation.width * animation.height] * len(indexes)
                # Use the single reader's accumulated pixels and per-frame palette.
                def selected_frames():
                    for i, decoded in enumerate(animation.decode(palette)):
                        if i in indexes:
                            yield decoded
                        if i == indexes[-1]:
                            break
                decoder = selected_frames()
            else:
                raise ValueError('unsupported scene resource type')
            total_pixels += sum(sizes)
            if max(sizes) > MAX_FRAME_PIXELS or total_pixels > MAX_SCENE_PIXELS:
                raise ValueError('decoded scene exceeds pixel budget')
            frames = tuple(Frame(image, colors) for image, colors in decoder)
            if any(f.image.width > 4096 or f.image.height > 4096 for f in frames):
                raise ValueError('texture dimension exceeds 4096 pixels')
            assets[identifier] = Asset(frames, anchor, key, fps)
        except (ValueError, OSError) as error:
            raise ValueError(f'asset {identifier}: {error}') from error

    grid = description['terrain']
    fields(grid, ('asset', 'columns', 'rows'))
    asset_id = grid['asset']
    if not isinstance(asset_id, str) or asset_id not in assets:
        raise ValueError('terrain references an unknown asset')
    columns = number(grid['columns'], 'columns', 1, 64, integer=True)
    rows = number(grid['rows'], 'rows', 1, 64, integer=True)
    if rows * 64 + (32 if columns > 1 else 0) > 4096:
        raise ValueError('terrain composite exceeds 4096 pixels per axis')
    ground = assets[asset_id]
    if ground.anchor != (0, 0) or any((f.image.width, f.image.height) != (64, 64) for f in ground.frames):
        raise ValueError('terrain requires 64x64 frames with top-left anchors')
    terrain, outlines = [], []
    for column in range(columns):
        for row in range(rows):
            origin = hex_origin(column, row)
            terrain.append(Placement(asset_id, origin, (column + row) % len(ground.frames)))
            outlines.append(hex_outline(origin))
    objects = description['objects']
    if not isinstance(objects, list) or len(objects) > 256:
        raise ValueError('scene permits at most 256 objects')
    placements = []
    for item in objects:
        fields(item, ('asset', 'position', 'frame'))
        identifier = item['asset']
        if not isinstance(identifier, str) or identifier not in assets:
            raise ValueError('object references an unknown asset')
        frame = item['frame']
        if frame is not None:
            number(frame, 'object frame', 0, len(assets[identifier].frames) - 1, integer=True)
        placements.append(Placement(identifier, pair(item['position'], 'object position'), frame))
    # Explicit ground-contact order; stable ties preserve manifest order.
    placements.sort(key=lambda item: item.position[1])
    return Scene(title, assets, tuple(terrain), tuple(placements), tuple(outlines), center, view)

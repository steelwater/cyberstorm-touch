# Milestone 2 — Battlefield renderer

Date: 2026-10-05 (Asia/Tokyo). Owner: Dan. Implementation/research: Codex.
Repository: https://github.com/steelwater/cyberstorm-touch.
Authority: [Crew Brief](https://docs.google.com/document/d/1GXnwIC6cRotZYDzFHh5d4-XAH9mmpuZ1kK2Kl8YYKsc/edit),
[roadmap](https://docs.google.com/document/d/1MhOmbCskBofRm592bZJAYqpExaWW33bZh1Xu51Up3N8/edit),
and the [Milestone 1 handoff](https://drive.google.com/file/d/1Ph9aKcBBKNEqMJ_de7aVCicZnV_k9d_F/view).
Stack: [approved decision](milestone-2-stack.md), mirrored to the
[canonical Drive project folder](https://drive.google.com/file/d/1vZuxuZw5jaoSfVuc_htcA0bRkyA4PLhr/view).

## Status and scope

Local implementation and macOS rendering proof are available on
`codex/milestone-2-battlefield-renderer`, starting from clean, fetched `main` at
`16b7e02` after Milestone 1 merged. On 2026-10-05, Dan reviewed the rendered
output, reported that it was good, and authorized Uplink. This records visual
acceptance of the shown macOS scene; it does not establish additional platform or
control checks. Windows/Linux native visual checks and true 2× high-DPI hardware
verification remain outstanding. **The milestone is not fully signed off.**
Uplink commit, PR and CI results are recorded in the
[canonical implementation handoff](https://drive.google.com/file/d/1H1IgYr7wwi0YSO3T8AeQl1g522oGulB1/view).
No merge, release or deployment is included in Uplink.

LogicPass: assemble the smallest coherent visual scene from proven reader outputs;
isolate scene data, camera/scaling/timing and SDL window/texture operations. Risks:
unproven transparency/anchors, fractional tile cracks, unbounded frame allocation,
experimental SDL adapter API, and accidentally redistributing decoded assets.
Proof uses generated fixtures plus ignored local original-data checks. No original
reader behavior needed changing. No simulation, map import, navigation, selection,
touch, audio, packaging or UI framework was added.

## Representative resources and evidence

The manifest `scenes/representative.json` contains resource names, frame indexes
and project-authored positions only. It is a constructed visual proof, not an
original mission/map reconstruction.

| Role | Archive/resource | Frames | Placement/key policy |
| --- | --- | --- | --- |
| Terrain | CYBDATA4.RBX / S1P1.BMX | 27, 28, 29; 64×64 | Top-left; selected index 0 keyed |
| Rocks | CYBDATA4.RBX / S1P1.BMX | 60, 61, 62; 64×64 | Authored anchor (32,48); index 0 keyed |
| HERC | CYBDATA1.RBX / HRC001B0.ANX | 0; 53×44 | Authored ground-contact anchor (27,43); index 0 keyed |
| Effect | CYBDATA2.RBX / FX001.BMX | 0–30; 100×100 | Authored canvas center (50,50); index 0 keyed; 10 fps loop |
| Palette | CYBDATA1.RBX / S1P1.PLX | 256 RGB entries | Explicit scene choice, not universal palette binding |

**Terrain and transparency:** terrain frames 0, 27, 28 and 29 have identical nonzero
footprints. Rows span 32 pixels at the top/bottom and 64 in the middle. Columns
spaced 48 pixels apart, with alternate columns shifted 32 pixels vertically and
rows spaced 64 pixels apart, cover the tested 192×192 interior exactly once when
index 0 is omitted: no overlaps or holes. Local opaque contact sheets show the
same blue matte around selected terrain, rock silhouettes, HERC and effect pixels.
Local composites preserve the terrain under those matte areas and retain the
visible object details. This independently supports index 0 as a key for **these
selected resources**. The adapter has no global default transparent index: null
means fully opaque, and keying compares indexes rather than equal RGB values.
Original runtime transparency rules for other resources remain unproven.

**Method 13:** BGGRNHEX.BMX is a 640×480 single-frame method-13 resource. It still
fails explicitly. The selected terrain set uses supported raw/method-1 frames,
so no permissive method-13 decoder or embedded-palette scan was needed. The
[Museum format reference](https://github.com/TeamCorgo/The-CyberStorm-Museum/blob/latest/tools/file%20specifications/anx_bmx.md)
does not settle this codec or the reserved descriptor fields. No third-party
decoder source was adopted. The filename alone did not establish a required tile.

**Anchors:** the HERC descriptor's last word can be split into plausible coordinate
bytes, but that is insufficient to establish original hotspot semantics. The
renderer does not interpret it. The manifest instead explicitly registers the
selected static sprite's visible lower extent to a scene point. Rocks and effect
use explicit canvas offsets. Correct original multi-facing registration remains
unknown; this milestone makes no facing labels or movement claims.

**Animation:** selected effect frames play in stored order at a diagnostic 10 fps,
looping independently of simulation. No original duration or loop semantics are
claimed. FLX assets route through `Animation.decode(palette)`, keeping its top-down
images and per-frame palette snapshots. A separate ignored local manifest checked
BGMSH25A.FLX at indexes 0,30,60,89, with no key. Its visible content is a portrait,
not a battlefield explosion; it is deliberately absent from the battlefield scene.
The earlier Milestone 1 explosion characterization does not apply to that resource.

## Contracts and limits

* `scene.py`: strict version-1 JSON schema; exact `ARCHIVE.RBX:RESOURCE.EXT` lookups;
  immutable indexed `Frame`, `Asset` and `Placement` values. Sprite frames use
  `Sprite.frame`; FLX frames use `Animation.decode`. No decoder duplication.
* World coordinates are top-down source pixels, +x right, +y down. Grid geometry
  uses the observed footprint. Object draw order is increasing authored ground y,
  with stable manifest order for ties. No occupancy or movement meaning is attached.
* `viewport.py`: camera center and zoom, uniform world-to-screen transform,
  endpoint-rounded draw rectangles, integer fit above 1× and fractional fallback
  below 1×. Fractional mode removes integer snapping. Camera center stays fixed
  on resize; wider views show extra world space. HUD-safe width is centered and
  capped at 16:9; there is no HUD implementation.
* `Timeline`: elapsed seconds, pause and modulo frame selection, independent of
  game-turn state. The window loop limits redraws to 60 Hz.
* `pygame_renderer.py`: only pygame imports, SDL window/events, explicit indexed
  RGBA conversion, nearest textures and drawable-size queries. Static terrain is
  composed once at native resolution before scaling; this prevents fractional
  transparency cracks. Object/effect textures remain separate cached draws.
* Limits: 256 KiB manifest, 32 assets, 240 selected frames per asset, FLX decode
  prefix at most 240 frames, 4 Mi pixels per frame, 16 Mi selected pixels per scene,
  4096-pixel texture axes, 64×64 grid bounds (subject to composite dimension cap),
  and 256 objects. The static terrain composite has a separate 4096×4096 maximum.
  Unsupported/corrupt resources fail with asset context. No best-effort substitute
  artwork is returned. The existing exact-installation and reader bounds remain.

## Verification

Commands from the repository root (the verification venv is local/ignored):

```sh
local-research/milestone-2-venv/bin/python -m unittest discover -s tests -v
local-research/milestone-2-venv/bin/python -m compileall -q cyberstorm tools tests
python3 -m tools.verify_local local-research/gog-1.1
local-research/milestone-2-venv/bin/python -m tools.battlefield local-research/gog-1.1 --check
local-research/milestone-2-venv/bin/python -m tools.battlefield local-research/gog-1.1
```

All 47 generated tests passed locally, with no skips; syntax compilation and
`git diff --check` passed. The suite includes all 26 unchanged Milestone 1 tests plus scene schema,
lookup, corrupt/unsupported data, pixel-budget, FLX adaptation, geometry, timing,
five aspect ratios and actual SDL texture/pixel-composition tests. A regression
checks fractional hex coverage after the initial native render revealed cracks.
CI installs the pinned dependency and retains the existing Windows/macOS/Linux ×
Python 3.11/3.14 matrix and job identity. SDL tests use dummy video/software rendering;
CI is not a substitute for native GPU/window verification. Remote CI has not run
at the initial local verification point; Uplink results are recorded in the
canonical handoff and PR checks. No type-checker, linter or separate build is configured.

The local original-data regression returned identical baseline metadata for all
1,787 resources, all 886 PKX wrappers, 30 regular palettes and six fonts; the RGB
cross-check remained identical. The scene loads 77 hexes, five object placements
and 38 decoded frames (336,908 indexed pixels; 1,347,632 RGBA bytes before the terrain
composite). The unchanged inspector remains available.

Native SDL rendering on this Mac exercised resize, fullscreen/windowed transitions,
zoom/reset, grid toggle, pause/resume and frame advancement. Local renderer captures
were visually inspected for terrain orientation, palette, keying and placement.

| Native window/drawable size | Case | Observed scale |
| --- | --- | --- |
| 800×600 | 4:3 | 1× |
| 960×540 | 16:9 | 0.99265× fallback |
| 960×600 | 16:10 | 1× |
| 1260×540 | 21:9 | 0.99265× fallback |
| 1536×432 | 32:9 | 0.79412× fallback |
| 701×501 | Fractional mode | 0.92096× |
| 1280×1088 | Integer mode | 2× |

All use uniform scale, with no horizontal stretching. The native drawable/window
ratio observed was 1.0 even with high-DPI requested. A generated test covers 2×
drawable math, but an actual 2× high-DPI monitor remains an explicit unrun check.
Windows/Linux native visual tests are unrun because this session has only macOS.

Observed on Python 3.14.7, pygame-ce 2.5.8, SDL 2.32.10: an uninstrumented scene
load took 0.307 s; tracemalloc measured about 2.22 MB peak Python allocation during
load (excludes SDL/VRAM). The terrain composite is 544×480, about 1.04 MB RGBA.
A native 180-frame sample had ~10 ms median draw+present time with grid off and
~20 ms maximum after the seam fix. This includes driver presentation behavior,
not just GPU rendering, and is not a frame-rate guarantee or whole-map benchmark.

## Remaining work, safeguards and handoff

| Area | Remaining boundary |
| --- | --- |
| Terrain | Method 13 and other sets not resolved; only the selected flat tile set is used |
| Palette/key | Original palette selection, remapping, lighting and universal key rules unknown |
| Anchors/facing | Explicit scene registration only; original metadata interpretation unproven |
| Timing | Diagnostic loop; no original timing or effect/audio synchronization |
| Platforms | Windows/Linux native checks and true 2× high-DPI hardware pending; macOS output accepted by Dan; CI tracked in Uplink |
| Performance | Small cached scene; whole-map texture chunking/streaming not designed |

Original data, contact sheets, renderer captures, investigation scripts and the
verification environment remain under ignored `local-research/`. Only source,
generated fixtures, resource names/metadata and documentation belong in the diff.
The original executable was never run. No assets were uploaded or packaged.

Next: complete the authorized Uplink and First Officer review, then finish the
outstanding desktop verification before marking Milestone 2 complete. Milestone 3 should start
from the coordinate/viewport/placement contracts, add tested inverse transforms
and map bounds, then selection and navigation without coupling them to SDL.
The static terrain composite suits this small proof; reevaluate chunking only
when larger map navigation gives a concrete requirement.

Rollback: `main` at `16b7e02` is untouched. Work is isolated on the feature branch;
no proprietary input, previous research output, tag, release or backup was changed
or deleted. No cleanup or destructive rollback operation was performed.

# Milestone 1 — Data and Asset Reader

Date: 2026-10-02 (Asia/Tokyo). Owner: Dan. Implementation/research: Codex.
Authority: [Crew Brief](https://docs.google.com/document/d/1K1lWGqCYZNJgSGXqXQ5zwlU58M5HzIg_wXg42jb4OhQ/edit),
[roadmap](https://docs.google.com/document/d/1MhOmbCskBofRm592bZJAYqpExaWW33bZh1Xu51Up3N8/edit),
and the [Milestone 0 baseline](gog-1.1/inventory.md).

## Outcome and verification boundary

Project code independently opens the supported installation, enumerates 1,787
resources, decodes all 886 PKX wrappers, reads 30 regular PLX palettes and all six
FNX tables, and exports representative BMX/ANX/FLX/font images for local inspection.
No original executable was run. The reader and PNG visual proof work; browser
control interaction and responsive layout verification remain blocked because the
available browser automation rejects `file://` URLs. Captain verification of the
local HTML viewer is still required before final milestone acceptance.

The project was not a Git repository at preflight. Ignore rules were verified,
Milestone 0 was preserved as baseline commit `544d053` on `main`, and work continued
on `feature/milestone-1-asset-reader`. Dan explicitly authorized a public repository
and selected GPL-3.0. The repository is https://github.com/steelwater/cyberstorm-touch.
No installer, extracted resource, decoded pixel, palette value, audio, game text,
or proprietary binary was added to source control. Original fixture data is never
needed by CI. The earlier research metadata remains unchanged.

## LogicPass and boundaries

Outcome: bounded, separable readers plus a small local inspector, using the existing
standard-library Python approach. Change surface: `cyberstorm/` reader modules,
existing RBX probe, inspector and local verification tools, generated tests, CI,
README, and format notes. Proof: preserve the complete Milestone 0 metadata result;
validate original wrappers and selected complete visual sequences locally; test
malformed/generated data; visually inspect decoded output and RGB/BGR alternatives.

Risks addressed: malformed lengths/offsets/counts, decompression growth, reading
across resource boundaries, unsupported variants mistaken for valid images,
proprietary output leakage, and reference specifications overstating semantics.
No production stack, data storage policy, game simulation, Android importer,
rendering engine, audio subsystem, or generalized animation layer was introduced.

## Evidence and reference use

The Museum's textual specifications were consulted as research leads:
[ANX/BMX](https://github.com/TeamCorgo/The-CyberStorm-Museum/blob/latest/tools/file%20specifications/anx_bmx.md),
[FNX/PKX](https://github.com/TeamCorgo/The-CyberStorm-Museum/blob/latest/tools/file%20specifications/fnx.md),
[PLX](https://github.com/TeamCorgo/The-CyberStorm-Museum/blob/latest/tools/file%20specifications/plx.md),
and [FLX](https://github.com/TeamCorgo/The-CyberStorm-Museum/blob/latest/tools/file%20specifications/flx.md).
No third-party decompressor source was copied or adopted; implementations were
written from structural descriptions and checked against supplied local data and
generated fixtures. No preservation game assets were downloaded.

These descriptions are not authoritative for every detail: their general claims
about wrapped PLX/FLX files disagree with this installation; one LZ loop description
also disagrees with the bytes. Our measured contract and explicit failures govern.
Fourth-byte palette meaning, reserved-slot rendering, transparency, lighting,
playback rate, and original font effects remain external claims or unresolved.

## Confirmed reader contracts

All format integers are little-endian; PNG output uses standard big-endian chunks.

### RBX

The Milestone 0 layout is unchanged: signature `9e 9a a9 0b`, u32 count, count ×
(12-byte padded ASCII DOS-style name + u32 absolute envelope offset). Each envelope
contains a u32 payload length; embedded data begins four bytes later. Physical
records must cover the entire region after the index contiguously without gaps,
overlaps, duplicate offsets, or trailing data. Case-insensitive duplicate names
are rejected; lookup itself requires the exact stored name.

`Archive` holds a seekable file open and reads only the index and length words at
construction. Immutable entries expose envelope and payload offsets separately.
`read(name, offset=..., size=...)` cannot cross a resource boundary. Default reads
are limited to 32 MiB and indexes to 100,000 entries. Inputs must remain unchanged
while open. The installation validator additionally checks the exact four baseline
sizes and SHA-256 values, rejecting patched/other-release archives rather than
claiming unverified compatibility.

The legacy probe now uses this module. Its complete JSON result matches all four
checked-in Milestone 0 metadata files exactly, including every payload hash.

### PKX

| Offset | Verified role in supplied data |
| --- | --- |
| 0 | `PKX:` signature |
| 4, 8 | Fixed signature constants `0x10011966`, `0x9baebacf`; deeper meanings unknown |
| 12 | Decoder selection: 14 for 885 resources; 1 for `FX017.BMX` |
| 16 | Stored byte count, exactly resource length minus 24 |
| 20 | Decoded byte count, verified for all 886 resources |
| 24 | Compressed stream |

Method 14 is an LZ-style stream with overlapping back-references. Header low three
bits specify the final partial group's token count. For a header below 8, the next
u16 is the number of full groups; 65535 escapes to a u32 count. Otherwise the upper
five bits minus one give the full group count. A flag byte precedes each group,
processed MSB-first: zero copies a literal; one reads a u16 token with distance
`(word >> 4) + 1` and length `(word & 15) + 3`. Distances must reference existing
output. There is **no extra flag byte when the partial count is zero**. Treating the
partial group as always eight tokens or adding one to its token count fails real
samples. Exact stream consumption and exact declared output succeeded for all 885.

Method 1 packets use low-seven-bit counts: high bit clear means literals, high bit
set means repeat the next byte. Zero count terminates. Exact output and a final
terminator are required with no trailing bytes. Verified on `FX017.BMX` and the
selected sprite frames. Alternative PKX methods/signature variants are unsupported.
Input and output have 32 MiB ceilings; PKX declared output must be positive. The LZ
u32 count extension is generated-test covered but not separately claimed as an
observed original-file feature.

### Regular PLX

Exactly 1,024 bytes, 256 records of four bytes. All thirty observed palettes have
zero fourth bytes. The reader returns the first three as **RGB**, while rejecting
nonzero fourth-byte variants and other lengths. It does not interpret the fourth
byte as alpha or flags. `BGMPALS.PLX` remains unsupported (13,320-byte shape).

Independent local cross-check: the first `BGMS.FLX` frame has a type-4 RGB palette
packet; its 236 central triples match `SIMGUI.PLX` entries 10–245 exactly. Rendering
that frame with regular PLX in RGB order gives natural warm human skin, green
indicators and red hex outlines. Reversing red/blue gives blue faces and blue hexes.
Both alternatives were rendered and visually inspected locally. This supports
stored RGB order; it does **not** prove Windows reserved-slot replacement or any
transparency/dynamic-lighting rule. No palette values or reference images are
included in this document or repository.

### BMX and ANX

After optional PKX: u32 descriptor count, then 12 bytes per descriptor. A descriptor
contains i32 offset relative to its own start, u16 width, u16 height, an unknown byte,
a method byte, and an unknown u16. Selected raw/method-1 streams produce exactly
width × height row-major index bytes. The next distinct pixel offset (or EOF) bounds
the stream. No speculative embedded-palette scanning or codec fallback is used.

Proof samples: `DMGMIN16.BMX`, six 107×96 silhouette frames; `HRC001B0.ANX`, six HERC
views sized 53×44, 65×54, 53×58, 50×55, 66×40, 51×45. All frames decode; contact sheets
were inspected in descriptor order. The sample palette `S1P1.PLX` is an explicit
inspection choice, not a proven universal original-game binding. ANX frame ordering
is confirmed as stored views; facing labels, offsets/hotspots, playback timing,
damage-color remapping, and transparency remain unknown. Other sprite methods,
including the method-13 candidate in `BGGRNHEX.BMX`, are rejected explicitly.

### FLX

The supported raw header is 128 bytes: u32 total length at 0, u16 magic `0xaf20` at 4,
u16 nominal frame count at 6, u16 width/height at 8/10, depth 8 at 12. Speed and
flags are exposed as uninterpreted words. Frames begin at 128, with u32 length,
u16 `0xf1fa`, u16 chunk count, and eight verified zero bytes. Chunks have a u32
length including their six-byte header and a u16 type. Every nested range is checked;
no truncated frame is silently dropped. Nominal count or count+1 stored frames are
accepted; the extra frame is inspected structurally and omitted from previews,
without claiming its original loop semantics.

Implemented observed chunks: 4 (RGB palette packets), 100 (literal/fill/skip stream),
102 (bounded rectangle metadata), 104 (LZ followed by the same run stream).
Run skips preserve prior pixels. Controls 1–127 copy literals; 0 reads count/value;
129–255 skip low-seven-bit count. Control 128 reads a u16: zero terminates, below
0x8000 skips, 0x8000–0xbfff copies low-14-bit literals, 0xc000–0xffff repeats the next
byte. Exact terminator/stream consumption required. Unsupported chunks fail.

Proof: all four nominal `HB_AMB1.FLX` frames (640×480) exercise types 100/102/104;
all 90 `BGMSH25A.FLX` frames (112×112) exercise types 4/100/102; all 90 `BGMS.FLX`
frames (640×480) also decode. BGMS portraits visibly establish bottom-up storage;
rows are flipped only when exposing an `Image` to the viewer. Explosion progression
was inspected at multiple stored indexes. Initial canvas is zero, with a supplied
baseline palette; original scene compositing, keyframe/loop rules, audio, timing,
and additional chunk types remain unimplemented. Palette index zero is not forcibly
rewritten because its original runtime treatment has not been independently proven.

### FNX

After PKX, `FNX:` followed by a 40-byte header. Observed format word at 4 is
`0x00080000`; word at 8 is unknown; glyph height is at 12; word at 16 remains unknown.
First character/count are at 20/24; absolute offset-table/width-table/bitmap offsets
are at 28/32/36. The supported layout has count × u32 bitmap-relative offsets at 40,
then 256 byte widths indexed by character code, then width × height index pixels
for each glyph. Table and glyph bounds are checked for all six original fonts.

`FONT10.FNX` has 11 stored character codes starting at 48 and height 24. Codes 48–57
visually read as digits 0–9 using an explicitly diagnostic nonzero-to-white mapping.
Glyph color remapping, spacing/advance behavior, effects and packed-bit variants
remain unresolved. No font-layout or game-UI subsystem was introduced.

## Verification and remaining unknowns

Commands (repository root):

```sh
python3 -m unittest discover -s tests -v
python3 -m compileall -q cyberstorm tools tests
python3 -m tools.verify_local local-research/gog-1.1
python3 -m tools.asset_inspector local-research/gog-1.1 verify
python3 -m tools.asset_inspector local-research/gog-1.1 list
```

Local integration returned 1,787 resources, 886 decoded PKX wrappers, 30 regular
palettes, six valid fonts, identical baseline metadata and the 236-color palette
cross-check. One observed wall time was 8.903 seconds for the full sequential check
on this development Mac; this is not a cross-platform performance guarantee.
Archive listing avoids loading the 165 MB largest archive; resource/decoded limits
are 32 MiB. The viewer limits each export to 16 selected frames. No peak-memory
benchmark has been claimed. FLX decode yields frames incrementally; callers should
consume iteratively rather than collecting complete long animations.

26 generated-fixture tests cover index-only reading, exact/sliced lookup,
corruption/truncation, PKX methods and bounds, palette shape/order, sprite decoding,
font tables, FLX delta retention/row orientation/chunks, PNG integrity, installation
identity, rendering and CLI diagnostics. Syntax compilation passes. CI runs the
same tests and compilation on three desktop OSes and two Python versions. The
repository has no configured third-party lint/typecheck/build toolchain.

Focused CLI failure checks passed: missing installation/resource, BGMPALS, missing
palette selection, out-of-range frames, and unsupported sprite method. Errors return
nonzero, stderr, and no success output. PNG output was visually inspected, including
HERC ordering, font digits, FLX orientation and RGB/BGR comparison. HTML controls,
responsive layouts and direct Windows/Linux visual inspection remain unverified;
the browser tool denied local file navigation. Do not count this as a full manual
viewer pass or Captain acceptance.

| Area | Confirmed subset | Remaining boundary |
| --- | --- | --- |
| RBX | Exact original four archives, all entries | Other releases/patched archives; concurrent file modification unsupported |
| PKX | All 886 observed wrappers | Other methods/constants; no checksum inside codec |
| PLX | Thirty regular palettes, RGB order | Fourth-byte meaning, BGMPALS, runtime reserved colors |
| BMX/ANX | Representative full frame sets | Other codecs, palette binding, transparency, anchors, timing |
| FLX | Three sequences and four chunk types | Other chunk types, original compositing/timing/loops |
| FNX | Six bounded 8-bit tables, digit visual proof | Original colors/effects/layout, packed-bit variants |
| Inspector | CLI + generated PNG/HTML | Browser controls/responsive manual acceptance |

## Milestone 2 handoff and rollback

Smallest interfaces: `Archive.lookup/read`; `unwrap`; `decode_palette` returning
256 RGB triples; immutable `Image(width, height, pixels)`; `Sprite.frame(index)`;
`Animation.decode(palette)` yielding top-down index images and palette snapshots;
`Font.glyph(code)`. Keep these independent of future simulation and input.

Recommendation, not an approved next mission: verify the local HTML viewer, then
resolve terrain sprite method 13/embedded palette handling, transparency and anchors
before choosing representative battlefield assets. Current image sizes and decode
proof justify a small renderer experiment but do not establish the final window,
rendering, input, audio, or Android stack. No production-stack choice is made here.

Rollback: the baseline commit remains available, original installer/extraction were
not changed, and new research outputs are additive and ignored. No branch cleanup,
merge, release, deployment, or asset deletion is part of this milestone.

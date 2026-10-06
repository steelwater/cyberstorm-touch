# Milestone 3 — Hex map and camera

Date: 2026-10-06 (Asia/Tokyo). Owner: Dan. Implementation: Codex.
Authority: [Milestone 3 Crew Brief](https://docs.google.com/document/d/1EZPYpq-W-xdpwKoIuPqLhAigNUQ4RLYBbWeuNFL-s14/edit)
and [roadmap](https://docs.google.com/document/d/1MhOmbCskBofRm592bZJAYqpExaWW33bZh1Xu51Up3N8/edit).
Branch: `codex/milestone-3-hex-map-camera`, based on fetched `main` at `0149c1d`.

## Implementation and boundaries

LogicPass outcome: inspect the existing battlefield, pan/zoom predictably and
select valid hex locations with mouse or touch. Smallest change surface: shared
hex geometry, camera transforms/bounds, gesture state, the existing SDL adapter,
generated tests and usage documentation. Risks: coordinate disagreement, high-DPI
input mismatch, pinch/tap confusion, edge clamping and integer zoom discontinuities.
Proof: numeric invariants, input sequences, SDL events/pixels and native playtesting.

`hexmap.Hex(column, row)` is the authoritative odd-column offset representation.
It retains the observed Milestone 2 64×64 footprint, 48-pixel column spacing and
32-pixel odd-column stagger. Scene assembly, outlines and picking use the same
model. These are authored diagnostic map coordinates, not a claim about the
original mission file schema. Picking tests neighboring polygons against explicit
map membership. Exact shared edges choose the lowest column, then row; empty
space, holes and scalloped outside corners do not select invented cells.

`Viewport` owns both world/drawable transforms. `Camera` owns uniform scale, pan,
zoom and terrain bounds, with no SDL/input dependency. It clamps each axis to the
terrain bounding box; if the visible span exceeds that axis, it centers the map.
This deliberately permits symmetric margins and the hex perimeter's empty
scallops rather than cropping legitimate edge hexes. Objects do not enlarge map
bounds. Zoom stays within 0.25–4 times the reference fit; the title shows actual
pixel scale, which can exceed 4 on large displays. Cursor/midpoint anchoring yields
to bounds when both constraints cannot be satisfied.

`Navigation` owns selection and gesture state in logical window points. The SDL
adapter converts normalized finger positions to those points, and Navigation maps
them to drawable pixels before invoking Camera. An 8-point threshold suppresses
jitter. Once a gesture becomes a drag or contains multiple fingers, releasing it
cannot select. A remaining finger after a pinch continues panning without a jump;
more than two fingers suspend camera changes until two remain. Focus loss, pointer
exit, resize, fullscreen changes and keyboard scale changes discard transient
gestures without clearing the selected hex. SDL touch-generated mouse events are
ignored to prevent duplicate input. Selection is drawn after objects and remains
visible with the grid disabled; the title includes zero-based coordinates.

The original integer/fractional scaling option and joined terrain texture remain.
Integer mode is initially enabled, so small wheel/pinch changes accumulate until
the next integer pixel scale. Press **I** for continuous fractional zoom; sampling
remains nearest-neighbor in both modes. No new dependency, framework, persistence,
network access, proprietary fixture or original reader change is introduced.

Modern adaptations: drag-to-pan, cursor/pinch-centered bounded zoom, touch-native
gesture recognition and diagnostic selection highlights are implemented for this
viewer. Their behavior is not claimed as a reconstruction of original CyberStorm
controls. No HERC movement/selection rules, tactical HUD, turns, combat, map-format
reconstruction, Android packaging or Milestone 4 work is included.

## Verification

Local environment: Python 3.14.7, pygame-ce 2.5.8, SDL 2.32.10, macOS.
Commands use the existing ignored `local-research/milestone-2-venv` environment;
new contributors can use the README `.venv` instructions.

- `python -m unittest discover -s tests -q`: **65 tests passed**, none skipped.
  The existing 47 Milestone 0–2 checks continue to pass with geometry imports and
  generated Scene constructors updated to the single authoritative model.
- `python -m compileall -q cyberstorm tools tests`: passed.
- `python -m tools.battlefield local-research/gog-1.1 --check`: passed; 77 hexes,
  five objects, 38 frames, 336,908 indexed pixels, unchanged from Milestone 2.
- Generated numeric/gesture tests cover round trips, all cell centers, footprint
  interiors/edges, holes/empty maps, camera corners at zoom limits, focal anchoring,
  repeated limit operations, mouse jitter/drag, touch tap/pan/pinch, coincident and
  extra fingers, cancellation and logical/drawable high-DPI conversion.
- Generated SDL software-render tests exercise mouse and finger event sequences,
  ignore synthesized mouse events, retain correct post-navigation selection,
  cancel interrupted input, and check actual yellow highlight pixels with grid off.
- Automated aspect-ratio cases: 800×600 (4:3), 960×540 (16:9), 960×600 (16:10),
  1260×540 (21:9), 1536×432 (32:9). Uniform scale and selection are checked at each.
- Native macOS window checked with original data: click selection, keyboard zoom,
  drag pan, wheel zoom, subsequent click selection, upper-left camera clamping,
  zoom out to minimum, empty-margin deselection, integer/fractional toggle,
  grid-off highlight and fullscreen/windowed transitions. The settled 3440×1440
  fullscreen view preserves artwork proportions. An initial UI-tool attachment
  timeout and window-coordinate errors were resolved by selecting the exact
  Python application path and testing in fullscreen.

Pending manual checks: real multi-touch hardware, Windows/Linux native window
interaction, true 2× high-DPI hardware and human playtesting at all five ratios.
Touch events and 2× input math are automated evidence, not physical-device proof.
Android Skills are not applicable: this is desktop SDL input, with no Android
implementation, testing, packaging or release work. No linter, type checker or
separate build system exists; compilation and the configured desktop CI suite
are the available code checks. CI results and PR identity belong in the canonical
Drive completion handoff after Uplink. Milestone acceptance remains with Dan.

## Manual navigation checklist

Launch `python -m tools.battlefield /path/to/data --size WIDTH HEIGHT`, substituting
the five dimensions above. Use **I** to compare integer and fractional modes.

1. Click/tap hex centers, shared edges and the outer perimeter. Confirm the yellow
   outline and title coordinates; click empty margins to clear selection. Toggle
   **G** off and verify the selected outline still appears above objects.
2. Zoom in; drag in each direction using left/middle/right mouse buttons. Select
   the same landmark after repeated pans and wheel zooms. Verify small click jitter
   selects, while dragging away and back does not accidentally change selection.
3. Wheel over an off-center landmark; it should stay under the cursor unless map
   bounds clamp. Use **+ / −**, **0** and repeated wheel input at both zoom limits.
   Integer steps are expected; fractional mode should zoom continuously.
4. At minimum and maximum zoom, pan to every edge/corner. The camera must stay on
   the map. An axis smaller than the viewport must remain centered with margins.
5. On hardware delivering SDL finger events: tap; pan one finger; pinch apart and
   together while moving the midpoint; lift either finger then continue panning.
   No pan/pinch release may select a new hex. Try coincident fingers, adding a
   third finger, then a fresh tap. Check both scaling modes.
6. During a drag/pinch, change focus or resize. Return and start a fresh gesture:
   no stuck drag, phantom click or jump. Check **F** transitions and moving between
   normal/high-DPI displays; selection must continue to match the displayed hex.
7. Confirm terrain/sprites keep their aspect ratio at each viewport and animation
   pause/resume still works. Record OS, device, logical/drawable sizes and failures.

## Handoff and rollback

StylePass and contract cleanup keep the new math local and remove the old duplicate
hex helper API and stored outline shape; all in-repo consumers use `Hex`. Review
includes the complete scoped diff and generated tests. Readers/assets and the
manifest format are unchanged. Original data stays ignored and is not uploaded.

The brief authorizes Uplink through PR/CI, not merge or deployment. `main` remains
at the starting commit until Dan accepts the work. Rollback is the unmodified
canonical branch; no data migration, release artifact, tag, stash or backup is
changed or deleted. Next: First Officer review and Captain playtesting, including
the hardware checks above. Do not begin Milestone 4 from this task.

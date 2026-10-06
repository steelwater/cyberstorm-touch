# Milestone 4 — HERCs and movement: reconstruction findings

Date: 2026-10-06 (Asia/Tokyo). Owner: Dan. Investigation: Codex.
Authority: [Crew Brief](https://docs.google.com/document/d/1I3IkjgHkx6Z3HdjReACPWFi4JdWLs_xItkOJUfEz4bE/edit)
and [roadmap](https://docs.google.com/document/d/1MhOmbCskBofRm592bZJAYqpExaWW33bZh1Xu51Up3N8/edit).
Status: static reconstruction advanced; gameplay implementation and original-game
validation remain incomplete. Dan selected “reconstruct first” on 2026-10-06.
No temporary movement rules are approved.

## Preflight and LogicPass

Created `codex/milestone-4-hercs-movement` from fetched `origin/main` at
`c78b79c`, which merges Milestone 3. The initial working tree was clean.
Outcome: data-backed HERC placement, selection and authoritative legal movement,
with mouse/touch presentation preserving camera navigation. Expected change surface:
data readers, a platform-independent simulation module, scene binding, input intents,
renderer animation/highlights, generated tests and developer documentation.

The smallest faithful implementation needs verified unit/pilot mappings and movement
cost semantics first. A shortest-path algorithm alone cannot establish original
movement legality. Risks include invented costs, treating sprite variations as
terrain rules, guessed facing order, and silently introducing turn accounting.
Proof must combine generated rule/reader tests with original-data validation and
controlled original-game comparisons, then desktop/touch playtesting.

## Evidence checked

- Milestone 0 identifies HERCTXT.BIN, PARASH.BIN, MINISH.BIN and executable tables
  as candidates, not decoded authoritative unit/pilot definitions. Milestones 1–3
  establish graphics and navigation; they do not resolve those tables.
- The supplied `DOC/CHASSIS.TXT` documents chassis properties and categorical
  jump costs. `DOC/DRIVE.TXT` documents drive energy factors and chassis compatibility.
  Neither inspected table defines the complete per-hex movement equation.
- The current representative scene has visual terrain frames and objects, without
  gameplay terrain classifications, costs, unit definitions or pilot assignments.
  Its rock artwork is not evidence of original blocking semantics.
- Preserved original [movement help](https://github.com/TeamCorgo/CS-Help/blob/latest/webpage/control_movement.html)
  describes destination preview followed by confirmation, reactor-energy use,
  and partial progress for a destination beyond current range. Continuing on a
  subsequent turn is also described. File blob: `1d3c080d02fd2eaa1e159b2b3147a84d65c5f71b`.
- Preserved [drive help](https://github.com/TeamCorgo/CS-Help/blob/latest/webpage/device_drive.html)
  says drive technology affects movement energy requirements. This corroborates
  the need for an energy formula, but supplies no exact equation.
- Preserved [Bioderm help](https://github.com/TeamCorgo/CS-Help/blob/latest/webpage/info_bioderm.html)
  identifies pilots and piloting skill. It does not establish a decoded runtime
  assignment format or the movement effect of that skill.
- The supplied eight-page `Manual.pdf` yielded no matching movement/terrain/facing
  text through pypdf extraction. It was not visually reviewed or OCRed; this is
  an extraction limit, not proof that relevant information is absent.

Public help was read through the GitHub connector after web/raw/API retrieval
failures. No preservation assets or third-party implementation code were adopted.
The subsequent approved reconstruction pass used bounded static disassembly of the
locally supplied executable. No controlled original-game execution or save comparison
has yet been performed.

## Reconstruction decision

Context: the brief requires faithful movement, and earlier milestones only establish
visual assets and camera navigation. On 2026-10-06 Dan selected reconstruction before
implementation. The alternative was a separately approved provisional prototype;
it was not selected. Consequence: derive rules from original data and call paths,
then compare player-visible edge cases in the original before claiming fidelity.
Owner: Dan. No architecture, dependency, release or deployment change was approved.

## Method and provenance

Supported local executable: `CSTORM.EXE`, 736,256 bytes, SHA-256
`b9d950fe3682885943ae1e7fe1b68a1b1e7b9b0c6d44fa426459eb879965b181`.
The original still matches the Milestone 0 manifest.

The public [preservation function index](https://github.com/TeamCorgo/The-CyberStorm-Museum/blob/523406bc5530cbb46631a109fa2d4a7afe3e1b81/modern/cstorm%20tracker.xlsx)
was read with the existing bundled openpyxl runtime. Its labels are investigation
leads, not authoritative semantics: several movement routines have unrelated names.
Addresses below were checked against local call paths. No third-party implementation
was incorporated. Preserved movement, drive, Bioderm, leg and anti-gravity help supplied
context, not the integer equations.

Apple LLVM 17 objdump rejected the original PE's zero section virtual sizes. An
ignored analysis-only copy fills those zero fields with each section's raw size.
Exactly nine bytes differ, all within section VirtualSize fields; file length and
all code/data bytes are unchanged. The copy was never executed. Original binaries,
function-index extraction and disassembly remain under ignored `local-research/`.
No original binary, disassembly listing or game table is included in this note.

All addresses are virtual addresses for this exact executable, image base `0x400000`.
Findings below establish static behavior; they are not live game measurements.

## Recovered data contracts

### Equipment and pilots

The definition registry at `0x493d90` has 23 entries of 20 bytes. Each entry includes
a definition pointer, record stride, text-label base and count. Lookup `0x438374`
uses the selected loadout index at HERC offset `0x12 + 8 * slot`.

| Slot | Definition | Table address | Stride | Count, including stub |
| --- | --- | --- | --- | --- |
| 0 | Chassis | `0x494a98` | 725 | 34 |
| 2 | Drive | `0x49b5c4` | 31 | 25 |
| 5 | Reactor | `0x49ba2c` | 31 | 19 |
| 6 | Battery | `0x49bc7c` | 35 | 33 |

Definition weight is a signed integer at `+0x17`; drive energy factor is at `+0x1b`.
All eight human chassis weights match `DOC/CHASSIS.TXT`, and all 24 non-stub drive
factors match `DOC/DRIVE.TXT`. Counts and comparisons were read from the supplied
files, rather than copied into application constants. `TECHTXT.BIN` label IDs
corroborate the categories.

Pilot templates use a 30-pointer array at `0x493cd8`, not a fixed record stride.
Initialization `0x435e43` / `0x435e9c` connects type and template to a runtime pilot.
Seven skill entries start at template `+0x17`, four bytes per entry. Piloting is
index 6: initial value at template `+0x2f`, cap at `+0x30`; runtime initialization
stores them shifted left 12 bits at `+0x66` / `+0x6a`.
Effective skill accessor `0x43718a` applies condition penalties and clamps to 0–99.
Using the template's initial piloting number directly would bypass those penalties.
The selected battlefield unit carries HERC and pilot pointers at `+0x18` / `+0x1c`.

BIN readers must account for a terminal offset entry. In the inspected TECHTXT and
HERCTXT headers, the declared entry count includes that sentinel, which points to
EOF; it is not another string. This differs from the preservation format note.

### Terrain resources

`0x4336d0` clears a 1,221-byte scenario resource structure and loads `s%dp%d.dat`
through `0x47c920`, which supports raw and PKX-compressed payloads. Short files leave
a zero-filled tail. All 23 inspected S1/S2/S3 P-number DAT resources have signature
`0xabbaabba`; unwrapped lengths range from 789 to 1,141 bytes.

The movement builder reads terrain bytes at DAT `0x6f + 39 * terrain`, terrain
indices 0–14. Overlay index 0 has zero base cost; indices 1–64 use DAT
`0x2b7 + 8 * index`. The scenario byte at `+0x12` supplies height scaling through
loader `0x4337e1`. Do not reject valid short resources for lacking the zero-padded tail.
Full terrain-record semantics and the representative scene's gameplay cell mapping
are still unfinished; visual frame IDs alone do not establish terrain class.

## Recovered movement calculation

### Cost table construction

`0x432930` takes map, HERC and pilot. It builds 82 scaled entries, plus ascent and
descent arrays. For the positive, supported values observed in these call paths,
let `trunc` mean integer division toward zero:

- `P`: effective piloting skill from `0x43718a(pilot, 6)`.
- `M`: effective HERC mass at runtime `+0xe7`.
- `W = trunc(100 * M / (50 + P))`.
- `D = max(10, effective_drive_energy_factor)` from `0x43b044(HERC, 2, scratch)`.
- `scale(B) = trunc((B * W + D - 1) / D)`.
- Terrain base: `B = raw + max(3 * (raw - 16), 0)`.
- Overlay base: zero for index 0; otherwise `B = 4 * raw + 16`.
- A separate map value at `+0x4c` receives `scale(16)`.

The builder also initializes two special entries. Their byte source and zero value
are identified, but their gameplay meaning is not yet established.

For height differences 1–7, chassis fields at `+0x28d + 4 * (difference - 1)`
and `+0x2ad + 4 * (difference - 1)` supply ascent/descent bases. Each is first
scaled with the equation above, then multiplied by scenario scaling and divided
by 500, truncating again. The loader computes that scaling as
`trunc(scenario_byte_at_0x12 * 500 / 100)`. Preserve this two-stage rounding.

Mass builder `0x438505` sums the weights of the 23 selected definitions. A global
factor, modified by equipment found through `0x43ac9c`, adjusts the sum. Below 100
the factor becomes `trunc((factor + 100) / 2)`; it is clamped to 20–500. The final
mass is `max(100, trunc(weight_sum * factor / 100))`. Gravity/anti-gravity is the
likely interpretation, consistent with help, but the global's full source and
all equipment/damage effects still need tracing before naming a public API.

### Effective drive refinement

The slot-2 branch of `0x43b044` takes the minimum effectiveness of drive and both
legs (slots 2, 3 and 4), applies device modifiers through `0x43ad4f`, then computes
`trunc((modified_factor * minimum_effectiveness + 50) / 100)`. Consequently an
undamaged drive alone does not establish its effective movement factor.
Effectiveness accessor `0x43842f` uses runtime component condition, definition
thresholds and a per-slot global modifier. A special chassis-range condition also
exists. Those global inputs still require provenance before exposing final rules.

Device modifier `0x43ad4f` scans slots 19–22 for matching target/type and active
or permitted state, with nonzero component effectiveness. Each contribution is
calculated against the original input factor, rather than compounding the previous
contribution; its final result is clamped to 0–100,000. This path is now located,
but device activation and environment semantics remain outside the verified API.

### Adjacent step and route search

`0x432b50` accesses 12-byte map cells: byte 0 terrain, byte 1 elevation and byte 3
overlay. The destination terrain and overlay costs are added; with a nonzero
source index, positive elevation difference adds ascent cost and negative difference
adds descent cost. The result is at least 1. Source index zero has special handling;
it must not silently become an ordinary grid coordinate.

`0x432c00` returns 2000 for occupied destinations, otherwise the step cost. That
is a search penalty/sentinel, not proof of a universally impassable cell.
`0x42d080` searches six neighbors and stores minimum accumulated cost and predecessors;
no facing input appears in this cost search. `0x458840` builds the preview path
(maximum 128 nodes in this call), distinguishing within-reactor and beyond-reactor
segments. Visibility and occupancy also influence preview classification.

### Energy and execution: unresolved behavioral boundary

`0x438602` returns HERC `+0x3d`, the reactor amount used by preview. `0x43863d`
returns battery `+0x45`; `0x438678` sums them. Debit routine `0x43a294` spends
reactor first, then battery if sufficient, and returns failure without mutation
if the combined amount cannot cover the debit.

Execution at `0x457b99` onward has an additional gate: when reactor cannot cover
the next step, unit byte `+0x8d` determines whether execution stops. A successful
step sets that byte to 1. Initialization/update at `0x44fb9e`–`0x44fbaf` sets it
according to whether HERC byte `+0x3b` equals 100. Other actions also set it.
The movement caller invokes the debit routine without checking its return in the
inspected path. This is evidence of a state-dependent exception, not sufficient
proof of a general “free first step” or battery-powered movement rule.

There is also an execution occupancy gate, including a special chassis/team branch.
It must be understood before replacing the search penalty with a hard occupancy rule.

### Facing

The function index's “rotate HERC” label at `0x44da10` appears to describe camera
rotation. It is not evidence that unit turning is free. The actual selected-unit
facing path `0x44e420` calls `0x455f70`, sets an angle at unit `+0x46`, and schedules
animation through `0x458d30`. No direct energy debit appears there, but the animation
and movement tick path has not been fully reconstructed. Facing-to-frame mapping
and turning energy remain unverified.

## Remaining proof and next action

Continue reconstruction on this branch. Do not implement temporary movement rules.
Remaining static work: terrain/cell binding, full effective-drive and mass inputs,
turning tick/frame mapping, the energy exception's complete state lifecycle, and
occupancy exceptions. Derive minimal data readers and generated fixtures only from
verified contracts; do not copy original tables into tests.

A controlled GOG 1.1 comparison is still required. Record one HERC's exact chassis,
loadout, pilot/condition, scenario/gravity, initial reactor/battery and starting cell.
Vary one input per observation:

1. Adjacent level moves across terrain and overlays; record preview and actual debit.
2. Height differences in both directions; check the two rounding stages.
3. Same route with a different drive or piloting value.
4. Turning in place and turning before a step; record energy and displayed facing.
5. First versus subsequent steps when reactor is below cost, with sufficient and
   insufficient battery, plus the relevant HERC status associated with `+0x3b`.
6. Occupied destinations and a route beyond the available reactor amount.

No runnable original-game environment was found in this local inspection. No Wine,
VM or durable analysis dependency was installed. Dan has been asked whether an
existing Windows/compatibility setup or manual capture route is available. That
question is about access to evidence, not reopening the approved reconstruction
choice. Keep proprietary captures local and report factual comparisons only.

## Verification and handoff

Local checks on the research branch (repeated for Uplink):

- `local-research/milestone-2-venv/bin/python -m unittest discover -s tests -q`:
  65 tests passed, none skipped.
- Same Python, `-m compileall -q cyberstorm tools tests`: passed.
- Same Python, `-m tools.battlefield local-research/gog-1.1 --check`: passed;
  77 hexes, five objects, 38 frames and 336,908 indexed pixels.

Reconstruction verification: all 24 drive factors and eight human chassis weights
match their supplied reference tables; the original executable hash is unchanged;
analysis-copy differences are confined to PE section-size metadata.

Dan playtested the launched existing renderer on 2026-10-06 and confirmed that
the Milestone 3 commands still work. This is regression evidence for the existing
controls, not verification of Milestone 4 movement. Dan then authorized Uplink of
this research checkpoint.

No new movement tests or manual movement/touch checks have run because movement
is not implemented. No separate lint/typecheck/build tooling is configured. No
Android work was performed. This research note is the only repository file change;
it contains no original asset payloads or copied game tables. Uplink scope is this
research note only, targeting `main`; gameplay remains incomplete. No merge, release,
dependency installation or deployment is included. Remote commit, PR and CI evidence
belong to the Uplink report.

Rollback: source behavior and original data remain unchanged at `c78b79c`; the
existing Milestone 3 branch is retained. The reconstruction choice is resolved.
Next work is the remaining static trace and
controlled original-game comparisons; Milestone 4 must not be reported complete.
An original-game access answer is pending.

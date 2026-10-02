# Cyber Storm Touch — Milestone 0 findings

Date: 2026-10-02 (Asia/Tokyo). Owner: Dan. Research/tooling: Codex.

Authority: [Milestone 0 Crew Brief](https://docs.google.com/document/d/1eklZ5boo0c62CI6iYEgMm5vwIYg6PMgBoX0-1d4rV8Y/edit)
and [roadmap](https://docs.google.com/document/d/1MhOmbCskBofRm592bZJAYqpExaWW33bZh1Xu51Up3N8/edit).

## Outcome and limits

The milestone's independent resource-read proof is achieved. Our standalone Python
probe reads all four original RBX archives, validates all 1,787 indexed payloads,
and identifies the structure of a regular PLX palette without executing the game.
The complete extracted installer payload is inventoried: **296 files, 11 directories,
306,433,900 file bytes**. This is a complete extraction inventory, not a claim that
Windows installer actions, registry changes, shortcuts, or first-run generated files
have been reproduced. Original save round-trips and gameplay definitions remain
unverified. No engine or production stack has been selected.

The workspace was not a Git repository at preflight. Branch, commit, remote, CI,
and PR are therefore not applicable; no Git repository was initialized or files
committed. All deliverables are local source/metadata files pending Dan's review.

## Input provenance and extraction

- Supplied file: `installer/setup_missionforce_cyberstorm_1.1_(31064).exe`.
- Size: 248,538,712 bytes.
- SHA-256: `bac121d00b238bbf4b8dde60fecd632848e20b36cace140a8d0ebf12bcc2717a`.
- `file` identifies a Windows PE32 GUI executable for Intel 80386.
- Embedded setup signature and innoextract identify Inno Setup 5.6.2 (Unicode).
- macOS `bsdtar` cannot open this package. Dan approved installing innoextract.
- Homebrew installed innoextract formula 1.9_14 (tool reports 1.9) and Boost 1.92.0.
  Homebrew also performed its normal metadata/portable-Ruby update. This approval
  does not select a dependency for the future engine.
- Extraction completed with exit code 0 and `Done.`; no installer/game executable
  was run. No input was moved or deleted.
- All 296 quoted paths in `innoextract --list --list-sizes` match the extracted file
  set exactly. There are 292 listing lines because four lines contain two destination
  names for shared data; these are not missing or extra files.

Run from the project root, using an empty output directory on a fresh reproduction:

```sh
innoextract --version
shasum -a 256 'installer/setup_missionforce_cyberstorm_1.1_(31064).exe'
innoextract --extract --output-dir local-research/gog-1.1 \
  'installer/setup_missionforce_cyberstorm_1.1_(31064).exe'
innoextract --list --list-sizes \
  'installer/setup_missionforce_cyberstorm_1.1_(31064).exe'
python3 tools/inventory.py local-research/gog-1.1 > docs/research/gog-1.1/file-manifest.csv
for n in 1 2 3 4; do
  python3 tools/rbx_probe.py "local-research/gog-1.1/CYBDATA$n.RBX" > "docs/research/gog-1.1/CYBDATA$n.metadata.json" || exit
done
python3 -m unittest discover -s tests -v
```

`file-manifest.csv` records every relative file/directory path, size, SHA-256,
extension, type hint, and classification. The four `CYBDATA*.metadata.json` files
record archive indexes, stored payload sizes/hashes, extension totals, and bounded
structural observations. They contain no resource payloads, palette values, decoded
images, audio, or game text. Extraction/listing logs remain under ignored
`local-research/`.

## Layout and classification

| Location | Files | Purpose/evidence |
| --- | ---: | --- |
| Root | 22 | Four RBX files; CSTORM.EXE, CWARSDLL.DLL; _inmm/libogg/libvorbis/libvorbisfile DLLs; config, GOG metadata, SEQUEL.ART, SAMPLE.CBM, manual/patch/readme |
| QSTART | 144 | 130 MP*.CBM and 14 QS*.CBS, all 30,003 bytes |
| DOC | 18 | 17 text references and WEAPONS.XLS; names include chassis, weapons, armor, life support, and Cybrid references |
| AVI | 3 | RIFF AVI containers |
| MUSIC | 3 | Ogg containers with Vorbis identification packets |
| app | 2 | GOG icon and webcache.zip |
| tmp | 102 | Installer UI images, text, font, configuration, helper DLLs and an unclassified empty placeholder |
| __redist/ISI | 1 | scriptinterpreter.exe installer helper |
| commonappdata/GOG.com/supportInstaller | 1 | uninstall.dll installer support |

Directory rows in the manifest preserve the full recursive tree, including parent
folders. Extension classifications are hints unless a signature is cited. Installer
artwork must not be mistaken for original game artwork.

## Confirmed RBX layout

All integer fields below are little-endian. This description was inferred locally
from the supplied package and validated across all four archives before consulting
any third-party parser code (none was copied).

| Offset | Structure |
| --- | --- |
| 0 | Four signature bytes `9e 9a a9 0b` |
| 4 | u32 index-entry count |
| 8 | Count × 16-byte entries: 12-byte ASCII filename, padded with zero bytes when shorter, followed by u32 absolute file offset |
| Each indexed offset | u32 stored payload byte length, followed by exactly that many bytes |

Physical payload order differs from index order. Sorting offsets gives contiguous
records from the end of the index to EOF, with no gaps/overlaps in any archive.
The length prefix is an RBX record envelope, not part of the embedded resource.
Names are DOS-style 8.3. The strict probe rejects unsupported names, duplicate names,
invalid counts/offsets/lengths, gaps, overlaps, truncated input, and trailing bytes.
It deliberately does not promise support for other releases or archive variants.

| Archive | Bytes | Entries | Index end | PKX-wrapped entries |
| --- | ---: | ---: | ---: | ---: |
| CYBDATA1.RBX | 4,764,886 | 427 | 6,840 | 219 |
| CYBDATA2.RBX | 15,306,390 | 821 | 13,144 | 644 |
| CYBDATA3.RBX | 16,805,969 | 291 | 4,664 | 0 |
| CYBDATA4.RBX | 165,223,668 | 248 | 3,976 | 23 |

## First original resource read

Run `python3 tools/rbx_probe.py local-research/gog-1.1/CYBDATA1.RBX`.
The saved metadata contains this observation:

```json
{
  "name": "MAINMENU.PLX",
  "offset": 791125,
  "stored_size": 1024,
  "sha256": "254b6825b69dd8ef721452c8167c8e4e1f8406671521f1647b0b327e12067519",
  "pkx_wrapper": false,
  "palette_records": 256,
  "palette_record_bytes": 4,
  "palette_fourth_byte_zero": true
}
```

The payload begins at 791129, immediately after its RBX length field. Our code reads
and hashes the actual resource bytes. Thirty PLX entries share this 1,024-byte shape
and have zero in every fourth byte. The remaining BGMPALS.PLX is 13,320 bytes and
must not be forced into the single-palette contract. RGB versus BGR order, reserved
indexes, dynamic lighting, and transparency semantics are not established by this
structural proof. No palette/image content was exported.

## Format and unknowns matrix

| Domain | Locally observed candidates | Confirmed vs unresolved |
| --- | --- | --- |
| Graphics/palette | 152 BMX; 31 PLX; loose SEQUEL.ART | PLX regular shape verified; 133 BMX and ART start with PKX:. Pixel decoding/channel order unresolved |
| Animation | 746 ANX; 256 FLX | All ANX start PKX:. 255 FLX are unwrapped; BABY.FLX header candidates include magic 0xaf20, 90 frames, 640×480, depth 8. Frame/chunk decoding unverified |
| Fonts | 6 FNX | All PKX-wrapped. Glyph map/metrics and shading unresolved |
| Audio/music | 439 WAX; 3 Ogg; 3 AVI | Sampled WAX begins WAX:. All three Ogg Vorbis identification headers report stereo 44,100 Hz. WAX decoding and AVI codecs/playback not tested |
| Video | CSINTRO.AVI, CST001.AVI, CST002.AVI | RIFF/AVI confirmed; sampled avih dimensions 320×240, 640×480, 640×480 respectively |
| Map/mission | 20 SIT*.CS; 55 DAT; QSTART CBM/CBS | SIT payloads sampled with 0xabcdabcd; SCAPE*.DAT with 0x88888888; planet DAT with 0xabbaabba. Schema/field meanings unresolved |
| Campaign/economy | WORLDS.DAT, SITTAB.DAT, planet DAT/BIN; CSTORM.EXE | WORLDS begins 0xdeadbeef; matching planet basename references and executable filename strings observed. Economy/progression rules not located conclusively |
| HERC/Bioderm | HERCTXT.BIN, PARASH.BIN, MINISH.BIN, DOC/CHASSIS.TXT, DOC/LIFE.TXT; CSTORM.EXE candidate | Reference/text locations identified, not authoritative gameplay tables. Executable-embedded definitions remain a research lead |
| Weapons/equipment | TECHTXT.BIN, PARATECH.BIN, DOC/WEAPONS.TXT, DOC/WEAPONS.XLS and equipment TXT references | Text/reference candidates located; exact runtime numeric table offsets unconfirmed |
| UI/localization | 41 BIN, 35 BOX, 5 PLY | Executable filename references confirm use of several BINs. Structure semantics mostly external claims, not decoded locally |
| Save/state | 131 CBM including SAMPLE; 14 CBS | All 30,003 bytes and CYB: signature. Distinct observed field at offset 12: CBM=3, CBS=2. No fresh player save or round-trip available |
| Unknown | DIGIPRI.XXX, installer tmp/empty | XXX role not independently decoded; empty installer file retained in manifest |

### Packing and compression

RBX is an indexed envelope; the entire archive need not be decompressed to address
a resource. Of 1,787 entries, 886 start `PKX:`. The next u32 values are consistently
`0x10011966`, `0x9baebacf`; the following u32 is 14 in 885 cases and 1 in one case.
These are observed header values, not proven codec IDs. The probe reports five
header words without assigning unverified meanings. Compression algorithm,
dictionary/window, and decompressed-size interpretation remain unknown. No PKX
implementation or third-party decompressor was added. Never infer that every ANX,
BMX, FLX, or FNX in every release uses the same wrapper.

### Save investigation

All supplied CBM/CBS files share `CYB:` followed by u32 `0x0000ca54` at offset 4,
zero at offset 8, and the values above at offset 12. Offset 16 varies, including
0 and 30202–30205, and is not treated as a file length. Identical physical sizes
suggest a fixed-size representation or reserved capacity, but this is a hypothesis.
These are distributed quick-start/map inputs, not evidence of complete player-save
compatibility. No `.hrc` or separately generated player saves are present. Next
save work requires controlled original-game saves with one known state change per
sample, format/version checks, and explicit round-trip comparisons. Neither native
save serialization nor original import/export compatibility is chosen here.

## Preservation references and license boundary

Consulted 2026-10-02:

- [CyberStorm Museum](https://github.com/TeamCorgo/The-CyberStorm-Museum): locally
  matches its counts of ANX/BMX/FLX/WAX/BIN/DAT/FNX and four archives. Its palette
  total includes a broader preservation set than our 31 indexed PLX files; counts
  must not be equated blindly. Its explanations of DAT relationships, executable
  unit/weapon definitions, embedded palettes, and audio timing are external leads,
  not locally verified behavior. Its HRC specification link is a future save lead.
- [CS-Graphics](https://github.com/TeamCorgo/CS-Graphics): reports PLX palettes,
  FNX fonts, ANX/BMX imagery, FLX animation and BOX/PLY UI geometry. Local names and
  counts support those candidates; decoding and rendering semantics were not
  reproduced. This older archived subproject lists three fonts while the current
  Museum and our local index have six, so use release-specific evidence.
- [RBXIT CyberStorm 1](https://github.com/juanitogan/rbxit/wiki/CyberStorm-1):
  installation filenames are locally confirmed. Its compatibility patches and
  save-dialog fixes concern the original Windows runtime; they are not a substitute
  for file-format parsing. They were not installed or behaviorally verified.
- [innoextract](https://constexpr.org/innoextract/): extraction utility used locally;
  its sources were not incorporated into Cyber Storm Touch.

Only reference descriptions were consulted. No third-party code was copied or
adopted; compatibility/license review is still required before any future reuse.
The extracted GOG game is the primary evidence, not preservation asset downloads.

## Technical gate and Milestone 1 recommendation

Context: The archive proof removes the need to execute Windows code to locate and
read stored resources. It does not yet prove image/audio decoding or game behavior.
Date/owner: 2026-10-02, Dan. Status: recommendations for approval, not stack decisions.

1. Start Milestone 1 with this strict RBX reader contract and a bounded PKX
   investigation using multiple original samples plus generated malformed fixtures.
2. Establish regular PLX channel order using independently checked rendering;
   handle BGMPALS separately only after its structure is confirmed.
3. Decode one BMX, then one ANX sequence, then a small FLX and FNX sample.
   Build only the smallest local inspector needed to compare those results.
4. Keep lookup/decompression/palette/glyph logic separate from simulation.

Recommended technical direction: continue disposable standard-library Python probes
for archaeology; defer the production language selection until the first visual
reader can be assessed. For a later language decision, compare a native library-based
approach (C++ or Rust with a portable window/input layer) with Dan's familiar web
stack, using measured decode/render performance and Android data-import constraints.
No package/framework is adopted by this comparison.

| Area | Evidence-based implication and remaining gate |
| --- | --- |
| Portability | Explicit little-endian parsing and seekable files suffice for RBX. Avoid native struct alignment and Windows API dependence |
| Rendering | Indexed palette resources and multi-frame candidates justify an indexed-color decode path. Palette effects, scaling, and decoded frames must precede renderer selection |
| Input | BOX/PLY are useful UI-layout research leads; no touch interaction design follows from archive metadata |
| Audio | Ogg music is confirmed; WAX codec and AVI needs remain gates for choosing a playback library |
| Android import | Four archives total 202,100,913 bytes. Plan bounded reads and user-supplied data; document-provider seeking/copy policy needs later device testing and approval |
| Packaging/build | Keep proprietary inputs outside distributable source/artifacts. No engine build system is justified yet |
| Serialization | CYB samples are insufficient to choose native saves or promise legacy compatibility |
| Testing | Promote generated corruption fixtures and reproducible metadata checks; keep original-data integration checks local |

Alternatives considered: choose an engine immediately, wrap the original executable,
or complete a reusable asset framework now. None is justified by the current scope;
executable wrapping also conflicts with the brief. Consequence: the next milestone
is a narrow reader/inspector, while runtime architecture remains reversible.

## Verification and safeguards

- Nine automated tests pass with generated fixtures only: directory/hash inventory,
  missing directory and symlink rejection; independent RBX payload/hash reads,
  out-of-order indexes, palette shape, PKX observation, every truncation of a small
  valid fixture, invalid signature/count/name/offset/size, duplicates/overlaps,
  trailing bytes, and truncated PKX header.
- Probe succeeds on all four real archives and validates exact contiguous coverage.
- CLI manually rejects the installer as a non-RBX input and reports a missing file
  clearly; neither produces a success JSON document.
  Both tools were also checked for missing input and inappropriate installer input:
  all four failure cases returned nonzero, with stderr and no stdout.
- Installer listing and extracted file set reconcile exactly. Hash manifest includes
  every file, including installer support/temp files. Original installer hash is
  unchanged from preflight.
- `.gitignore` excludes installer, local-research, extracted, game-data, dumps,
  exports, scratch, Python caches, and .DS_Store. Payloads remain only in these
  local research locations. No proprietary assets were committed/uploaded.
  Actual Git ignore matching passed for eight representative data/cache paths in
  a disposable isolated test repository; the project itself was not initialized.
- No existing project test/build/lint/typecheck configuration exists. Python syntax
  compilation and the focused tests are the applicable checks. No UI, responsive
  flow, audio playback, original-game saves, or Android implementation was created;
  those manual/device checks remain unrun and are not claimed.
- Source and metadata were reviewed against the brief. A Git diff is unavailable
  because this folder has no repository. No push, PR, deployment, or release occurred.
- Rollback: the original installer remains intact. Research is additive; no existing
  project files were overwritten except this task's preliminary notes/tool updates.
  Keep the ignored extraction for reproducibility; no cleanup is authorized here.

The exit proof and complete extracted-payload inventory are delivered. Open
acceptance limits are a true installed/first-run Windows state inventory, definitive
runtime unit/equipment/economy table locations, and behavioral save verification.
Those limits are explicit rather than being counted as decoded or compatible.

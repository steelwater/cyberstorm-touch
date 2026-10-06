# Cyber Storm Touch

Open-source research toward a platform-independent reimplementation of
MissionForce: CyberStorm. Users must supply their own legally obtained **GOG 1.1**
data. Milestone 3 adds hex selection and mouse/touch navigation to the diagnostic
battlefield renderer; this is not a playable game.

Original project code is **GPL-3.0-only**; see [LICENSE](LICENSE). That license grants
no rights to CyberStorm, its assets, or its trademarks. No original game executable
is run, and no original assets are included. The approved desktop rendering path
uses Python + pygame-ce; Android integration remains unproven.

## Run the battlefield renderer

Python **3.11 or later**. From the repository root on macOS/Linux:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-renderer.txt
.venv/bin/python -m tools.battlefield /path/to/data
```

Windows PowerShell (activation is not required):

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-renderer.txt
.\.venv\Scripts\python.exe -m tools.battlefield C:\path\to\data
```

Supply the directory containing the four original `CYBDATA*.RBX` archives. The
scene is assembled in memory using the exact validated GOG 1.1 data. It does not
run the original executable, start a server, or export assets. Use `--check` to
decode/validate without opening a window, `--size 1280 720` for an initial window
size, or `--scene path/to/scene.json` for another bounded metadata manifest.

Controls: **left click / tap** select a hex; **left, middle, or right drag / one-finger
pan** move the map; **mouse wheel / two-finger pinch** zoom around the pointer or
pinch midpoint. An 8-window-point movement threshold separates a tap from a drag.
Dragging and pinching preserve the existing selection; clicking empty space clears
it. Yellow marks selection, blue marks mouse hover, and the window title reports
zero-based `column,row`. These are location diagnostics, not HERC commands.

**+ / −** zoom around the view center; **0** reset zoom; **I** switch integer/fractional
scaling; **G** toggle grid; **Space** pause playback; **F** desktop fullscreen/windowed;
**Esc** quit. Resize the window normally. Zoom is bounded to 0.25–4 times the
reference fit. Integer mode retains stepped pixel scaling; press **I** for smooth
wheel/pinch scaling. Both modes use nearest-neighbor sampling and equal axis scale.
Camera bounds follow terrain: axes smaller than the viewport stay centered, while
larger axes pan to their edges. Some margin is unavoidable on small maps and around
the scalloped hex perimeter. Focal points are preserved unless bounds require clamping.

The representative manifest lays out 77 terrain hexes, three rock groups, one
HERC, and a repeating effect. Positions and the **10 fps diagnostic rate** are
authored for visual inspection, not reconstructed mission data or original timing.
There is no HERC movement, combat, or tactical game UI.

See [Milestone 3 navigation and playtest checklist](docs/research/milestone-3.md),
[Milestone 2 findings and verification](docs/research/milestone-2.md) and the
[approved stack decision](docs/research/milestone-2-stack.md). macOS native rendering
was checked locally; Windows/Linux native visual checks and true 2× high-DPI
hardware verification remain pending.

## Run the local inspector

Python **3.11 or later**, standard library only; no package installation required.
Run these commands from the repository root. Pass the directory containing the four
`CYBDATA1.RBX` through `CYBDATA4.RBX` files, not the installer executable.

```sh
python3 -m tools.asset_inspector /path/to/data verify
python3 -m tools.asset_inspector /path/to/data list
python3 -m tools.asset_inspector /path/to/data info CYBDATA1.RBX HRC001B0.ANX
python3 -m tools.asset_inspector /path/to/data render CYBDATA1.RBX HRC001B0.ANX \
  --palette CYBDATA1.RBX:S1P1.PLX --count 6
python3 -m tools.asset_inspector /path/to/data render CYBDATA1.RBX DMGMIN16.BMX \
  --palette CYBDATA1.RBX:S1P1.PLX --count 6
python3 -m tools.asset_inspector /path/to/data render CYBDATA4.RBX BGMSH25A.FLX \
  --palette CYBDATA1.RBX:S1P1.PLX --first 25 --count 6
python3 -m tools.asset_inspector /path/to/data render CYBDATA1.RBX FONT10.FNX --count 10
```

`render` prints the path to a local HTML viewer. Open that file in your browser.
Use its slider or Previous/Next buttons to inspect stored frame order. The CLI is
the resource browser; the HTML page displays the selected frames. No server,
telemetry, account, automatic playback, or network request is needed.

PNG and HTML outputs are written only beneath ignored `local-research/inspector/`,
in a new directory per run. **Do not upload or redistribute these outputs.**
Font previews use a diagnostic white/black mapping, not original font colors.
BMX/ANX use an explicitly selected palette; this does not establish which palette
the original game would select in every context. All pixels are displayed opaque.
FLX starts on a zero canvas; original compositing and timing remain unresolved.

Only the exact four researched GOG archive checksums are accepted. Other releases,
modified archives, BGMPALS palettes, and unimplemented codecs fail explicitly.
See [Milestone 1 format notes](docs/research/milestone-1.md) for supported subsets,
verification, and remaining limitations.

## Verification and contribution

```sh
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python -m compileall -q cyberstorm tools tests
# Optional integration against your local original data; never run this in CI:
python3 -m tools.verify_local /path/to/data
```

Tests generate all fixtures in code. CI is configured for Windows, macOS, and Linux
with Python 3.11 and 3.14, installing the pinned renderer dependency. Renderer
tests use SDL's dummy video driver and software renderer to check actual pixels;
this does not replace native window/GPU visual checks. Without pygame-ce, only
the SDL-specific tests skip. Readers and viewport/scene tests remain dependency-free.
On Windows, substitute `.\.venv\Scripts\python.exe` for `.venv/bin/python` above.
No separate linter, type-checker, or build toolchain is configured.

Keep installer files in ignored `installer/`; keep extraction, dumps, and decoded
content in ignored `local-research/`. Never contribute original images, audio,
palettes, game text, or binaries. Contribute generated-fixture tests and factual
format observations with explicit limits. Gameplay, Android implementation, full
touch UX, packaging, and full resource coverage are outside this milestone.

The original probes remain available:

```sh
python3 tools/inventory.py /path/to/data
python3 tools/rbx_probe.py /path/to/data/CYBDATA1.RBX
```

[Milestone 0 findings](docs/research/gog-1.1/inventory.md) preserve the baseline,
extraction instructions, roadmap link, and earlier unknowns as historical evidence.
The canonical [Milestone 3 Crew Brief](https://docs.google.com/document/d/1EZPYpq-W-xdpwKoIuPqLhAigNUQ4RLYBbWeuNFL-s14/edit)
sets the current scope.

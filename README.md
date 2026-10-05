# Cyber Storm Touch

Open-source research toward a platform-independent reimplementation of
MissionForce: CyberStorm. Users must supply their own legally obtained **GOG 1.1**
data. This is a reader/inspector milestone, not a playable game.

Original project code is **GPL-3.0-only**; see [LICENSE](LICENSE). That license grants
no rights to CyberStorm, its assets, or its trademarks. No original game executable
is run, and no original assets are included. Production engine selection is deferred.

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
python3 -m unittest discover -s tests -v
python3 -m compileall -q cyberstorm tools tests
# Optional integration against your local original data; never run this in CI:
python3 -m tools.verify_local /path/to/data
```

Tests generate all fixtures in code. CI runs them on Windows, macOS, and Linux
with Python 3.11 and 3.14. No third-party runtime dependencies, build system,
linter, or type-checker configuration is required by this research tool.

Keep installer files in ignored `installer/`; keep extraction, dumps, and decoded
content in ignored `local-research/`. Never contribute original images, audio,
palettes, game text, or binaries. Contribute generated-fixture tests and factual
format observations with explicit limits. Production stack, gameplay, Android,
touch controls, packaging, and full resource coverage are outside this milestone.

The original probes remain available:

```sh
python3 tools/inventory.py /path/to/data
python3 tools/rbx_probe.py /path/to/data/CYBDATA1.RBX
```

[Milestone 0 findings](docs/research/gog-1.1/inventory.md) preserve the baseline,
extraction instructions, roadmap link, and earlier unknowns as historical evidence.
The canonical [Milestone 1 Crew Brief](https://docs.google.com/document/d/1K1lWGqCYZNJgSGXqXQ5zwlU58M5HzIg_wXg42jb4OhQ/edit)
sets the current scope.

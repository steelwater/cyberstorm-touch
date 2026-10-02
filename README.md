# Cyber Storm Touch

Milestone 0 tooling for inspecting user-supplied MissionForce: CyberStorm 1.1 GOG data.
This is an archaeology workspace, not a playable engine.

See [research findings](docs/research/gog-1.1/inventory.md) for the canonical brief
links, extraction commands, format evidence, limitations, and Milestone 1 handoff.

Python 3 standard library is sufficient for the tools and generated-fixture tests:

```sh
python3 tools/inventory.py /path/to/local/installation
python3 tools/rbx_probe.py /path/to/CYBDATA1.RBX
python3 -m unittest discover -s tests -v
```

Both tools emit metadata to stdout and errors to stderr with a nonzero exit status.
The RBX probe reads and hashes stored resources; it does not decompress or export
assets. Its deliberately strict format contract is limited to the observed GOG 1.1
layout. No original executable is needed to run these probes.

Keep installers, extracted data, dumps and decoded content under the ignored
`installer/` or `local-research/` directories. Never add original game content to
source control. Generated tests contain no game assets. Engine/runtime choices
remain deferred. This workspace currently has no Git repository or remote.

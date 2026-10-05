# Milestone 2 renderer decision

Date: 2026-10-05 (Asia/Tokyo). Owner/approver: Dan.
Status: approved in chat: “Let's use Python + pygame-ce”.

## Context

The [Milestone 2 Crew Brief](https://docs.google.com/document/d/1GXnwIC6cRotZYDzFHh5d4-XAH9mmpuZ1kK2Kl8YYKsc/edit)
requires an interactive desktop battlefield proof consuming the existing Python
readers. Windows, macOS and Linux are the current targets; Android remains a later
milestone. No gameplay, data importer, packaging or engine rewrite is authorized.

## Decision

Use Python 3.11+ and pin pygame-ce 2.5.8, the release installed from PyPI for this
implementation. SDL provides window events and fullscreen. A narrow pygame adapter
converts indexed images plus explicit palette/key metadata to RGBA surfaces and
cached SDL textures, with nearest-neighbor sampling. Window drawable dimensions
drive uniform viewport scaling; resize/input stay outside readers and scene data.
Camera math and diagnostic playback timing use only the standard library.

The [pygame-ce SDL renderer API](https://pyga.me/docs/ref/sdl2_video.html) supports
texture upload, destination rectangles, nearest sampling and renderer output.
It is explicitly experimental. Isolate it in one adapter, pin the dependency,
and cover actual upload/composition with generated-pixel tests. No renderer API
types enter reader interfaces, scene placement or viewport calculations.

## Alternatives considered

* Godot: [documented desktop/mobile and 2D facilities](https://docs.godotengine.org/en/stable/about/list_of_features.html),
  but integrating the existing Python readers adds a language/bridge decision
  and larger implementation surface now. Not chosen for this milestone.
* Standard-library HTML inspector: retained for resource archaeology; it is not
  the interactive desktop rendering/window path required by this brief.

## Consequences and boundaries

One runtime dependency is introduced only for the renderer. Reader tooling remains
dependency-free. SDL texture caching avoids rebuilding static sprites every frame;
palette conversion occurs on load. The small diagnostic scene can preload bounded
animation frames; this is not a streaming strategy for whole-game resources.

Android packaging and Python integration are **unproven**. SDL ancestry does not
establish Android readiness. A later Android decision may replace this adapter;
reader contracts and manifest/placement/math boundaries should remain reusable.
No Android implementation or Android dependency is introduced here.

Next action: implement the selected scene, verify native rendering locally and
generated fixtures in the desktop CI matrix, and record remaining platform checks.

---
name: pixel-kit
description: Make pixel art animations and export them as crisp MP4 video (1080x1350, 1080x1920, 1080x1080) with the local Pixel Kit engine. Use when the user asks for a pixel animation, a pixel video, a pixel art scene, a pixel explainer, or to render, recolor, or edit a scene in their Pixel Kit workspace.
---

# Pixel Kit

You make pixel art animations by writing a small Python scene file and rendering it with the
`pixelkit` engine. Everything is drawn in code on a tiny canvas (for example 180x225) with named
palette colors, then scaled up with nearest-neighbor to a sharp 1080px video. No image models.

## Where things are

The workspace is `~/pixel-kit` (on Windows `%USERPROFILE%\pixel-kit`). If it is not there, find the
folder that contains `pixelkit/__init__.py` before doing anything else.

```
~/pixel-kit/
  pixelkit/        the engine (do not edit unless asked)
  templates/       starting scenes: blank, forest, desk, chart, measure, dominoes
  examples/        finished pieces, e.g. booster_catch.py
  scenes/          the user's scenes go here
  palettes/        night, dusk, ember, harbor, paper (+ any .json the user adds)
  assets/sprites/  text sprites: robot, cat, person, bird, coin, heart
  out/             renders land here
```

Run everything from the workspace with its own Python:

- macOS / Linux: `cd ~/pixel-kit && .venv/bin/python -m pixelkit ...`
- Windows: `cd %USERPROFILE%\pixel-kit && .venv\Scripts\python -m pixelkit ...`

Below, `pk` means that command.

## Workflow

1. **Brief.** Work out what the animation shows. If the request leaves these open, ask once, in a
   single message, and offer a default for each:
   - Subject and what happens (the one change the viewer should watch: it falls, grows, lights up, counts)
   - Format: 4:5 feed post (default), 9:16 full screen, or square
   - Length: 6-10 seconds (default 8)
   - Colors: a preset palette (night, dusk, ember, harbor, paper), one hue (give a hex), black and white, or their own colors
   - Any on-screen number or label (a readout is what turns a pretty loop into an explainer)
   If the user said "just make it" or the request is clear, decide and say what you decided.

2. **Beat sheet.** Before code, write the timeline in a comment at the top of the scene:
   `0.0 subject already on screen | 1.0 the change starts | ... | last 1.5s hold the payoff`.
   The first frame must already show the subject. Something should change at least every second.

3. **Start from the closest template.**
   `pk new <template> scenes/<name>.py` then edit. Templates:
   - `measure` subject draws itself in while a bracket and readout measure it
   - `chart` bars grow, numbers count, peak gets called out, total lands
   - `dominoes` one push sets off a chain, counter tracks it
   - `desk` character at a desk, rain, city window (chunky 120x150 canvas)
   - `forest` parallax scenery loop, fireflies, a creature
   - `blank` empty starter with the four drawing layers
   `examples/booster_catch.py` is the reference for a full showpiece: physics-driven motion,
   lighting, particles, steam, telemetry bar. Read it when the brief is ambitious.

4. **Draw.** Follow `reference/style.md` (the art rules) and `reference/api.md` (every function).
   Short version: light from the upper left, ramps go dark to light, color only through palette
   references like `"main.3"`, flat shapes with dither only at band edges, HUD drawn last.

5. **Look at it before you show it.** Render a contact sheet first, it takes about a second:
   `pk render scenes/<name>.py --sheet --frames 12`
   Open the PNG it writes (out/<name>_sheet.png) with your file reader and check it against the
   review checklist in `reference/style.md`. Fix what fails. For detail, render single frames:
   `pk render scenes/<name>.py --still 3.2`. Repeat until it passes. Do not hand over a video you
   have not looked at.

6. **Render.** `pk render scenes/<name>.py` writes `out/<name>.mp4`.
   Color versions: `--palette ember`, `--hue "#1f3dff"`, `--mono`,
   `--colors "#0b0b0f,#3a3d4a,#f4efe6,#ff5a1f"` (their own colors; 10+ colors works as a full palette),
   or `--all-modes` for the base, one-hue, and black-and-white versions together.
   `--gif` makes a small preview GIF.

7. **Hand over.** Give the file path, length, size, and one line on what to tweak next if they want.

## Editing an existing scene

Read the scene file first. Change the smallest thing that does what was asked (timing lives in the
constants and `Keys(...)` at the top; colors are palette references; text is in `_hud` or `ui.*`
calls). Re-render the sheet and look again before re-rendering the video.

## If something breaks

- `pk doctor` checks Python, numpy, Pillow, and ffmpeg.
- "ffmpeg not found": `.venv/bin/pip install imageio-ffmpeg` (a bundled ffmpeg), or install ffmpeg.
- A color reference error (`KeyError: 'main.9'`): ramps have fixed lengths, see `reference/api.md`.
- Black or empty frames: something drew `"clear"` over everything, or the canvas was never filled
  (start `draw()` with a backdrop).

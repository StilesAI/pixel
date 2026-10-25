# Pixel Kit

Pixel art animation made by Claude Code, rendered to sharp MP4. Every frame is drawn in code on a
small pixel canvas with a real palette, then scaled up 6x or 9x with no smoothing. No image
generators, no blurry upscales, and any scene can be recolored in one command.

Open `START HERE.html` for the setup steps and copy-paste prompts.

## What's inside

| Folder | What it is |
|---|---|
| `pixelkit/` | the render engine (Python) |
| `skill/pixel-kit/` | the Claude skill: workflow, art rules, full API reference |
| `templates/` | six starting scenes: measure, chart, dominoes, desk, forest, blank |
| `examples/` | `booster_catch.py`, a full showpiece to learn from |
| `palettes/` | night, dusk, ember, harbor, paper |
| `assets/sprites/` | robot, cat, person (with walk cycle), bird, coin, heart |
| `PROMPTS.md` | the install prompt and starter prompts |

## Color modes

Every scene renders in any of these without changes:

- a preset palette: `--palette dusk`
- one hue: `--hue "#1f3dff"`
- black and white: `--mono`
- your own colors: `--colors "#0b0b0f,#3a3d4a,#f4efe6,#ff5a1f"` (10+ colors works as a full palette)

## Requirements

- Claude Code
- Python 3.9 or newer (macOS, Windows, or Linux)
- numpy, Pillow, imageio-ffmpeg (installed for you by the install prompt)

## Commands

From the kit folder, with its virtual environment:

```
.venv/bin/python -m pixelkit render examples/booster_catch.py          # video
.venv/bin/python -m pixelkit render examples/booster_catch.py --sheet  # 8-frame preview
.venv/bin/python -m pixelkit new measure scenes/my_scene.py            # start from a template
.venv/bin/python -m pixelkit doctor                                    # check the install
```

On Windows use `.venv\Scripts\python` in place of `.venv/bin/python`.

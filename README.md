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
| `tools/`, `fx/`, `pk` | `pk fx`: pixel effects pinned to your hand in real video |

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

## Hand-tracked effects (pk fx)

Put a pixel effect on a real video, pinned to your hand, in one command:

```
./pk fx aurora-ribbon --take take.mov --joint right_wrist --seconds 5 --debug   # try 5 seconds first
./pk fx aurora-ribbon --take take.mov --joint right_wrist                       # the whole take
./pk fx aurora-ribbon --take take.mov --joint right_wrist --palette blue         # recolor it
./pk fx fire/spirit-flame --take take.mov --joint right_wrist                    # any pixelfx effect
```

1. A free pose model from Google (MediaPipe Pose Landmarker) finds your wrist in every frame, smoothed so it
   doesn't jitter. `--debug` also writes the track as a video with a dot on your wrist.
2. The effect is drawn along your hand's recent path in hard square pixels, so it trails behind your hand,
   and kept off your face.
3. It's composited onto the take with ffmpeg, its glow added on top. Out comes an MP4 with your audio.

Selfie video from the front camera is usually mirrored: if the effect lands on the wrong hand, add `--mirrored`.
Switch colors partway through with `--palette-at "20.1:blue,22.3:aurora"` (seconds into the take). Run
`./pk fx --help` for the rest (trail length, how far down the arm it reaches, glow, pixel size).

**Effects.** `aurora-ribbon` is in this kit (`fx/`). Every other effect id comes from
[pixelfx](https://github.com/patch-gg/pixelfx) by Patch (MIT, method by Hugo Duprez), 244 pixel art effects:
clone it next to this folder, so you have `pixelfx/` and this kit side by side (or pass `--pixelfx PATH`). Nothing
from pixelfx is copied in here, and `aurora-ribbon` draws with pixelfx's core too, so you need the clone either way.
When you post, credit them: "pixelfx by Patch, method by Hugo Duprez".

**Needs**, on top of the kit's requirements: Node.js 18 or newer, ffmpeg on your PATH, and

```
.venv/bin/python -m pip install -r requirements-fx.txt
```

The pose model (about 9 MB) downloads into `models/` on first run. On Windows, run
`.venv\Scripts\python -m pixelkit fx ...` in place of `./pk fx ...`.

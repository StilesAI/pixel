# Pixel Kit prompts

Paste these into Claude Code. Run the first one once.

## 01 Install

```
Set up Pixel Kit on this computer. I downloaded and unzipped it; find the folder named pixel-kit (check Downloads and Desktop first) that contains a pixelkit folder and requirements.txt.

Do these steps in order, and ask me before installing anything outside that folder:
1. Check that Python 3.9 or newer is installed (python3 --version, or py --version on Windows). If it is missing, tell me how to install it and stop.
2. Copy the kit to ~/pixel-kit (on Windows %USERPROFILE%\pixel-kit). If ~/pixel-kit already exists, ask me before replacing anything, and never overwrite its scenes or out folders.
3. Create a virtual environment at ~/pixel-kit/.venv and install requirements.txt into it.
4. Install the skill by copying ~/pixel-kit/skill/pixel-kit to ~/.claude/skills/pixel-kit.
5. Run the install check from ~/pixel-kit: .venv/bin/python -m pixelkit doctor (Windows: .venv\Scripts\python -m pixelkit doctor).
6. Render the example as a test: .venv/bin/python -m pixelkit render examples/booster_catch.py, then open out/booster_catch.mp4 for me.
7. Tell me in a short list what you installed and where.
```

## 02 Make your first one

```
Use the pixel-kit skill to make a pixel animation of [what happens, e.g. "a hot air balloon rising out of a valley at sunrise while an altitude readout counts up"].
Format 4:5, about 8 seconds. Show me the contact sheet before you render the video.
```

More ideas to swap in:

- a lighthouse that builds itself from the ground up while a height readout counts to 48 m
- a robot at a desk at night, rain on the window, typing, the laptop screen lighting its face
- a bar chart of my screen time this week, the biggest day called out, then the total
- a train crossing a bridge over a canyon, a speed readout ticking as it goes
- a seed sprouting into a tree over a year, with a day counter
- one domino tipping a row of twelve, a counter tracking how many have fallen

## 03 Change the colors

```
Render scenes/[name].py in these color versions: the dusk palette, one hue of #1f3dff, and black and white. Put them side by side in a contact sheet so I can compare, then render the one I pick.
```

Use your own colors:

```
Render scenes/[name].py with my colors: #0b0b0f, #3a3d4a, #f4efe6, #ff5a1f.
```

Or paste a full palette (10+ colors, like one from lospec.com) and it maps every color in the scene to the nearest of yours.

## 04 Edit

```
In scenes/[name].py: make the [thing] slower, start the readout at [number], and change the label to [text]. Show me the sheet again.
```

## 05 Make it yours

```
Turn scenes/[name].py into a template I can reuse: pull every value I would change (subject, numbers, labels, timing) into constants at the top with a comment on each, and save it to templates/[name].py.
```

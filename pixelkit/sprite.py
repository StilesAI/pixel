"""Sprites drawn as text, so Claude (or you) can write and edit them by hand.

File format (assets/sprites/<name>.txt):

    # robot, idle
    legend:
      . clear
      o main.0
      m main.3
      h main.5
      e acc.2
    frame:
    ....oooo....
    ...ommmmo...
    frame:
    ...

Multiple `frame:` blocks make an animation (walk cycle, blink, flicker).
"""
from __future__ import annotations

from pathlib import Path

import numpy as np

from .canvas import Canvas
from .palette import TRANSPARENT, Palette, rgb_to_oklab, ref

ASSET_DIR = Path(__file__).resolve().parent.parent / "assets" / "sprites"


def from_text(grid: str | list[str], legend: dict[str, str]) -> Canvas:
    rows = [r for r in (grid.strip("\n").split("\n") if isinstance(grid, str) else grid)]
    rows = [r.rstrip() for r in rows]
    w = max(len(r) for r in rows)
    c = Canvas(w, len(rows))
    lut = {ch: ref(v) for ch, v in legend.items()}
    for y, r in enumerate(rows):
        for x, ch in enumerate(r):
            if ch in (" ", "."):
                if ch in lut:
                    c.buf[y, x] = lut[ch]
                continue
            if ch not in lut:
                raise KeyError(f"sprite char {ch!r} not in legend")
            c.buf[y, x] = lut[ch]
    return c


class SpriteSheet:
    def __init__(self, name: str, frames: list[Canvas], legend: dict[str, str]):
        self.name = name
        self.frames = frames
        self.legend = legend

    def __getitem__(self, i) -> Canvas:
        return self.frames[i % len(self.frames)]

    def __len__(self):
        return len(self.frames)

    def at(self, t: float, fps: float = 8) -> Canvas:
        """Frame for time t when cycling at `fps` frames per second."""
        return self.frames[int(t * fps) % len(self.frames)]


def parse(text: str, name: str = "sprite") -> SpriteSheet:
    legend: dict[str, str] = {}
    frames: list[list[str]] = []
    mode = None
    for raw in text.split("\n"):
        line = raw.rstrip()
        if line.startswith("#"):
            continue
        low = line.strip().lower()
        if low == "legend:":
            mode = "legend"
            continue
        if low == "frame:":
            mode = "frame"
            frames.append([])
            continue
        if mode == "legend" and line.strip():
            parts = line.split()
            legend[parts[0]] = parts[1]
        elif mode == "frame" and line.strip():
            frames[-1].append(line.strip())
    if not frames:
        raise ValueError(f"{name}: no frame: blocks")
    return SpriteSheet(name, [from_text(f, legend) for f in frames], legend)


_cache: dict[str, SpriteSheet] = {}


def load(name: str) -> SpriteSheet:
    """Load assets/sprites/<name>.txt (or a path)."""
    if name in _cache:
        return _cache[name]
    p = Path(name)
    if not p.exists():
        p = ASSET_DIR / f"{name}.txt"
    sheet = parse(p.read_text(), p.stem)
    _cache[name] = sheet
    return sheet


def available() -> list[str]:
    return sorted(p.stem for p in ASSET_DIR.glob("*.txt"))


def from_png(path: str, palette: Palette, alpha_cut: int = 128) -> Canvas:
    """Bring in your own pixel art: each PNG color snaps to the nearest slot
    of the palette (by perceived color), so it recolors like everything else."""
    from PIL import Image
    img = Image.open(path).convert("RGBA")
    a = np.array(img)
    slots = [i for i in range(256) if i != TRANSPARENT and i < 39]
    labs = np.array([rgb_to_oklab(palette.rgb[i]) for i in slots])
    c = Canvas(a.shape[1], a.shape[0])
    cache = {}
    for y in range(a.shape[0]):
        for x in range(a.shape[1]):
            r, g, b, al = a[y, x]
            if al < alpha_cut:
                continue
            key = (r, g, b)
            if key not in cache:
                l = np.array(rgb_to_oklab((r, g, b)))
                cache[key] = slots[int(np.argmin(((labs - l) ** 2).sum(1)))]
            c.buf[y, x] = cache[key]
    return c

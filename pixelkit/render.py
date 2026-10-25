"""Scenes and rendering.

A scene is a class with a size, a length, and a draw(c, t) method:

    class Tower(Scene):
        W, H = 180, 320       # pixel canvas (180x320 -> 1080x1920 at 6x)
        duration = 8          # seconds
        palette = "night"     # preset name, or a .json path
        anim_fps = 12         # motion updates 12x/s for a hand-animated feel

        def draw(self, c, t):
            c.gradient_v(0, 0, c.w, c.h, ["bg.0", "bg.1", "bg.2"])
            ...

Render with:  python -m pixelkit render scenes/tower.py
"""
from __future__ import annotations

import importlib.util
import math
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image

from .canvas import Canvas
from .palette import Palette, resolve_palette


class Scene:
    W = 180
    H = 320
    fps = 30
    anim_fps = 12         # None = update every output frame
    duration = 6.0
    palette = "night"
    background = "bg.0"
    seed = 1

    def __init__(self):
        self.setup()

    def setup(self):
        """Build sprites, emitters, and anything you want precomputed."""

    def draw(self, c: Canvas, t: float):
        raise NotImplementedError

    # helpers
    @property
    def scale(self):
        return max(1, min(1080 // self.W, 1920 // self.H))

    def frame(self, t: float) -> Canvas:
        c = Canvas(self.W, self.H, self.background)
        self.draw(c, t)
        return c


def load_scene(path: str) -> Scene:
    p = Path(path).resolve()
    if not p.exists():
        raise FileNotFoundError(path)
    spec = importlib.util.spec_from_file_location(p.stem, p)
    mod = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(p.parent))
    spec.loader.exec_module(mod)
    found = [v for v in vars(mod).values()
             if isinstance(v, type) and issubclass(v, Scene) and v is not Scene
             and v.__module__ == mod.__name__]
    if not found:
        raise ValueError(f"{path}: no Scene subclass found")
    return found[-1]()


def _ffmpeg():
    exe = shutil.which("ffmpeg")
    if exe:
        return exe
    try:
        import imageio_ffmpeg  # pip install imageio-ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        raise RuntimeError("ffmpeg not found. Install it (brew install ffmpeg) or "
                           "pip install imageio-ffmpeg")


def _times(scene: Scene, t0=0.0, t1=None):
    t1 = scene.duration if t1 is None else t1
    n = int(round((t1 - t0) * scene.fps))
    for i in range(n):
        t = t0 + i / scene.fps
        if scene.anim_fps:
            t = math.floor(t * scene.anim_fps + 1e-9) / scene.anim_fps
        yield i, t


def render_video(scene: Scene, out: str, palette: Palette | None = None, scale: int | None = None,
                 crf: int = 14, best: bool = False, t0=0.0, t1=None, quiet=False) -> str:
    pal = palette or Palette.load(scene.palette)
    s = scale or scene.scale
    out = str(out)
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    W, H = scene.W, scene.H
    cmd = [_ffmpeg(), "-y", "-loglevel", "error",
           "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(scene.fps), "-i", "-",
           "-vf", f"scale={W * s}:{H * s}:flags=neighbor",
           "-c:v", "libx264", "-preset", "slow" if best else "veryfast", "-tune", "animation",
           "-crf", str(crf), "-pix_fmt", "yuv420p", "-movflags", "+faststart", out]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    last_t, last_bytes = None, None
    total = int(round(((scene.duration if t1 is None else t1) - t0) * scene.fps))
    for i, t in _times(scene, t0, t1):
        if t != last_t:
            last_bytes = scene.frame(t).to_rgb(pal).tobytes()
            last_t = t
        proc.stdin.write(last_bytes)
        if not quiet and (i % max(1, total // 10) == 0):
            print(f"  frame {i + 1}/{total}", flush=True)
    proc.stdin.close()
    if proc.wait() != 0:
        raise RuntimeError("ffmpeg failed")
    if not quiet:
        print(f"  wrote {out}  ({W * s}x{H * s}, {scene.duration:g}s, palette {pal.name})")
    return out


def render_still(scene: Scene, t: float, out: str, palette: Palette | None = None, scale=None) -> str:
    pal = palette or Palette.load(scene.palette)
    s = scale or scene.scale
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    scene.frame(t).to_image(pal, s).save(out)
    return out


def contact_sheet(scene: Scene, out: str, n: int = 8, palette: Palette | None = None,
                  scale: int = 2, cols: int = 4, times=None) -> str:
    """Grid of frames across the scene with timestamps, for fast review."""
    pal = palette or Palette.load(scene.palette)
    times = times or [scene.duration * (i + 0.5) / n for i in range(n)]
    imgs = []
    for t in times:
        if scene.anim_fps:
            t = math.floor(t * scene.anim_fps) / scene.anim_fps
        im = scene.frame(t).to_image(pal, scale)
        imgs.append((t, im))
    w, h = imgs[0][1].size
    rows = math.ceil(len(imgs) / cols)
    pad = 14
    sheet = Image.new("RGB", (cols * (w + 6) + 6, rows * (h + pad + 6) + 6), (24, 24, 28))
    from PIL import ImageDraw
    d = ImageDraw.Draw(sheet)
    for k, (t, im) in enumerate(imgs):
        x = 6 + (k % cols) * (w + 6)
        y = 6 + (k // cols) * (h + pad + 6)
        sheet.paste(im, (x, y + pad))
        d.text((x, y), f"{t:.2f}s", fill=(220, 220, 220))
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out)
    return out


def render_gif(scene: Scene, out: str, palette: Palette | None = None, scale: int = 3) -> str:
    pal = palette or Palette.load(scene.palette)
    fps = scene.anim_fps or scene.fps
    frames = []
    n = int(round(scene.duration * fps))
    for i in range(n):
        frames.append(scene.frame(i / fps).to_image(pal, scale))
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    frames[0].save(out, save_all=True, append_images=frames[1:], duration=int(1000 / fps), loop=0,
                   optimize=False, disposal=1)
    return out


def palette_sheet(out: str, base: str = "night", extra_hues=("#1f3dff", "#e0401a", "#2fa59b")) -> str:
    from .palette import presets
    pals = [Palette.load(n) for n in presets()]
    pals += [Palette.load(base).one_hue(h) for h in extra_hues]
    pals.append(Palette.load(base).mono())
    sw = [p.swatch(10) for p in pals]
    w = max(s.size[0] for s in sw)
    h = sw[0].size[1]
    sheet = Image.new("RGB", (len(sw) * (w + 8) + 8, h + 24), (20, 20, 24))
    from PIL import ImageDraw
    d = ImageDraw.Draw(sheet)
    for i, (p, s) in enumerate(zip(pals, sw)):
        sheet.paste(s, (8 + i * (w + 8), 20))
        d.text((8 + i * (w + 8), 4), p.name[:14], fill=(220, 220, 220))
    sheet.save(out)
    return out


__all__ = ["Scene", "load_scene", "render_video", "render_still", "contact_sheet",
           "render_gif", "resolve_palette", "palette_sheet"]

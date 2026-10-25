"""pixelkit: code-drawn pixel art animation, rendered to crisp 1080x1920 video."""
from .canvas import Canvas, Dither
from .palette import Palette, resolve_palette, presets, ref, ramp
from .render import Scene, render_video, render_still, contact_sheet, render_gif, load_scene
from . import anim, fx, ui, shapes, sprite, props
from .anim import ease, tween, prog, Keys, osc, blink, snap, count, typewriter

__version__ = "1.0.0"

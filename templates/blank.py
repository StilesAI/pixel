"""Blank starter. Copy this, rename the class, and draw.

Canvas sizes that export cleanly (scale is picked automatically):
  180 x 225   -> 1080 x 1350  (4:5 feed post, default)
  180 x 320   -> 1080 x 1920  (9:16 reel, full screen)
  120 x 150   -> 1080 x 1350  (4:5, chunkier pixels for character scenes)
  180 x 180   -> 1080 x 1080  (square)
"""
from pixelkit import Scene, fx, props, shapes, ui
from pixelkit.anim import Keys, ease, prog, tween


class Blank(Scene):
    W, H = 180, 225
    duration = 6          # seconds
    palette = "night"     # night, dusk, ember, harbor, paper, or a .json path
    anim_fps = 12         # 12-15 feels hand-animated; None = smooth 30fps

    def setup(self):
        # build anything you only need once (sprites, emitters, layers)
        self.bob = Keys((0, 0), (1, -3, "outQuad"), (2, 0, "inQuad"))

    def draw(self, c, t):
        # 1. backdrop
        c.gradient_v(0, 0, c.w, 170, ["bg.0", "bg.1", "bg.2", "bg.3"])
        fx.stars(c, t, n=40, region=(0, 0, c.w, 100))
        # 2. ground
        shapes.ground(c, 170, ramp=("alt.0", "alt.1", "alt.2"))
        # 3. subject
        y = 150 + self.bob(t % 2)
        shapes.sphere(c, 90, y, 16, ["main.0", "main.1", "main.2", "main.3", "main.4", "main.5"])
        c.shadow(90, 171, 14 - y + 150, 2)
        # 4. overlay text last, so effects never shade it
        ui.readout(c, 8, 8, "LABEL", f"{tween(t, 0, 3, 0, 100):.0f}", "%", show=prog(t, 0, 0.3))

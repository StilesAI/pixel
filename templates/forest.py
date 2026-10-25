"""Forest at dusk: parallax layers drifting sideways, fireflies, a cat on a
rock. Good for calm, cozy, 'warm fantasy' loops.

Change: palette, the creature (any sprite in assets/sprites), the caption.
"""
import math

from pixelkit import Scene, fx, props, shapes, sprite, ui
from pixelkit.anim import prog


class Forest(Scene):
    W, H = 180, 225
    duration = 8
    palette = "dusk"
    anim_fps = 12
    CAPTION = "SOMEWHERE QUIET"

    def setup(self):
        self.cat = sprite.load("cat")

    def layer(self, c, speed, t, draw, period):
        """Draw a repeating layer scrolled by speed px/s."""
        off = (t * speed) % period
        for k in range(-1, int(c.w / period) + 2):
            draw(k * period - off)

    def draw(self, c, t):
        c.gradient_v(0, 0, c.w, 150, ["bg.0", "bg.1", "bg.2", "bg.3", "bg.4"])
        fx.stars(c, t, n=40, region=(0, 0, c.w, 70))
        shapes.sphere(c, 132, 40, 12, ["bg.4", "main.4", "main.5", "ui.3"], light=(-0.6, -0.4))
        c.glow(132, 40, 30, steps=1)

        # far ridge, mid pines, near pines, each slower than the last
        self.layer(c, 2, t, lambda x: props.mountain(c, x + 40, 150, 120, 60, ramp=("bg.1", "bg.2", "bg.3"),
                                                    snow=None), 120)
        self.layer(c, 5, t, lambda x: [props.pine(c, x + dx, 165, h, ramp=("bg.0", "bg.1", "bg.2", "bg.2"),
                                                  trunk="bg.0")
                                       for dx, h in ((0, 44), (14, 56), (26, 40))], 40)
        c.rect(0, 160, c.w, 70, "bg.1")
        self.layer(c, 11, t, lambda x: [props.pine(c, x + dx, 190, h, trunk="alt.0",
                                                   ramp=("leaf.0", "leaf.0", "leaf.1", "leaf.2"),
                                                   sway=math.sin(t * 1.3 + dx) * 0.6)
                                        for dx, h in ((0, 70), (28, 86), (48, 62))], 70)

        # ground
        c.rect(0, 186, c.w, c.h - 186, "leaf.0")
        c.hline(0, c.w - 1, 186, "leaf.1")
        c.gradient_v(0, 187, c.w, c.h - 187, ["leaf.1", "leaf.0", "leaf.0"])
        for gx in range(0, c.w, 3):
            c.pset(gx, 185 - (gx * 7 % 3 == 0), "leaf.1")
        for i in range(40):  # grass tufts that lean with the breeze
            gx = (i * 37) % c.w
            gy = 192 + (i * 53) % 30
            lean = 1 if math.sin(t * 1.5 + gx * 0.1) > 0.3 else 0
            c.pset(gx, gy, "leaf.2")
            c.pset(gx + lean, gy - 1, "leaf.2")
            c.pset(gx + 2, gy, "leaf.1")
        props.rock(c, 66, 192, 34, 14, ramp=("main.0", "main.1", "main.2", "main.3"))
        props.mushroom(c, 110, 194, 1.2)
        props.mushroom(c, 121, 196, 0.8)
        props.mushroom(c, 30, 200, 1.0)
        c.blit(self.cat.at(t, 1.5), 60, 179, anchor="bottom")

        props.fireflies(c, t, n=16, region=(0, 110, c.w, 90))
        fx.vignette(c, 0.8)
        ui.caption(c, self.CAPTION, 207, font="tiny", show=prog(t, 0.5, 0.8))

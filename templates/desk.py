"""Late-night desk: a robot working on a laptop, rain on the window, the city
outside, a lamp, a mug that steams. Good for 'how I work' and AI-tool scenes.

Uses a smaller 120x150 canvas (9x scale) so the character reads big and chunky.
Change: the character sprite, the caption, the palette.
"""
import math

import numpy as np

from pixelkit import Scene, fx, props, sprite, ui, shapes
from pixelkit.anim import prog

DESK = 104


class Desk(Scene):
    W, H = 120, 150
    duration = 8
    palette = "night"
    anim_fps = 12
    CAPTION = "LATE SHIFT"

    def setup(self):
        self.steam = fx.Emitter(seed=3, t0=-3, t1=20, rate=5, origin=(23, DESK - 9), angle=-90, spread=10,
                                speed=(4, 8), life=(1.3, 2.0), colors=["main.4", "main.3", "main.2"], wind=1.2)

    def draw(self, c, t):
        # wall with soft vertical panels
        c.rect(0, 0, c.w, DESK, "bg.1")
        for x in range(4, c.w, 24):
            c.vline(x, 0, DESK - 1, "bg.0")

        # window: city in the rain
        wx, wy, ww, wh = 8, 12, 54, 50
        win = c.m_rect(wx, wy, ww, wh)
        out = c.copy()
        out.gradient_v(wx, wy, ww, wh, ["bg.0", "bg.1", "bg.2"])
        props.skyline(out, wy + wh, t=t, lit=0.45, seed=7, ramp=("bg.0", "bg.1", "bg.2"), hmin=14, hmax=40)
        fx.rain(out, t, n=40, speed=180, slant=0.2, length=3, color="bg.3")
        c.buf[win] = out.buf[win]
        c.frame(wx - 2, wy - 2, ww + 4, wh + 4, "main.2")
        c.frame(wx - 1, wy - 1, ww + 2, wh + 2, "main.0")
        c.vline(wx + ww // 2, wy, wy + wh - 1, "main.2")
        c.hline(wx, wx + ww - 1, wy + wh // 2, "main.2")
        c.rect(wx - 4, wy + wh + 2, ww + 8, 2, "main.3")
        c.hline(wx - 4, wx + ww + 3, wy + wh + 4, "main.0")

        # clock with tick marks
        cx, cy = 92, 30
        c.disc(cx, cy, 8, "main.2")
        c.disc(cx, cy, 7, "ui.3")
        for k in range(12):
            a = k * math.pi / 6
            c.pset(cx + 6 * math.cos(a), cy + 6 * math.sin(a), "main.3")
        m = t * 0.9 - math.pi / 2
        c.line(cx, cy, cx + 5 * math.cos(m), cy + 5 * math.sin(m), "main.0")
        c.line(cx, cy, cx + 3 * math.cos(-0.6), cy + 3 * math.sin(-0.6), "main.0")
        c.pset(cx, cy, "warm.1")

        # robot, typing: a 1px bob on the beat
        bob = 1 if int(t * 4) % 2 else 0
        blinking = (t % 3.2) > 3.0
        look = -1 if (t % 5) > 3.5 else 0
        props.robot(c, 60, DESK - 2 + bob, s=24, t=t, blink=blinking, look=look)


        # laptop lid, back side to us
        lid = [(47, DESK - 1), (74, DESK - 1), (72, DESK - 10), (49, DESK - 10)]
        c.poly(lid, "main.2")
        c.line(49, DESK - 10, 72, DESK - 10, "main.4")
        c.line(47, DESK - 1, 49, DESK - 10, "main.3")
        c.rect(59, DESK - 7, 3, 3, "main.3")
        c.pset(60, DESK - 6, "acc.2")

        # mug and steam
        c.rect(19, DESK - 8, 8, 8, "warm.1")
        c.vline(19, DESK - 8, DESK - 1, "warm.2")
        c.hline(19, 26, DESK - 8, "warm.0")
        c.frame(27, DESK - 6, 3, 4, "warm.1")
        self.steam.draw(c, t)

        # lamp and its pool of light
        lx = 100
        c.rect(lx - 4, DESK - 2, 9, 2, "main.2")
        c.line(lx, DESK - 2, lx - 3, DESK - 13, "main.1")
        c.line(lx - 3, DESK - 13, lx + 3, DESK - 19, "main.1")
        c.poly([(lx + 1, DESK - 22), (lx + 9, DESK - 18), (lx + 5, DESK - 13)], "main.3")
        c.pset(lx + 5, DESK - 16, "warm.3")

        # desk
        shapes.slab(c, 0, DESK, c.w, 5, ["alt.1", "alt.2", "alt.3"], top=2)
        c.lighten(c.m_ellipse(lx + 4, DESK + 1, 12, 2), 1)
        c.lighten(c.m_ellipse(lx + 4, DESK + 1, 7, 1), 1)
        c.rect(0, DESK + 5, c.w, c.h - DESK - 5, "alt.0")
        c.frame(10, DESK + 10, 40, 16, "alt.1")
        c.rect(27, DESK + 17, 6, 2, "main.3")
        c.frame(70, DESK + 10, 40, 16, "alt.1")
        c.rect(87, DESK + 17, 6, 2, "main.3")

        fx.dust_motes(c, t, n=10, region=(70, 40, 45, 55), color="main.3")
        fx.vignette(c, 0.9)
        ui.caption(c, self.CAPTION, 133, font="tiny", show=prog(t, 0.5, 0.8))

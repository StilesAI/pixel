"""Measure explainer: a subject draws itself in from the ground up while a
bracket measures it and a readout counts. Then it comes alive (here, the
lighthouse lamp turns on and sweeps). Same structure as a 'how tall / how far
/ how much' explainer.

Change: HEIGHT_M, LABEL, the subject drawn in subject(), the palette.
"""
import math

from pixelkit import Canvas, Scene, fx, props, shapes, ui
from pixelkit.anim import ease, prog, tween

LABEL = "HEIGHT"
HEIGHT_M = 48
BASE = 176          # ground line of the subject
TOP = 64            # top of the subject


class Measure(Scene):
    W, H = 180, 225
    duration = 8
    palette = "ember"
    anim_fps = 15

    def setup(self):
        self.tower = Canvas(self.W, self.H)
        self.subject(self.tower)

    def subject(self, c):
        """The thing being measured, drawn once into its own layer."""
        x = 88
        h = BASE - TOP
        # tapered body
        for y in range(TOP + 16, BASE):
            u = (y - TOP - 16) / (h - 16)
            half = int(8 + 6 * u)
            band = ((y - TOP - 16) // 12) % 2
            ramp = ["warm.0", "warm.1", "warm.2", "warm.2"] if band else ["main.2", "main.3", "main.4", "main.5"]
            row = c.m_rect(x - half, y, 2 * half, 1)
            shapes.cylinder(c, x - half, y, 2 * half, 1, ramp, light=0.3, spec=False, mask=row)
        # gallery, lantern room, roof
        c.rect(x - 12, TOP + 13, 24, 3, "main.1")
        c.hline(x - 12, x + 11, TOP + 13, "main.3")
        c.rect(x - 6, TOP + 4, 12, 9, "main.0")
        c.rect(x - 4, TOP + 5, 8, 7, "warm.3")
        c.vline(x, TOP + 5, TOP + 11, "main.0")
        c.poly([(x - 8, TOP + 4), (x, TOP - 3), (x + 7, TOP + 4)], "warm.0")
        c.vline(x, TOP - 6, TOP - 3, "main.1")
        # door and windows
        c.rect(x - 2, BASE - 9, 5, 9, "main.0")
        for wy in (TOP + 34, TOP + 58, TOP + 82):
            c.rect(x - 1, wy, 2, 4, "main.0")

    def draw(self, c, t):
        c.gradient_v(0, 0, c.w, 150, ["bg.0", "bg.1", "bg.2", "bg.3", "bg.4", "acc.1"])
        fx.stars(c, t, n=30, region=(0, 0, c.w, 60))
        # setting sun on the horizon
        shapes.sphere(c, 140, 150, 16, ["warm.1", "warm.2", "warm.3", "acc.3"], light=(0, -0.3))
        props.water(c, 150, c.h, t, ramp=("cool.0", "cool.1", "acc.1", "acc.2"))
        for yy in range(152, 200, 3):  # sun path
            w = 6 + (yy - 150) // 4
            o = int(2 * math.sin(yy + t * 3))
            c.hline(140 - w // 2 + o, 140 + w // 2 + o, yy, "acc.1" if yy % 2 else "warm.2")
        # rocks
        props.rock(c, 88, BASE + 6, 70, 18, ramp=("alt.0", "alt.1", "alt.2", "alt.3"))
        props.rock(c, 50, BASE + 10, 30, 10, ramp=("alt.0", "alt.1", "alt.2", "alt.3"))

        # build from the ground up with a bright scanline
        ui.scan_reveal_up(c, self.tower, t, 0.5, 3.2)

        # bracket + readout
        u = ease(prog(t, 0.5, 3.2), "linear")
        cur_top = BASE - (BASE - TOP + 6) * u
        if u > 0:
            ui.bracket(c, 122, int(cur_top), BASE, "ui.3", side="left")
            ui.guide_h(c, 104, 121, int(cur_top), "ui.2")

        # lamp comes on and sweeps
        if t > 3.6:
            on = prog(t, 3.6, 3.9)
            a = (t - 3.6) * 1.6
            lx, ly = 88, TOP + 8
            reach = 120
            spread = 0.12
            for side in (1, -1):
                aa = a + (0 if side == 1 else math.pi)
                dx = math.cos(aa)
                if abs(dx) < 0.15:
                    continue
                pts = [(lx, ly - 1), (lx + reach * dx, ly - 10 - reach * spread),
                       (lx + reach * dx, ly + 6 + reach * spread)]
                k = on * min(1, abs(dx) * 1.5)
                c.lighten(c.m_poly(pts), 1, level=int(7 * k))
                core = [(lx, ly), (lx + reach * dx, ly - 4 - reach * spread * 0.4),
                        (lx + reach * dx, ly + 2 + reach * spread * 0.4)]
                c.lighten(c.m_poly(core), 1, level=int(16 * k))
            c.glow(lx, ly, 14 * on, steps=2)


        # HUD last so nothing shades it
        val = HEIGHT_M * min(1.0, u)
        ui.readout(c, 8, 8, LABEL, f"{val:.0f}", " M", w=64, show=prog(t, 0.1, 0.4))
        if t > 3.6:
            ui.tag(c, 8, 44, "LIGHT ON", fill="warm.1", color="ui.3")

"""Chain reaction: a ball rolls in, tips the first domino, and the rest fall
in sequence while a counter tracks them. For 'one small thing sets off the
next' explainers, step-by-step processes, compounding.

Change: N, LABEL, spacing, the palette.
"""
import math

from pixelkit import Canvas, Scene, fx, props, shapes, ui
from pixelkit.anim import ease, prog

N = 11
LABEL = "FALLEN"
CAPTION = "ONE PUSH"
TABLE = 104
DW, DH = 4, 17          # domino size
X0, GAP = 16, 8         # first domino x and spacing
T_HIT = 1.4             # ball reaches the first domino
STEP = 0.24             # seconds between dominoes


class Dominoes(Scene):
    W, H = 120, 150
    duration = 7
    palette = "harbor"
    anim_fps = 15

    def setup(self):
        self.dom = Canvas(DW, DH)
        shapes.slab(self.dom, 0, 0, DW, DH, ["main.0", "main.1", "main.4", "main.5"], top=1)
        self.dom.frame(0, 0, DW, DH, "main.0")
        self.dom.rect(1, DH // 2, DW - 2, 1, "main.2")
        for py in (4, 7, DH - 7, DH - 4):
            self.dom.pset(DW // 2, py, "main.0")
        # resting angle: leaning on the next domino
        self.rest = math.degrees(math.asin(min(1.0, (GAP - DW + DW) / DH * 0.98)))

    def domino(self, c, px, py, a):
        """Domino as a rotated polygon around its bottom-right corner (px, py).
        Polygons keep thin shapes clean where sprite rotation would stair-step."""
        r = math.radians(a)
        ca, sa = math.cos(r), math.sin(r)

        def p(dx, dy):  # dx, dy relative to pivot, unrotated (dy negative = up)
            return (px + dx * ca - dy * sa, py + dx * sa + dy * ca)
        corners = [p(-DW, 0), p(0, 0), p(0, -DH), p(-DW, -DH)]
        c.poly(corners, "main.4")
        c.line(*corners[3], *corners[0], "main.5")
        c.line(*corners[2], *corners[3], "main.5")
        c.line(*corners[1], *corners[2], "main.1")
        c.line(*corners[0], *corners[1], "main.0")
        mid = p(-DW / 2, -DH / 2)
        for f in (0.25, 0.75):
            c.pset(*p(-DW / 2, -DH * f), "main.0")

    def angle(self, i, t):
        t0 = T_HIT + i * STEP
        last = i == N - 1
        target = 90 if last else self.rest
        u = prog(t, t0, t0 + STEP * (1.6 if last else 1.0))
        return target * ease(u, "inQuad" if not last else "outBounce")

    def draw(self, c, t):
        c.gradient_v(0, 0, c.w, TABLE, ["bg.3", "bg.4", "bg.4"])
        # window light shape on the wall
        c.lighten(c.m_poly([(70, 0), (116, 0), (100, 84), (54, 84)]), 1, level=6)
        # framed print and a pendant lamp on the wall
        art = c.copy()
        art.gradient_v(70, 44, 38, 28, ["bg.2", "bg.3", "bg.4"])
        props.mountain(art, 82, 72, 34, 20, ramp=("cool.0", "cool.1", "cool.2"), snow="ui.3")
        props.mountain(art, 97, 72, 26, 14, ramp=("leaf.0", "leaf.1", "leaf.2"), snow=None)
        win = c.m_rect(70, 44, 38, 28)
        c.buf[win] = art.buf[win]
        c.frame(68, 42, 42, 32, "alt.1")
        c.frame(69, 43, 40, 30, "alt.3")
        lx = 92
        c.vline(lx, 0, 12, "main.1")
        c.poly([(lx - 7, 20), (lx + 7, 20), (lx + 3, 12), (lx - 3, 12)], "main.1")
        c.hline(lx - 7, lx + 7, 20, "main.0")
        c.hline(lx - 3, lx + 3, 21, "warm.3")

        # table
        shapes.slab(c, 0, TABLE, c.w, 6, ["alt.1", "alt.2", "alt.3", "alt.4"], top=2)
        c.rect(0, TABLE + 6, c.w, c.h - TABLE - 6, "alt.1")
        c.hline(0, c.w - 1, TABLE + 6, "alt.0")

        # ball rolls in from the left
        bx = -8 + (X0 - 4 + 8) * ease(prog(t, 0.2, T_HIT), "inQuad")
        if t > T_HIT:
            bx = X0 - 4 - 2 * ease(prog(t, T_HIT, T_HIT + 0.3), "outQuad")
        by = TABLE - 4
        c.shadow(bx, TABLE + 1, 5, 1)
        shapes.sphere(c, bx, by, 3.5, ["warm.0", "warm.1", "warm.2", "warm.3"])
        roll = int(bx * 0.8) % 4
        c.pset(bx - 1 + roll % 2, by - 1 + roll // 2, "warm.3")

        fallen = 0
        for i in range(N):
            x = X0 + i * GAP
            a = self.angle(i, t)
            if a > self.rest * 0.8:
                fallen += 1
            c.shadow(x + DW / 2 + a / 90 * DH * 0.5, TABLE + 1, DW / 2 + a / 90 * DH * 0.45, 1)
            self.domino(c, x + DW, TABLE, a)
            # dust where the last one lands
        if t > T_HIT + (N - 1) * STEP + STEP * 0.8:
            puff = prog(t, T_HIT + N * STEP, T_HIT + N * STEP + 0.8)
            if 0 < puff < 1:
                lx = X0 + (N - 1) * GAP + DW + DH * 0.6
                for k in range(5):
                    r = 1 + 2 * puff
                    c.disc(lx - 8 + k * 4 + (k - 2) * 3 * puff, TABLE - 2 - 2 * puff * (k % 2), r, "main.4")

        # counter
        ui.readout(c, 6, 6, LABEL, f"{fallen}/{N}", show=prog(t, 0.0, 0.3),
                   fill="ui.0", line="ui.1")
        if fallen == N:
            ui.tag(c, 6, 41, "DONE", fill="acc.1", color="ui.3")
        ui.caption(c, CAPTION, 128, font="tiny", fill="alt.0", color="alt.4", show=prog(t, 0.4, 0.7))

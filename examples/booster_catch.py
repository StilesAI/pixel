"""Booster catch: a rocket booster drops out of the night sky, lights its
landing burn, slides over to the tower, and the arms catch it.

    python -m pixelkit render examples/booster_catch.py
"""
import math

import numpy as np

from pixelkit import Canvas, Keys, Scene, fx, prog, ramp, shapes, ui

W, H = 180, 225
GROUND = 189
HORIZON = 177
BAR_Y = 197               # telemetry bar
TOWER_X, TOWER_W, TOWER_TOP = 122, 13, 22
ARM_Y = 60                 # arm hinge height on the tower
ARM_LEN = 36
BW, BH = 13, 86            # booster size
PIN = 11                   # catch pins, px below the booster top
CATCH_X = 99               # booster center x when caught
CATCH_TOP = ARM_Y - PIN
MOUNT_TOP = 163

T_IGNITE = 1.0
T_CATCH = 5.6
T_CUTOFF = 5.7
DECEL = 6.3                # px/s^2 during the landing burn
GRAV = 9.0                 # px/s^2 before it
M_PER_PX = 9.0

STEEL = ["main.0", "main.1", "main.2", "main.3", "main.4", "main.5"]
SKY = set(ramp("bg"))


def booster_top(t):
    """Free fall, then a constant-deceleration burn that ends at zero speed
    exactly at the catch. Physically right, so the counter feels right."""
    if t >= T_CATCH:
        return CATCH_TOP
    if t >= T_IGNITE:
        return CATCH_TOP - 0.5 * DECEL * (T_CATCH - t) ** 2
    top_i = booster_top(T_IGNITE)
    v_i = DECEL * (T_CATCH - T_IGNITE)
    d = T_IGNITE - t
    return top_i - v_i * d + 0.5 * GRAV * d * d


def booster_speed(t):
    if t >= T_CATCH:
        return 0.0
    if t >= T_IGNITE:
        return DECEL * (T_CATCH - t)
    return DECEL * (T_CATCH - T_IGNITE) - GRAV * (T_IGNITE - t)


class BoosterCatch(Scene):
    W, H = W, H
    duration = 7.8
    palette = "night"
    anim_fps = 15

    # ---------------------------------------------------------------- setup
    def setup(self):
        self.booster = self._make_booster()
        self.arm_front = self._make_arm(front=True)
        self.arm_back = self._make_arm(front=False)

        self.cx = Keys((0.0, 70), (T_IGNITE, 70), (2.6, 78, "inOutSine"), (4.5, CATCH_X, "inOutSine"))
        self.lean = Keys((0.0, -7), (T_IGNITE, -5, "outQuad"), (2.4, 6, "inOutSine"),
                         (3.9, -3, "inOutSine"), (4.9, 0, "outQuad"))
        self.arm_open = Keys((0.0, 1.0), (T_CATCH - 0.35, 1.0), (T_CATCH + 0.02, 0.0, "outCubic"))
        self.dip = Keys((0.0, 0), (T_CATCH, 0), (T_CATCH + 0.13, 3, "outQuad"),
                        (T_CATCH + 0.5, 0, "outBack"))

        self.sparks = fx.Emitter(seed=21, t0=T_IGNITE, t1=T_CUTOFF, rate=60, origin=self._nozzle,
                                 angle=90, spread=28, speed=(40, 85), life=(0.12, 0.4),
                                 gravity=50, colors=["ui.3", "warm.3", "warm.2", "warm.1"])
        # steam kicked up when the plume reaches the mount, then a lingering haze
        self.steam = fx.Billow(seed=4, center=(CATCH_X, MOUNT_TOP + 2), t0=self._plume_hits(),
                               n=40, spread=(84, 16), grow=(4, 12), rise=2.2, dur=2.6, drift=1.2,
                               ramp=("main.1", "main.2", "main.3", "main.4"),
                               fade_after=7.0, fade_dur=3.5)
        # contact sparks where the pins land on the arms
        self.contact = [fx.Emitter(seed=40 + k, t0=T_CATCH + 0.02, t1=T_CATCH + 0.1, rate=180,
                                   origin=(CATCH_X + side * (BW // 2 + 2), ARM_Y), angle=-90 + side * 35,
                                   spread=50, speed=(25, 60), life=(0.15, 0.4), gravity=160,
                                   colors=["ui.3", "warm.3", "warm.2"])
                        for k, side in enumerate((-1, 1))]
        rng = np.random.default_rng(2)
        self.flick = rng.uniform(0.84, 1.16, 400)

    def _plume_hits(self):
        t = T_IGNITE
        while t < T_CATCH and booster_top(t) + BH + 40 < MOUNT_TOP:
            t += 0.02
        return t

    def _nozzle(self, t):
        return self.cx(t), booster_top(t) + BH + 1

    def _make_booster(self):
        b = Canvas(BW + 8, BH + 3)          # 4px margin each side for grid fins
        x0 = 4
        shapes.cylinder(b, x0, 0, BW, BH, STEEL, light=0.3)
        # dark vented ring on top, lit lip under it
        b.rect(x0, 0, BW, 5, "main.0")
        for vx in range(x0 + 1, x0 + BW - 1, 2):
            b.rect(vx, 1, 1, 3, "main.2")
        b.hline(x0, x0 + BW - 1, 5, "main.4")
        # weld seams
        for sy in range(14, BH - 6, 9):
            b.darken(b.m_rect(x0, sy, BW, 1), 1)
        # engine section: one clean darker band
        b.darken(b.m_rect(x0, BH - 9, BW, 6), 1)
        b.hline(x0, x0 + BW - 1, BH - 10, "main.1")
        # grid fins seen edge-on
        for fx_ in (0, BW + 4):
            b.rect(fx_, 7, 4, 6, "main.1")
            b.frame(fx_, 7, 4, 6, "main.0")
            b.pset(fx_ + 1, 9, "main.3")
            b.pset(fx_ + 2, 10, "main.3")
        # catch pins
        b.rect(2, PIN, 2, 2, "main.4")
        b.rect(BW + 4, PIN, 2, 2, "main.3")
        # engine skirt and bells
        b.rect(x0 + 1, BH - 3, BW - 2, 3, "main.0")
        b.hline(x0 + 1, x0 + BW - 2, BH - 3, "main.2")
        for ex in range(x0 + 2, x0 + BW - 2, 3):
            b.rect(ex, BH, 2, 2, "main.1")
        return b

    def _make_arm(self, front):
        a = Canvas(ARM_LEN, 5)
        line = "main.2" if front else "main.0"
        hi = "main.4" if front else "main.1"
        shapes.truss_h(a, 0, 0, ARM_LEN, 5, line=line, hi=hi, cell=5)
        a.rect(0, 0, 3, 5, line)
        a.hline(0, 2, 0, hi)
        return a

    # ---------------------------------------------------------------- draw
    def thrust(self, t):
        if t < T_IGNITE or t > T_CUTOFF + 0.15:
            return 0.0
        up = prog(t, T_IGNITE, T_IGNITE + 0.14)
        down = 1 - 0.35 * prog(t, 4.6, T_CATCH)
        off = 1 - prog(t, T_CUTOFF, T_CUTOFF + 0.15)
        return up * down * off

    def draw(self, c, t):
        f = int(round(t * 15))
        s = self.thrust(t)
        flick = self.flick[f % len(self.flick)] if s > 0 else 0
        top = booster_top(t)
        bx, lean = self.cx(t), self.lean(t)
        nx, ny = self._nozzle(t)

        self._sky(c, t, f, s, nx, flick)
        self._land(c, t, f)

        # searchlights tracking the booster
        vis = prog(t, 0.2, 0.9)
        for gx in (34, 172):
            beam = c.m_poly([(gx - 1, GROUND), (gx + 1, GROUND),
                             (bx + 8, top + BH * 0.6), (bx - 8, top + BH * 0.35)])
            c.lighten(beam, 1, level=int(5 * vis))
            c.pset(gx, GROUND - 1, "ui.3")

        self._mount(c)
        self._tower(c, t)
        dip, op = self.dip(t), self.arm_open(t)
        c.blit_rotated(self.arm_back, -13 * op, (ARM_LEN - 1, 2), (TOWER_X, ARM_Y + dip))

        # engine light falls on the structures (not the sky)
        if s > 0:
            solid = ~np.isin(c.buf, list(SKY))
            c.glow(nx, ny + 18, 64 * s * flick, steps=2, mask=solid)
            c.glow(nx, ny + 8, 26 * s * flick, steps=1)

        # booster, lit from below while the engines run
        layer = Canvas(c.w, c.h)
        layer.blit_rotated(self.booster, lean, (BW / 2 + 4, BH), (bx, top + BH))
        if s > 0:
            # underside catches the flame: clean bands, no noise
            bm = layer.m_opaque()
            yy = np.arange(c.h)[:, None]
            near = bm & (yy > ny - 4 - 22 * s)
            layer.lighten(near, 1)
            layer.tint(bm & (yy > ny - 4 - 5 * s), to="warm")
        c.blit(layer, 0, 0)

        if s > 0:
            self._plume(c, nx, ny, s, flick, lean, f)
            self.sparks.draw(c, t)

        c.blit_rotated(self.arm_front, 11 * op, (ARM_LEN - 1, 2), (TOWER_X, ARM_Y + 1 + dip))
        if op < 0.02 and (t * 2) % 1 < 0.6:
            c.pset(TOWER_X - ARM_LEN + 1, ARM_Y + 1 + dip, "acc.2")

        # steam, lit orange near the flame while it burns
        before = c.buf.copy()
        self.steam.draw(c, t)
        for e in self.contact:
            e.draw(c, t)
        if s > 0:
            cloud = c.buf != before
            c.tint_radial(nx, MOUNT_TOP, 30 * s * flick, to="warm", mask=cloud, inner=0.35)

        # ignition flash, shake, vignette
        if T_IGNITE <= t < T_IGNITE + 0.12:
            c.lighten(None, 1)
        dx, dy = fx.shake(t, T_IGNITE, T_IGNITE + 0.5, amp=1.5)
        dx2, dy2 = fx.shake(t, T_CATCH, T_CATCH + 0.35, amp=1.2, seed=9)
        c.shift(dx + dx2, dy + dy2)
        fx.vignette(c, 0.7)

        self._hud(c, t)

    # ---------------------------------------------------------------- parts
    def _sky(self, c, t, f, s, nx, flick):
        c.gradient_v(0, 0, c.w, HORIZON, ["bg.0", "bg.0", "bg.1", "bg.2", "bg.3"])
        fx.stars(c, t, seed=5, n=60, region=(0, 0, c.w, HORIZON - 40))
        # moon
        shapes.sphere(c, 140, 12, 9, ["bg.3", "bg.4", "ui.2", "ui.3"], light=(-0.7, -0.5))
        c.disc(136, 9, 2, "bg.4")
        c.disc(144, 16, 1, "bg.4")
        # horizon line and sea
        c.hline(0, c.w - 1, HORIZON - 1, "bg.4")
        c.rect(0, HORIZON, c.w, GROUND - HORIZON, "bg.1")
        rng = np.random.default_rng(100 + f // 3)
        for _ in range(14):
            sx, sy = rng.integers(0, c.w), rng.integers(HORIZON + 1, GROUND - 1)
            c.hline(sx, sx + rng.integers(1, 4), sy, "bg.2")
        for yy in range(HORIZON + 2, GROUND - 1, 2):  # moon path
            off = int(2 * math.sin(yy * 1.7 + t * 3))
            c.hline(140 + off - 1, 140 + off + 1, yy, "bg.3")
        if s > 0:  # plume glints on the water
            for yy in range(HORIZON + 1, GROUND - 1):
                if rng.uniform() < 0.55:
                    spread = 2 + 7 * s * (yy - HORIZON) / (GROUND - HORIZON)
                    gx = nx + rng.uniform(-spread, spread)
                    c.hline(gx, gx + rng.integers(0, 3), yy, "warm.1" if rng.uniform() < 0.7 else "warm.2")

    def _land(self, c, t, f):
        # tank farm
        for tx, th, tw in ((4, 18, 7), (13, 25, 9), (24, 15, 7), (33, 21, 8)):
            shapes.cylinder(c, tx, GROUND - th, tw, th, ["bg.0", "bg.1", "bg.2", "bg.2"],
                            light=0.3, spec=False)
            c.hline(tx, tx + tw - 1, GROUND - th, "bg.3")
            if math.sin(t * 1.7 + tx) > 0.1:
                c.pset(tx + 2, GROUND - th + 3, "warm.2")
        # ground and pad
        c.rect(0, GROUND, c.w, c.h - GROUND, "alt.0")
        c.hline(0, c.w - 1, GROUND, "alt.1")
        c.rect(60, GROUND, 100, 5, "main.0")
        c.hline(60, 159, GROUND, "main.2")
        for i, lx in enumerate(range(64, 158, 10)):
            if (i + f // 6) % 4:
                c.pset(lx, GROUND + 2, "warm.2")
        for yy in range(GROUND + 7, c.h, 4):
            for xx in range((yy * 7) % 11, c.w, 13):
                c.pset(xx, yy, "alt.1")

    def _mount(self, c):
        x0, x1 = 78, 121
        for lx in (81, 90, 107, 116):
            c.rect(lx, MOUNT_TOP + 6, 3, GROUND - MOUNT_TOP - 6, "main.0")
            c.vline(lx, MOUNT_TOP + 6, GROUND - 1, "main.1")
        c.rect(x0, MOUNT_TOP, x1 - x0, 7, "main.1")
        c.hline(x0, x1 - 1, MOUNT_TOP, "main.3")
        c.hline(x0, x1 - 1, MOUNT_TOP + 6, "main.0")
        c.rect(CATCH_X - 8, MOUNT_TOP + 1, 16, 5, "bg.0")

    def _tower(self, c, t):
        x, w = TOWER_X, TOWER_W
        c.rect(x + 1, TOWER_TOP, w - 2, GROUND - TOWER_TOP, "bg.0")
        shapes.truss(c, x, TOWER_TOP, w, GROUND - TOWER_TOP, line="main.1", hi="main.2", cell=7)
        c.vline(x + w - 1, TOWER_TOP, GROUND - 1, "main.0")
        for py in range(TOWER_TOP + 30, GROUND - 14, 28):  # service platforms
            c.rect(x - 1, py, w + 2, 2, "main.1")
            c.hline(x - 1, x + w, py, "main.3")
        c.vline(x + w - 3, TOWER_TOP, GROUND - 1, "main.0")  # pipe run
        c.rect(x - 2, GROUND - 12, w + 4, 12, "main.0")
        c.hline(x - 2, x + w + 1, GROUND - 12, "main.2")
        # crown, jib and mast
        c.rect(x - 1, TOWER_TOP - 4, w + 2, 4, "main.1")
        c.hline(x - 1, x + w, TOWER_TOP - 4, "main.3")
        shapes.truss_h(c, x + w - 2, TOWER_TOP - 9, 20, 4, line="main.1", hi="main.2", cell=4)
        c.vline(x + w // 2, TOWER_TOP - 20, TOWER_TOP - 5, "main.2")
        # arm carriage rides on the tower
        dip = self.dip(t)
        c.rect(x - 2, ARM_Y - 5 + dip, 6, 12, "main.1")
        c.frame(x - 2, ARM_Y - 5 + dip, 6, 12, "main.0")
        c.hline(x - 2, x + 3, ARM_Y - 5 + dip, "main.3")
        # aviation lights
        if (t * 1.1) % 1.0 < 0.45:
            c.pset(x + w // 2, TOWER_TOP - 21, "warm.1")
            c.pset(x, TOWER_TOP + 70, "warm.1")
            c.pset(x + w - 1, TOWER_TOP + 70, "warm.1")
        if ((t + 0.5) * 1.1) % 1.0 < 0.45:
            c.pset(x + w + 17, TOWER_TOP - 9, "warm.1")

    def _plume(self, c, nx, ny, s, flick, lean, f):
        L = (32 + 12 * s) * s * flick
        tilt = math.radians(-lean)

        def pt(d, w):
            return (nx + math.sin(tilt) * d + w, ny + math.cos(tilt) * d)

        hit = max(0.0, ny + L - MOUNT_TOP)
        layer = Canvas(c.w, c.h)
        for frac, width, col in ((1.0, 5.5, "warm.1"), (0.78, 4.2, "warm.2"), (0.52, 2.8, "warm.3"),
                                 (0.26, 1.5, "ui.3")):
            d = L * frac
            w = width * (0.75 + 0.25 * s)
            layer.poly([pt(0, -w), pt(0, w), pt(d * 0.55, w * 1.05), pt(d, 0), pt(d * 0.55, -w * 1.05)], col)
        for k in range(1, 4):
            d = L * 0.17 * k
            if d < L * 0.6:
                x, y = pt(d, 0)
                layer.pset(x, y, "ui.3")
        if hit > 0:
            # the plume flattens against the mount and splashes sideways
            layer.buf[MOUNT_TOP:, :] = 255
            spread = min(24, 5 + hit * 1.3) * flick
            jr = np.random.default_rng(f)
            for side in (-1, 1):
                for k in range(5):
                    u = (k + 1) / 5
                    px = nx + side * spread * u + jr.uniform(-1.5, 1.5)
                    py = MOUNT_TOP - 1 - jr.uniform(0, 3) * (1 - u) - 1.5 * u
                    r = 3.2 * (1 - u * 0.75)
                    layer.disc(px, py, r, "warm.1")
                    if u < 0.6:
                        layer.disc(px, py + 0.5, r * 0.6, "warm.2")
            layer.ellipse(nx, MOUNT_TOP - 1, 4, 1.5, "warm.3")
            layer.buf[MOUNT_TOP:, :] = 255
        c.blit(layer, 0, 0)

    def _hud(self, c, t):
        dist = max(0.0, CATCH_TOP - booster_top(t)) * M_PER_PX
        speed = booster_speed(t) * M_PER_PX * 3.6
        # telemetry bar along the bottom, like a launch webcast
        c.rect(0, BAR_Y, c.w, c.h - BAR_Y, "ui.0")
        c.hline(0, c.w - 1, BAR_Y, "ui.1")
        c.text("DISTANCE TO ARMS", 7, BAR_Y + 4, "ui.2", font="tiny")
        c.text(f"{dist:,.0f} M", 7, BAR_Y + 11, "ui.3", scale=2)
        c.vline(112, BAR_Y + 4, c.h - 5, "ui.1")
        c.text("SPEED", 118, BAR_Y + 4, "ui.2", font="tiny")
        c.text(f"{speed:,.0f}", 118, BAR_Y + 11, "ui.3")
        c.text("KM/H", 118 + Canvas.measure(f"{speed:,.0f}") + 3, BAR_Y + 13, "ui.2", font="tiny")
        clock = 6 * 60 + 41 + t
        c.text(f"T+{int(clock // 60):02d}:{int(clock % 60):02d}", 118, c.h - 8, "ui.2", font="tiny")
        # status, top left
        c.text("BOOSTER CATCH", 7, 7, "ui.2", font="tiny")
        if T_IGNITE <= t < T_CUTOFF + 0.15:
            if (t - T_IGNITE) > 0.5 or ((t - T_IGNITE) * 6) % 1 < 0.6:
                ui.tag(c, 7, 15, "LANDING BURN", fill="warm.1")
        if t >= T_CUTOFF + 0.15:
            if t >= T_CUTOFF + 0.4 or int(t * 30) % 2 == 0:
                ui.tag(c, 7, 15, "CAUGHT", fill="acc.1")

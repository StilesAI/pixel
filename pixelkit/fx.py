"""Effects: particles, stars, clouds of smoke/steam, weather, fades.

Everything is deterministic: a frame depends only on (seed, t), so any frame
can be rendered on its own, previews match the final video exactly, and
re-renders never flicker differently.
"""
from __future__ import annotations

import math

import numpy as np

from .canvas import BAYER4, Canvas, Dither
from .palette import ref


# ------------------------------------------------------------------ particles

class Emitter:
    """Spawns particles between t0 and t1.

    origin   (x, y) or fn(t) -> (x, y)
    angle    direction in degrees (0 = right, 90 = down, -90 = up)
    spread   +/- degrees
    speed    (min, max) px/s
    life     (min, max) seconds
    gravity  px/s^2 (positive = down)
    drag     0 = none, 2 = heavy (exponential)
    colors   ramp from birth -> death, e.g. ["warm.3", "warm.2", "warm.1", "main.1"]
    size     (start radius, end radius); 0 = single pixel
    jitter   spawn position spread in px (x, y)
    """

    def __init__(self, seed=1, t0=0.0, t1=1.0, rate=30, origin=(0, 0), angle=-90, spread=20,
                 speed=(20, 40), life=(0.5, 1.0), gravity=0.0, drag=0.0,
                 colors=("ui.3",), size=(0, 0), jitter=(0, 0), wind=0.0):
        self.origin = origin
        self.gravity = gravity
        self.drag = drag
        self.colors = [ref(c) for c in colors]
        self.size = size
        self.wind = wind
        rng = np.random.default_rng(seed)
        n = max(0, int((t1 - t0) * rate))
        self.birth = np.sort(rng.uniform(t0, t1, n))
        ang = np.radians(angle + rng.uniform(-spread, spread, n))
        spd = rng.uniform(speed[0], speed[1], n)
        self.vx = np.cos(ang) * spd
        self.vy = np.sin(ang) * spd
        self.life = rng.uniform(life[0], life[1], n)
        self.jx = rng.uniform(-jitter[0], jitter[0], n) if jitter[0] else np.zeros(n)
        self.jy = rng.uniform(-jitter[1], jitter[1], n) if jitter[1] else np.zeros(n)
        self.ox = np.zeros(n)
        self.oy = np.zeros(n)
        if not callable(origin):
            self.ox[:] = origin[0]
            self.oy[:] = origin[1]
        else:
            for i, b in enumerate(self.birth):
                self.ox[i], self.oy[i] = origin(b)

    def positions(self, t):
        age = t - self.birth
        alive = (age >= 0) & (age < self.life)
        a = age[alive]
        if self.drag > 0:
            k = self.drag
            f = (1 - np.exp(-k * a)) / k
        else:
            f = a
        x = self.ox[alive] + self.jx[alive] + self.vx[alive] * f + 0.5 * self.wind * a * a
        y = self.oy[alive] + self.jy[alive] + self.vy[alive] * f + 0.5 * self.gravity * a * a
        u = a / self.life[alive]
        return x, y, u

    def draw(self, c: Canvas, t: float):
        x, y, u = self.positions(t)
        if len(x) == 0:
            return
        nc = len(self.colors)
        ci = np.minimum((u * nc).astype(int), nc - 1)
        r0, r1 = self.size
        # draw older particles first so fresh ones sit on top
        for i in np.argsort(-u):
            col = self.colors[ci[i]]
            r = r0 + (r1 - r0) * u[i]
            if r < 0.75:
                c.pset(x[i], y[i], col)
            else:
                c.disc(x[i], y[i], r, col)


# ------------------------------------------------------------------ sky

def stars(c: Canvas, t: float, seed=7, n=60, region=None, colors=("bg.4", "ui.3"),
          twinkle=0.35, avoid=None):
    """Static star field with gentle twinkle."""
    rng = np.random.default_rng(seed)
    x0, y0, w, h = region or (0, 0, c.w, c.h)
    xs = rng.integers(x0, x0 + w, n)
    ys = rng.integers(y0, y0 + h, n)
    ph = rng.uniform(0, 1, n)
    sp = rng.uniform(0.6, 1.8, n)
    big = rng.uniform(0, 1, n) > 0.9
    cols = [ref(k) for k in colors]
    for i in range(n):
        if avoid is not None and avoid[ys[i], xs[i]]:
            continue
        s = math.sin(2 * math.pi * (t * sp[i] + ph[i]))
        if s < -1 + 2 * twinkle and not big[i]:
            continue
        col = cols[-1] if (big[i] or s > 0.6) else cols[0]
        c.pset(xs[i], ys[i], col)
        if big[i] and s > 0.2:
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                c.pset(xs[i] + dx, ys[i] + dy, cols[0])


# ------------------------------------------------------------------ volumes

def puff(c: Canvas, x, y, r, ramp=("main.1", "main.2", "main.3", "main.4"), light=(-0.6, -0.8)):
    """One shaded ball of smoke/steam/cloud. ramp is dark -> light."""
    if r < 0.6:
        c.pset(x, y, ramp[-1])
        return
    lx, ly = light
    c.disc(x, y, r, ramp[0])
    if r >= 2:
        c.disc(x + lx * r * 0.18, y + ly * r * 0.18, r * 0.82, ramp[1])
    if len(ramp) > 2 and r >= 3:
        c.disc(x + lx * r * 0.32, y + ly * r * 0.32, r * 0.55, ramp[2])
    if len(ramp) > 3 and r >= 5:
        c.disc(x + lx * r * 0.45, y + ly * r * 0.45, r * 0.25, ramp[3])


class Billow:
    """A growing cloud of puffs: launch steam, explosions, dust, fog banks.

    center   (x, y) where it starts
    t0       start time
    n        number of puffs
    spread   (sx, sy) how far puffs travel (px)
    grow     (r_start, r_end) puff radius range
    rise     upward drift px/s after spreading
    dur      seconds to reach full spread
    """

    def __init__(self, seed=3, center=(90, 280), t0=0.0, n=24, spread=(70, 18), grow=(2, 11),
                 rise=4.0, dur=2.5, ramp=("main.1", "main.2", "main.3", "main.4"),
                 fade_after=None, fade_dur=2.0, drift=0.0, light=(-0.6, -0.8), rim=None):
        rng = np.random.default_rng(seed)
        self.center, self.t0, self.dur, self.rise = center, t0, dur, rise
        self.ramp = ramp
        self.drift = drift
        self.light = light
        self.rim = rim
        self._last = None
        self.fade_after, self.fade_dur = fade_after, fade_dur
        ang = rng.uniform(math.pi, 2 * math.pi, n)  # upper half + sides
        d = rng.uniform(0.25, 1.0, n) ** 0.7
        self.dx = np.cos(ang) * d * spread[0]
        self.dy = np.sin(ang) * d * spread[1]
        self.r = rng.uniform(grow[0], grow[1], n) * (1.15 - 0.5 * d)
        self.delay = rng.uniform(0, 0.35, n) * dur
        order = np.argsort(self.dy)  # far/high puffs first
        self.order = order

    def puffs(self, t: float):
        cx, cy = self.center
        out = []
        for i in self.order:
            a = t - self.t0 - self.delay[i]
            if a <= 0:
                continue
            u = 1 - (1 - min(1.0, a / self.dur)) ** 3
            x = cx + self.dx[i] * u + self.drift * a
            y = cy + self.dy[i] * u - self.rise * max(0.0, a - self.dur * 0.5)
            r = self.r[i] * (0.25 + 0.75 * u)
            if self.fade_after is not None:
                f = (t - self.fade_after) / self.fade_dur
                if f > 0:
                    r *= max(0.0, 1 - f)
            if r > 0.4:
                out.append((x, y, r))
        return out

    def draw(self, c: Canvas, t: float):
        """Draw the cloud as one mass lit from the upper left: a flat body,
        a lit rim along the top edges, a shadow along the bottom edges, and a
        few soft inner lumps. Reads as one cloud instead of a pile of balls."""
        ps = self.puffs(t)
        if not ps:
            return
        S = np.zeros(c.shape, bool)
        for x, y, r in ps:
            S |= c.m_disc(x, y, r)
        if not S.any():
            return
        r0, r1, r2, r3 = (list(self.ramp) + [self.ramp[-1]] * 4)[:4]
        c.paint(S, r1)
        # soft inner lumps on the bigger puffs (upper-left of each)
        lumps = np.zeros(c.shape, bool)
        for x, y, r in ps:
            if r >= 4:
                lumps |= c.m_disc(x - r * 0.25, y - r * 0.3, r * 0.55)
        c.paint(lumps & S, r2)
        # lit top-left rim and bottom shadow, following the bumpy outline
        top2 = S & ~_shift(S, 2, 1)
        top1 = S & ~_shift(S, 1, 1)
        bot = S & ~_shift(S, -2, -1)
        c.paint(top2, r2)
        c.paint(top1, r3)
        c.paint(bot & ~top1, r0)
        if self.rim:
            c.outline_mask(S, self.rim)


def _shift(m, dy, dx):
    """m moved down by dy and right by dx (False fills the gap)."""
    out = np.zeros_like(m)
    h, w = m.shape
    ys = slice(max(0, dy), h + min(0, dy))
    yd = slice(max(0, -dy), h + min(0, -dy))
    xs = slice(max(0, dx), w + min(0, dx))
    xd = slice(max(0, -dx), w + min(0, -dx))
    out[ys, xs] = m[yd, xd]
    return out


# ------------------------------------------------------------------ weather

def rain(c: Canvas, t, seed=11, n=80, speed=260, slant=0.25, length=5, color="cool.2"):
    rng = np.random.default_rng(seed)
    xs = rng.uniform(0, c.w + 40, n)
    ph = rng.uniform(0, 1, n)
    for i in range(n):
        y = ((t * speed / (c.h + 20)) + ph[i]) % 1.0 * (c.h + 20) - 10
        x = xs[i] - y * slant
        c.line(x, y, x - length * slant, y - length, color)


def snow(c: Canvas, t, seed=12, n=70, speed=18, color="ui.3"):
    rng = np.random.default_rng(seed)
    xs = rng.uniform(0, c.w, n)
    ph = rng.uniform(0, 1, n)
    sw = rng.uniform(0.5, 1.5, n)
    for i in range(n):
        y = ((t * speed * sw[i] / c.h) + ph[i]) % 1.0 * c.h
        x = xs[i] + 3 * math.sin(t * sw[i] * 2 + ph[i] * 6)
        c.pset(x, y, color)


def dust_motes(c: Canvas, t, seed=13, n=25, region=None, color="ui.2"):
    rng = np.random.default_rng(seed)
    x0, y0, w, h = region or (0, 0, c.w, c.h)
    bx = rng.uniform(x0, x0 + w, n)
    by = rng.uniform(y0, y0 + h, n)
    ph = rng.uniform(0, 6.28, n)
    for i in range(n):
        x = bx[i] + 4 * math.sin(t * 0.7 + ph[i])
        y = by[i] - (t * 3 + ph[i] * 5) % h * 0.15 + 2 * math.cos(t * 0.5 + ph[i])
        if math.sin(t * 1.3 + ph[i]) > -0.3:
            c.pset(x, y, color)


# ------------------------------------------------------------------ screen

def fade(c: Canvas, amount: float, to="bg.0"):
    """Dithered fade to a color. amount 0..1."""
    lvl = int(round(max(0, min(1, amount)) * 16))
    if lvl <= 0:
        return
    _, _, b = c._g()
    c.buf[b < lvl] = ref(to)


def vignette(c: Canvas, strength=1.0, steps=1):
    """Darken toward the corners, palette-consistent."""
    yy, xx, b = c._g()
    nx = (xx - c.w / 2) / (c.w / 2)
    ny = (yy - c.h / 2) / (c.h / 2)
    d = np.sqrt(nx * nx * 1.1 + ny * ny * 0.9)
    for s in range(steps):
        edge = 0.85 + 0.25 * s
        lvl = np.clip((d - edge) / 0.3 * 16 * strength, 0, 16)
        c.darken(b < lvl)


def shake(t, t0, t1, amp=2.0, freq=30, seed=5):
    """Camera shake offset (dx, dy) in whole pixels."""
    if not (t0 <= t <= t1):
        return 0, 0
    u = 1 - (t - t0) / max(1e-6, t1 - t0)
    k = int(t * freq)
    rng = np.random.default_rng(seed + k)
    return int(round(rng.uniform(-1, 1) * amp * u)), int(round(rng.uniform(-1, 1) * amp * u))


def heat_haze(c: Canvas, t, y0, y1, amp=1, x0=0, x1=None):
    """Shimmer rows sideways (engine heat, desert air)."""
    x1 = c.w if x1 is None else x1
    for y in range(max(0, int(y0)), min(c.h, int(y1))):
        dx = int(round(amp * math.sin(y * 0.9 + t * 25)))
        if dx:
            c.buf[y, x0:x1] = np.roll(c.buf[y, x0:x1], dx)

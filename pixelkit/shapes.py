"""Shaded forms. Light comes from the upper left by default, ramps are
dark -> light, and every transition is a clean band with a thin ordered-dither
seam, which is what makes code-drawn shapes read as hand-shaded pixel art."""
from __future__ import annotations

import math

import numpy as np

from .canvas import Canvas
from .palette import ref


def _quantize(c: Canvas, I, mask, ramp, dither_band=0.35):
    """Map intensity 0..1 to ramp slots. Most of each band is flat; only the
    last `dither_band` of it dithers into the next level."""
    cols = np.array([ref(r) for r in ramp], np.uint8)
    n = len(cols) - 1
    _, _, b = c._g()
    u = np.clip(I, 0, 1) * n
    k = np.clip(np.floor(u).astype(int), 0, max(0, n - 1)) if n > 0 else np.zeros_like(u, int)
    frac = u - k
    lvl = np.clip((frac - (1 - dither_band)) / dither_band * 16, 0, 16)
    out = np.where(b < lvl, cols[np.minimum(k + 1, n)], cols[k])
    c.buf[mask] = out[mask]


def cylinder(c: Canvas, x, y, w, h, ramp, light=0.3, ambient=0.12, spec=True, mask=None):
    """Vertical cylinder (tower, booster, can, column).
    light = where across the width the highlight sits (0 = left edge)."""
    region = c.m_rect(x, y, w, h)
    if mask is not None:
        region &= mask
    yy, xx, _ = c._g()
    u = (xx + 0.5 - x) / max(1, w)  # 0..1 across
    nx = u * 2 - 1
    nz = np.sqrt(np.clip(1 - nx * nx, 0, 1))
    lx = light * 2 - 1
    lz = math.sqrt(max(0.0, 1 - lx * lx))
    I = np.clip(nx * lx + nz * lz, 0, 1)
    I = ambient + (1 - ambient) * I ** 2.2
    if spec:
        I = np.where(I > 0.93, 1.0, np.minimum(I, 0.84))
    else:
        I = np.minimum(I, 0.84)
    _quantize(c, I, region, ramp)
    return region


def sphere(c: Canvas, cx, cy, r, ramp, light=(-0.55, -0.65), ambient=0.1, rim=None):
    region = c.m_disc(cx, cy, r)
    yy, xx, _ = c._g()
    nx = (xx - cx) / max(0.5, r)
    ny = (yy - cy) / max(0.5, r)
    nz = np.sqrt(np.clip(1 - nx * nx - ny * ny, 0, 1))
    lx, ly = light
    lz = math.sqrt(max(0.0, 1 - lx * lx - ly * ly))
    I = np.clip(nx * lx + ny * ly + nz * lz, 0, 1)
    I = ambient + (1 - ambient) * I ** 1.2
    _quantize(c, I, region, ramp)
    if rim is not None:
        edge = region & ~_shrink(region)
        lower = edge & ((xx - cx) * lx + (yy - cy) * ly > 0)
        c.paint(lower, rim)
    return region


def slab(c: Canvas, x, y, w, h, ramp, top=2, side=None, edge_light=True):
    """Front-facing block with a lit top lip and darker bottom, for ledges,
    floors, platforms, crates. side: 'left'|'right' adds a thin side face."""
    lo, mid, hi = ramp[0], ramp[len(ramp) // 2], ramp[-1]
    c.rect(x, y, w, h, mid)
    c.rect(x, y, w, top, hi)
    c.rect(x, y + h - 1, w, 1, lo)
    if side == "right":
        c.rect(x + w - 2, y + top, 2, h - top, ramp[max(0, len(ramp) // 2 - 1)])
    elif side == "left":
        c.rect(x, y + top, 2, h - top, ramp[max(0, len(ramp) // 2 - 1)])
    if edge_light:
        c.pset(x, y, ramp[-1])


def truss(c: Canvas, x, y, w, h, line="main.2", hi="main.4", cell=None, double=True):
    """Lattice tower section: two uprights with X bracing every `cell` px."""
    cell = cell or max(6, w)
    c.vline(x, y, y + h - 1, line)
    c.vline(x + w - 1, y, y + h - 1, line)
    if double:
        c.vline(x + 1, y, y + h - 1, hi)
    yy = y
    while yy < y + h - 1:
        y2 = min(y + h - 1, yy + cell)
        c.line(x, yy, x + w - 1, y2, line)
        c.line(x + w - 1, yy, x, y2, line)
        c.hline(x, x + w - 1, yy, hi)
        yy = y2
    c.hline(x, x + w - 1, y + h - 1, line)


def truss_h(c: Canvas, x, y, w, h, line="main.2", hi="main.4", cell=None):
    """Horizontal lattice beam (crane arm, bridge span)."""
    cell = cell or max(6, h)
    c.hline(x, x + w - 1, y, hi)
    c.hline(x, x + w - 1, y + h - 1, line)
    xx = x
    while xx < x + w - 1:
        x2 = min(x + w - 1, xx + cell)
        c.line(xx, y, x2, y + h - 1, line)
        c.line(xx, y + h - 1, x2, y, line)
        c.vline(xx, y, y + h - 1, line)
        xx = x2
    c.vline(x + w - 1, y, y + h - 1, line)


def lit_window(c: Canvas, x, y, w=2, h=3, on=True, col_on="warm.3", col_off="bg.1"):
    c.rect(x, y, w, h, col_on if on else col_off)


def _shrink(m):
    g = m.copy()
    g[1:, :] &= m[:-1, :]
    g[:-1, :] &= m[1:, :]
    g[:, 1:] &= m[:, :-1]
    g[:, :-1] &= m[:, 1:]
    return g


def ground(c: Canvas, y, ramp=("alt.0", "alt.1", "alt.2"), seed=4, rough=True):
    """Flat ground plane from y to the bottom with a lit top edge and specks."""
    c.rect(0, y, c.w, c.h - y, ramp[0])
    c.rect(0, y, c.w, 2, ramp[1])
    c.hline(0, c.w - 1, y, ramp[-1])
    if rough:
        rng = np.random.default_rng(seed)
        for _ in range(c.w // 3):
            px = rng.integers(0, c.w)
            py = rng.integers(y + 3, c.h)
            c.pset(px, py, ramp[1])

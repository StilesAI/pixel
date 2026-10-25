"""Props: shaded scenery drawn in code. Each takes a canvas and a base point
(usually the bottom center or bottom left) and follows the palette, so a
forest, a skyline, or a desk setup recolors with the rest of the scene."""
from __future__ import annotations

import math

import numpy as np

from . import fx, shapes
from .canvas import Canvas


# ------------------------------------------------------------------ nature

def pine(c: Canvas, x, base, h, ramp=("leaf.0", "leaf.1", "leaf.2", "leaf.3"), trunk="alt.1", sway=0.0):
    """Layered pine: tiers drawn bottom-up so each one shades the tier below,
    lit on the left, with a jagged needle edge along each tier's base."""
    x = round(x)
    tw = max(2, h // 12)
    c.rect(x - tw // 2, base - h // 6, tw, h // 6, trunk)
    tiers = max(3, h // 12)
    top = base - h
    body = h * 0.86
    for i in reversed(range(tiers)):
        u = i / max(1, tiers - 1)
        th = max(5, int(body / tiers * 1.7))
        ty = top + int(u * (body - th))
        half = 2 + int((h * 0.30) * (0.3 + 0.7 * u))
        dx = sway * (1 - u)
        ax = x + dx
        by = ty + th
        tri = c.m_poly([(ax, ty), (x + half, by), (x - half, by)])
        c.paint(tri, ramp[1])
        lit = c.m_poly([(ax, ty), (x - half, by), (x - half * 0.15, by)]) & tri
        c.paint(lit, ramp[2])
        edge = c.m_line(ax, ty, x - half, by) & tri
        c.paint(edge, ramp[3] if len(ramp) > 3 else ramp[2])
        # jagged needle fringe on the base
        for k, fx_ in enumerate(range(int(x - half), int(x + half) + 1, 2)):
            c.pset(fx_, by + 1, ramp[1] if fx_ > x else ramp[2])
        # shadow the tier below, just under this one
        under = c.m_rect(x - half + 2, by + 2, 2 * half - 3, 2)
        c.darken(under & ~tri, 1, level=10)


def round_tree(c: Canvas, x, base, r, ramp=("leaf.0", "leaf.1", "leaf.2", "leaf.3"), trunk="alt.1"):
    c.rect(x - 1, base - r - 2, 3, r + 2, trunk)
    cy = base - r * 2
    for dx, dy, rr in ((-r * 0.5, r * 0.25, r * 0.7), (r * 0.5, r * 0.3, r * 0.65), (0, -r * 0.2, r * 0.8)):
        shapes.sphere(c, x + dx, cy + dy, rr, ramp)


def bush(c: Canvas, x, base, w, ramp=("leaf.0", "leaf.1", "leaf.2", "leaf.3")):
    r = w / 4
    for k in range(3):
        shapes.sphere(c, x - w / 3 + k * w / 3, base - r - (k == 1) * 2, r + (k == 1), ramp)


def mushroom(c: Canvas, x, base, s=1.0, cap=("warm.0", "warm.1", "warm.2", "warm.3"), stem="ui.3"):
    h = int(7 * s)
    c.rect(x - int(1 * s), base - h, max(2, int(3 * s)), h, "main.4")
    c.vline(x - int(1 * s), base - h, base - 1, "main.3")
    r = 5 * s
    cy = base - h
    m = c.m_ellipse(x, cy, r, r * 0.7) & (c._g()[0] <= cy + 1)
    c.paint(m, cap[1])
    hl = c.m_ellipse(x - r * 0.3, cy - r * 0.25, r * 0.55, r * 0.35) & m
    c.paint(hl, cap[2])
    c.hline(x - r, x + r, cy + 1, cap[0])
    for dx, dy in ((-r * 0.4, -r * 0.2), (r * 0.35, -r * 0.35), (r * 0.1, r * 0.1)):
        c.pset(x + dx, cy + dy, stem)


def rock(c: Canvas, x, base, w, h, ramp=("main.0", "main.1", "main.2", "main.3")):
    pts = [(x - w / 2, base), (x - w / 2 + 2, base - h * 0.7), (x - w / 6, base - h), (x + w / 3, base - h * 0.8),
           (x + w / 2, base)]
    c.poly(pts, ramp[1])
    c.poly([(x - w / 2 + 2, base - h * 0.7), (x - w / 6, base - h), (x, base - h * 0.4)], ramp[2])
    c.hline(x - w / 2, x + w / 2, base, ramp[0])


def mountain(c: Canvas, x, base, w, h, ramp=("bg.1", "bg.2", "bg.3"), snow="ui.3", seed=3):
    """Mountain with a lit left face, shadowed right face, and a snow cap."""
    peak = (x, base - h)
    c.poly([(x - w / 2, base), peak, (x + w / 2, base)], ramp[1])
    c.poly([(x - w / 2, base), peak, (x + w * 0.05, base)], ramp[2])
    rng = np.random.default_rng(seed)
    for k in range(4):  # ridges
        yy = base - h + h * (0.3 + 0.17 * k)
        c.line(x + w * 0.02, yy - 6, x + w * 0.12 + rng.integers(0, 4), yy, ramp[0])
    if snow:
        sh = h * 0.24
        pts = [peak, (x + w / 2 * sh / h, base - h + sh), (x + 2, base - h + sh * 0.7), (x - 2, base - h + sh),
               (x - w / 2 * sh / h, base - h + sh)]
        c.poly(pts, snow)


def cloud(c: Canvas, x, y, w, ramp=("bg.3", "bg.4", "ui.2", "ui.3"), seed=5):
    """Flat-bottomed cumulus."""
    b = fx.Billow(seed=seed, center=(x, y), t0=-10, n=max(4, int(w / 5)), spread=(w / 2, w / 7),
                  grow=(w / 9, w / 5), rise=0, dur=0.01, ramp=ramp)
    m = c.m_rect(x - w, y - w, w * 2, w + 1)
    tmp = Canvas(c.w, c.h)
    b.draw(tmp, 0)
    tmp.buf[~m] = 255
    c.blit(tmp, 0, 0)


def sun(c: Canvas, x, y, r, t=0.0, core=("warm.2", "warm.3", "ui.3"), rays="warm.2"):
    for k in range(8):
        a = k * math.pi / 4 + t * 0.4
        c.line(x + math.cos(a) * (r + 2), y + math.sin(a) * (r + 2),
               x + math.cos(a) * (r + 5), y + math.sin(a) * (r + 5), rays)
    shapes.sphere(c, x, y, r, list(core), light=(-0.4, -0.4))


def water(c: Canvas, y0, y1, t, ramp=("cool.0", "cool.1", "cool.2", "cool.3"), seed=8):
    """Water band with drifting highlight dashes."""
    c.gradient_v(0, y0, c.w, y1 - y0, list(ramp[:2]))
    rng = np.random.default_rng(seed)
    for i in range(int(c.w * (y1 - y0) / 60)):
        bx = rng.uniform(0, c.w)
        by = rng.integers(y0 + 1, y1)
        sp = rng.uniform(4, 10)
        ln = rng.integers(2, 5)
        x = (bx + t * sp) % (c.w + 10) - 5
        if math.sin(t * 2 + i) > -0.2:
            c.hline(x, x + ln, by, ramp[2] if i % 4 else ramp[3])


def fireflies(c: Canvas, t, n=12, region=None, seed=17, color="warm.3", halo="warm.2"):
    rng = np.random.default_rng(seed)
    x0, y0, w, h = region or (0, 0, c.w, c.h)
    for i in range(n):
        ph = rng.uniform(0, 6.28)
        bx, by = rng.uniform(x0, x0 + w), rng.uniform(y0, y0 + h)
        x = bx + 6 * math.sin(t * 0.6 + ph)
        y = by + 4 * math.sin(t * 0.9 + ph * 1.7)
        on = math.sin(t * 2.2 + ph * 3)
        if on > 0.2:
            c.pset(x, y, color)
            if on > 0.7:
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    c.pset(x + dx, y + dy, halo)


# ------------------------------------------------------------------ built

def building(c: Canvas, x, base, w, h, ramp=("main.0", "main.1", "main.2"), lit=0.5, t=0.0, seed=1,
             window_on="warm.2", window_off="main.0", roof=True):
    """Office/apartment block with a window grid. lit 0..1 = share of lights on."""
    c.rect(x, base - h, w, h, ramp[1])
    c.vline(x, base - h, base - 1, ramp[2])
    c.vline(x + w - 1, base - h, base - 1, ramp[0])
    if roof:
        c.rect(x - 1, base - h - 1, w + 2, 2, ramp[2])
    rng = np.random.default_rng(seed)
    order = rng.uniform(0, 1, 400)
    k = 0
    for wy in range(base - h + 4, base - 4, 4):
        for wx in range(x + 2, x + w - 3, 3):
            on = order[k % 400] < lit
            c.rect(wx, wy, 2, 2, window_on if on else window_off)
            k += 1


def skyline(c: Canvas, base, t=0.0, lit=0.5, seed=4, ramp=("main.0", "main.1", "main.2"), hmin=30, hmax=90):
    rng = np.random.default_rng(seed)
    x = -4
    i = 0
    while x < c.w:
        w = int(rng.integers(14, 26))
        h = int(rng.integers(hmin, hmax))
        building(c, x, base, w, h, ramp, lit=lit, seed=seed * 31 + i)
        if rng.uniform() < 0.3:
            c.vline(x + w // 2, base - h - 8, base - h - 1, ramp[2])
            if (t * 1.2 + i * 0.3) % 1 < 0.5:
                c.pset(x + w // 2, base - h - 9, "warm.1")
        x += w + int(rng.integers(0, 4))
        i += 1


def house(c: Canvas, x, base, w=24, h=16, wall=("alt.1", "alt.2", "alt.3"), roof=("warm.0", "warm.1"),
          light=True):
    c.rect(x, base - h, w, h, wall[1])
    c.vline(x + w - 1, base - h, base - 1, wall[0])
    c.poly([(x - 3, base - h), (x + w // 2, base - h - w // 2), (x + w + 2, base - h)], roof[1])
    c.line(x - 3, base - h, x + w // 2, base - h - w // 2, roof[0])
    c.rect(x + 3, base - 9, 5, 9, wall[0])  # door
    c.rect(x + w - 10, base - h + 4, 6, 5, "warm.3" if light else "main.0")
    c.frame(x + w - 10, base - h + 4, 6, 5, wall[0])
    if light:
        c.glow(x + w - 7, base - h + 6, 10, steps=1)


def lamp_post(c: Canvas, x, base, h=28, on=True, head="main.2"):
    c.vline(x, base - h, base - 1, "main.1")
    c.hline(x - 2, x + 2, base - 1, "main.1")
    c.rect(x - 2, base - h - 2, 5, 3, head)
    if on:
        c.hline(x - 1, x + 1, base - h + 1, "warm.3")
        c.glow(x, base - h + 6, 18, steps=2)


def desk_lamp(c: Canvas, x, base, on=True, ramp=("main.1", "main.2", "main.3")):
    c.rect(x - 4, base - 2, 9, 2, ramp[1])
    c.line(x, base - 2, x - 3, base - 12, ramp[0])
    c.line(x - 3, base - 12, x + 5, base - 18, ramp[0])
    c.poly([(x + 3, base - 21), (x + 10, base - 17), (x + 6, base - 13)], ramp[2])
    if on:
        c.pset(x + 7, base - 15, "warm.3")
        beam = c.m_poly([(x + 6, base - 15), (x + 18, base - 1), (x - 2, base - 1)])
        c.lighten(beam, 1, level=9)


def laptop(c: Canvas, x, base, w=22, screen="cool.2", glow=True, t=0.0):
    """Laptop seen from the side-front, screen facing left."""
    c.rect(x, base - 2, w, 2, "main.2")
    c.hline(x, x + w - 1, base - 2, "main.4")
    c.poly([(x + w - 2, base - 2), (x + w + 1, base - 2), (x + w - 3, base - w + 2), (x + w - 6, base - w + 2)],
           "main.1")
    c.poly([(x + w - 3, base - 3), (x + w - 1, base - 3), (x + w - 4, base - w + 3), (x + w - 5, base - w + 3)],
           screen)
    if glow:
        c.glow(x + w - 6, base - w // 2, 16, steps=1)


def crate(c: Canvas, x, base, s=12, ramp=("alt.0", "alt.1", "alt.2", "alt.3")):
    c.rect(x, base - s, s, s, ramp[2])
    c.frame(x, base - s, s, s, ramp[0])
    c.line(x + 1, base - s + 1, x + s - 2, base - 2, ramp[1])
    c.hline(x + 1, x + s - 2, base - s + 1, ramp[3])


def screen_panel(c: Canvas, x, y, w, h, t=0.0, color="cool.2", seed=2):
    """Monitor with scrolling code lines."""
    c.rect(x, y, w, h, "main.0")
    c.frame(x, y, w, h, "main.2")
    c.rect(x + 2, y + 2, w - 4, h - 4, "cool.0")
    rng = np.random.default_rng(seed)
    lens = rng.integers(3, w - 8, 60)
    ind = rng.integers(0, 3, 60) * 2
    off = int(t * 4)
    for i in range((h - 6) // 2):
        k = (i + off) % 60
        c.hline(x + 4 + ind[k], x + 4 + ind[k] + lens[k] - ind[k], y + 4 + i * 2,
                color if k % 5 else "acc.2")


# ------------------------------------------------------------------ characters

def robot(c: Canvas, x, base, s=22, t=0.0, blink=False, look=0, eye="acc.2", body=("main.0", "main.1", "main.2",
          "main.3", "main.4", "main.5"), visor="ui.0", antenna="warm.2", talk=False):
    """A friendly robot drawn at any size. s = head width in px.
    look = -1/0/1 shifts the eyes left/right. talk opens a mouth bar."""
    x = round(x)
    hw, hh = s, int(s * 0.78)
    bw, bh = int(s * 0.82), int(s * 0.55)
    # body
    by = base - bh
    shapes.cylinder(c, x - bw // 2, by, bw, bh, list(body), light=0.3)
    c.frame(x - bw // 2, by, bw, bh, body[0])
    c.rect(x - bw // 4, by + 3, bw // 2, max(3, bh // 3), body[1])
    c.pset(x - bw // 4 + 1, by + 4, "warm.2" if int(t * 2) % 2 else "acc.2")
    # neck
    c.rect(x - s // 6, by - 3, s // 3, 3, body[1])
    # head
    hy = by - 3 - hh
    corners = ((x - hw // 2, hy), (x + hw // 2 - 1, hy), (x - hw // 2, hy + hh - 1), (x + hw // 2 - 1, hy + hh - 1))
    keep = [c.get(px, py) for px, py in corners]
    shapes.cylinder(c, x - hw // 2, hy, hw, hh, list(body), light=0.3)
    c.frame(x - hw // 2, hy, hw, hh, body[0])
    for (px, py), v in zip(corners, keep):
        c.pset(px, py, v)
    # visor
    vx, vy, vw, vh = x - hw // 2 + 3, hy + 3, hw - 6, int(hh * 0.5)
    c.rect(vx, vy, vw, vh, visor)
    c.hline(vx, vx + vw - 1, vy, body[0])
    ex = int(look * max(1, vw // 8))
    eh = 1 if blink else max(2, vh - 4)
    ew = max(2, vw // 6)
    for side in (-1, 1):
        exx = x + side * (vw // 4) - ew // 2 + ex
        eyy = vy + (vh - eh) // 2 + (1 if blink else 0)
        c.rect(exx, eyy, ew, eh, eye)
        if not blink and ew >= 2 and eh >= 3:
            c.pset(exx, eyy, "ui.3")
    if talk:
        c.rect(x - 2, vy + vh + 2, 4, 1, eye)
    # ears
    c.rect(x - hw // 2 - 2, hy + hh // 3, 2, hh // 3, body[1])
    c.rect(x + hw // 2, hy + hh // 3, 2, hh // 3, body[2])
    # antenna
    c.vline(x, hy - 4, hy - 1, body[2])
    c.pset(x, hy - 5, antenna if int(t * 1.5) % 2 else "warm.3")
    return hy - 5

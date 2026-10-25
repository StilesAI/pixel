"""Pixel UI: readouts, panels, tags, bars, guides. The overlay layer that turns
an animation into an explainer ("ALTITUDE 0412 M", a lean angle, a progress
bar) without leaving the pixel grid."""
from __future__ import annotations

import math

from .canvas import Canvas
from .anim import prog


def panel(c: Canvas, x, y, w, h, fill="ui.0", line="ui.1", notch=True):
    """Flat panel with a 1px border. notch=True clips the corners by one
    pixel, which reads as crisp pixel UI instead of a plain box."""
    corners = ((x, y), (x + w - 1, y), (x, y + h - 1), (x + w - 1, y + h - 1))
    keep = [c.get(px, py) for px, py in corners]
    c.rect(x, y, w, h, fill)
    c.frame(x, y, w, h, line)
    if notch:
        for (px, py), v in zip(corners, keep):
            c.pset(px, py, v)
    return c


def readout(c: Canvas, x, y, label, value, unit="", w=None, fill="ui.0", line="ui.2",
            label_color="ui.2", value_color="ui.3", scale=2, show=1.0):
    """Instrument box: tiny label on top, big value under it.
    show 0..1 wipes the box open from the left (use prog() for the intro)."""
    vw = Canvas.measure(value + unit, "body", scale, 1)
    lw = Canvas.measure(label, "tiny")
    bw = w or max(vw, lw) + 8
    bh = 6 + 5 + 3 + 7 * scale + 3
    if show <= 0:
        return bw, bh
    cw = max(2, int(round(bw * min(1.0, show))))
    layer = Canvas(c.w, c.h)
    panel(layer, x, y, bw, bh, fill, line, notch=True)
    layer.text(label, x + 4, y + 4, label_color, font="tiny")
    layer.text(value + unit, x + 4, y + 4 + 5 + 3, value_color, font="body", scale=scale)
    clip = c.m_rect(x, y, cw, bh)
    c.blit(layer, 0, 0, mask=clip)
    return bw, bh


def tag(c: Canvas, x, y, text, fill="acc.1", color="ui.3", font="tiny", pad=(3, 2), align="left"):
    """Small solid label, like a sticker on the scene."""
    tw = Canvas.measure(text, font)
    th = 5 if font == "tiny" else 7
    w, h = tw + pad[0] * 2, th + pad[1] * 2
    if align == "center":
        x -= w // 2
    elif align == "right":
        x -= w
    corners = ((x, y), (x + w - 1, y), (x, y + h - 1), (x + w - 1, y + h - 1))
    keep = [c.get(px, py) for px, py in corners]
    c.rect(x, y, w, h, fill)
    for (px, py), v in zip(corners, keep):
        c.pset(px, py, v)
    c.text(text, x + pad[0], y + pad[1], color, font=font)
    return w, h


def bar(c: Canvas, x, y, w, h, frac, fill="acc.1", back="ui.1", ticks=0):
    c.rect(x, y, w, h, back)
    fw = int(round((w) * max(0.0, min(1.0, frac))))
    if fw > 0:
        c.rect(x, y, fw, h, fill)
    for i in range(1, ticks):
        tx = x + round(w * i / ticks)
        c.vline(tx, y, y + h - 1, "ui.0")


def guide_v(c: Canvas, x, y0, y1, color="ui.2", dash=(2, 2)):
    c.line(x, y0, x, y1, color, dash=dash)


def guide_h(c: Canvas, x0, x1, y, color="ui.2", dash=(2, 2)):
    c.line(x0, y, x1, y, color, dash=dash)


def bracket(c: Canvas, x, y0, y1, color="ui.2", side="right", tick=3):
    """Dimension bracket |-- --| for measuring heights."""
    c.vline(x, y0, y1, color)
    d = tick if side == "right" else -tick
    c.hline(x, x - d, y0, color)
    c.hline(x, x - d, y1, color)


def arc(c: Canvas, cx, cy, r, a0, a1, color="acc.2", step=None):
    """Arc of pixels from angle a0 to a1 (degrees, 0 = right, -90 = up)."""
    if step is None:
        step = max(1.0, 60.0 / max(1, r))
    a = a0
    n = 0
    sgn = 1 if a1 >= a0 else -1
    while (a - a1) * sgn <= 0:
        c.pset(cx + r * math.cos(math.radians(a)), cy + r * math.sin(math.radians(a)), color)
        a += step * sgn
        n += 1
        if n > 4000:
            break


def arrow(c: Canvas, x0, y0, x1, y1, color="ui.3", head=3):
    c.line(x0, y0, x1, y1, color)
    ang = math.atan2(y1 - y0, x1 - x0)
    for s in (-1, 1):
        a = ang + math.pi + s * 0.6
        c.line(x1, y1, x1 + head * math.cos(a), y1 + head * math.sin(a), color)


def scan_reveal(c: Canvas, src: Canvas, t, t0, t1, x=0, y=0, line="acc.2"):
    """Reveal src top-to-bottom with a bright scanline at the edge."""
    u = prog(t, t0, t1)
    if u <= 0:
        return
    rows = int(round(src.h * u))
    m = c.m_rect(x, y, src.w, rows)
    c.blit(src, x, y, mask=m)
    if u < 1:
        c.hline(x, x + src.w - 1, y + rows, line)


def sparkline(c: Canvas, x, y, w, h, values, color="acc.2", upto=1.0, fill=None):
    """Tiny line chart. upto 0..1 draws it progressively."""
    if len(values) < 2:
        return
    lo, hi = min(values), max(values)
    pts = []
    n = len(values)
    last = max(1, int(round((n - 1) * upto)))
    for i in range(last + 1):
        px = x + (w - 1) * i / (n - 1)
        py = y + (h - 1) - (h - 1) * (values[i] - lo) / max(1e-9, hi - lo)
        pts.append((px, py))
    for (a, b), (cc, d) in zip(pts, pts[1:]):
        if fill is not None:
            c.poly([(a, b), (cc, d), (cc, y + h - 1), (a, y + h - 1)], fill)
        c.line(a, b, cc, d, color)


def caption(c: Canvas, text, y, color="ui.3", fill="ui.0", font="body", scale=1, show=1.0):
    """Centered caption chip (subtitle style) inside the pixel frame."""
    if show <= 0:
        return
    tw = Canvas.measure(text, font, scale)
    w = tw + 8
    h = (7 if font == "body" else 5) * scale + 6
    x = (c.w - w) // 2
    panel(c, x, y, w, h, fill, fill)
    c.text(text, x + 4, y + 3, color, font=font, scale=scale)


def scan_reveal_up(c: Canvas, layer: Canvas, t, t0, t1, line="ui.3"):
    """Reveal a full-canvas layer from the bottom of its content upward,
    with a bright build line at the edge (construction / draw-on effect)."""
    u = prog(t, t0, t1)
    if u <= 0:
        return
    import numpy as np
    m = layer.buf != 255
    rows = np.where(m.any(axis=1))[0]
    if len(rows) == 0:
        return
    top, bot = rows.min(), rows.max()
    edge = int(round(bot + 1 - (bot - top + 1) * u))
    clip = c.m_rect(0, edge, c.w, c.h - edge)
    c.blit(layer, 0, 0, mask=clip)
    if u < 1:
        row = np.zeros_like(m)
        row[edge, :] = m[edge, :] if edge < c.h else False
        c.paint(row, line)

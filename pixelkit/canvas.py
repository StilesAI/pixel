"""The pixel canvas.

A Canvas is a small grid of palette slots (uint8). Everything is drawn with
whole pixels and named colors, so it reads as real pixel art and can be
recolored by swapping the palette. 255 means transparent.
"""
from __future__ import annotations

import math
from functools import lru_cache

import numpy as np
from PIL import Image, ImageDraw

from . import font as _font
from .palette import LUT_DARK, LUT_LIGHT, LUT_TINT, TRANSPARENT, ref

BAYER4 = np.array([[0, 8, 2, 10],
                   [12, 4, 14, 6],
                   [3, 11, 1, 9],
                   [15, 7, 13, 5]], np.uint8)


@lru_cache(maxsize=16)
def _grid(h, w):
    yy, xx = np.mgrid[0:h, 0:w]
    return yy, xx, BAYER4[yy % 4, xx % 4]


class Dither:
    """Ordered-dither fill between two colors. level 0 = all a, 16 = all b."""

    def __init__(self, a, b, level):
        self.a, self.b = ref(a), ref(b)
        self.level = int(max(0, min(16, round(level))))


class Canvas:
    def __init__(self, w: int, h: int, fill=None):
        self.w, self.h = int(w), int(h)
        self.buf = np.full((self.h, self.w), ref(fill), np.uint8)

    # ------------------------------------------------------------ basics
    @property
    def shape(self):
        return self.h, self.w

    def copy(self) -> "Canvas":
        c = Canvas(self.w, self.h)
        c.buf = self.buf.copy()
        return c

    def clear(self, color=None):
        self.buf[:] = ref(color)
        return self

    def _g(self):
        return _grid(self.h, self.w)

    def _fill_values(self, color, mask):
        if isinstance(color, Dither):
            _, _, b = self._g()
            return np.where(b[mask] < color.level, color.b, color.a).astype(np.uint8)
        if callable(color):
            yy, xx, _ = self._g()
            return np.asarray(color(xx[mask], yy[mask]), np.uint8)
        return ref(color)

    def paint(self, mask, color):
        """Fill a bool mask with a color, Dither, or fn(x, y) -> slots."""
        if mask is None or not mask.any():
            return self
        self.buf[mask] = self._fill_values(color, mask)
        return self

    def pset(self, x, y, color):
        x, y = int(round(x)), int(round(y))
        if 0 <= x < self.w and 0 <= y < self.h:
            self.buf[y, x] = ref(color)
        return self

    def get(self, x, y):
        x, y = int(x), int(y)
        if 0 <= x < self.w and 0 <= y < self.h:
            return int(self.buf[y, x])
        return TRANSPARENT

    # ------------------------------------------------------------ masks
    def m_rect(self, x, y, w, h):
        m = np.zeros(self.shape, bool)
        x0, y0 = int(round(x)), int(round(y))
        x1, y1 = x0 + int(round(w)), y0 + int(round(h))
        m[max(0, y0):max(0, min(self.h, y1)), max(0, x0):max(0, min(self.w, x1))] = True
        return m

    def m_disc(self, cx, cy, r):
        yy, xx, _ = self._g()
        cx, cy = round(cx * 2) / 2, round(cy * 2) / 2
        return (xx - cx) ** 2 + (yy - cy) ** 2 <= r * r + r * 0.8

    def m_ellipse(self, cx, cy, rx, ry):
        yy, xx, _ = self._g()
        rx, ry = max(rx, 0.5), max(ry, 0.5)
        return ((xx - cx) / (rx + 0.4)) ** 2 + ((yy - cy) / (ry + 0.4)) ** 2 <= 1.0

    def m_poly(self, pts):
        img = Image.new("1", (self.w, self.h), 0)
        ImageDraw.Draw(img).polygon([(round(x), round(y)) for x, y in pts], fill=1, outline=1)
        return np.array(img, bool)

    def m_line(self, x0, y0, x1, y1, dash=None):
        m = np.zeros(self.shape, bool)
        for i, (x, y) in enumerate(_bresenham(x0, y0, x1, y1)):
            if dash and (i % sum(dash)) >= dash[0]:
                continue
            if 0 <= x < self.w and 0 <= y < self.h:
                m[y, x] = True
        return m

    def m_ring(self, cx, cy, r):
        d = self.m_disc(cx, cy, r)
        return d & ~_erode(d)

    def m_opaque(self):
        return self.buf != TRANSPARENT

    # ------------------------------------------------------------ shapes
    def rect(self, x, y, w, h, color):
        return self.paint(self.m_rect(x, y, w, h), color)

    def frame(self, x, y, w, h, color, t=1):
        outer = self.m_rect(x, y, w, h)
        inner = self.m_rect(x + t, y + t, w - 2 * t, h - 2 * t)
        return self.paint(outer & ~inner, color)

    def hline(self, x0, x1, y, color):
        return self.rect(min(x0, x1), y, abs(x1 - x0) + 1, 1, color)

    def vline(self, x, y0, y1, color):
        return self.rect(x, min(y0, y1), 1, abs(y1 - y0) + 1, color)

    def line(self, x0, y0, x1, y1, color, dash=None):
        return self.paint(self.m_line(x0, y0, x1, y1, dash), color)

    def disc(self, cx, cy, r, color):
        return self.paint(self.m_disc(cx, cy, r), color)

    def ring(self, cx, cy, r, color):
        return self.paint(self.m_ring(cx, cy, r), color)

    def ellipse(self, cx, cy, rx, ry, color):
        return self.paint(self.m_ellipse(cx, cy, rx, ry), color)

    def poly(self, pts, color):
        return self.paint(self.m_poly(pts), color)

    def outline_mask(self, mask, color, diagonal=False):
        """Draw a 1px outline just outside a mask."""
        grown = _dilate(mask, diagonal)
        return self.paint(grown & ~mask, color)

    # ------------------------------------------------------------ fills
    def gradient_v(self, x, y, w, h, colors, steps_per_band=16):
        """Vertical banded gradient across colors (top -> bottom) with
        ordered-dither transitions between bands."""
        cols = [ref(c) for c in colors]
        yy, xx, b = self._g()
        region = self.m_rect(x, y, w, h)
        if not region.any():
            return self
        n = len(cols) - 1
        u = np.clip((yy - y) / max(1, h - 1), 0, 1) * n
        k = np.minimum(np.floor(u).astype(int), n - 1) if n > 0 else np.zeros_like(yy)
        frac = u - k
        # hold flat for most of the band, dither only near the edge
        lvl = np.clip((frac - 0.55) / 0.45 * 16, 0, 16)
        arr = np.array(cols, np.uint8)
        lo = arr[np.clip(k, 0, n)]
        hi = arr[np.clip(k + 1, 0, n)]
        out = np.where(b < lvl, hi, lo).astype(np.uint8)
        self.buf[region] = out[region]
        return self

    def gradient_radial(self, cx, cy, r, colors, mask=None):
        """Radial gradient, colors from center outward, dithered edges."""
        cols = np.array([ref(c) for c in colors], np.uint8)
        yy, xx, b = self._g()
        d = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2) / max(1e-6, r) * (len(cols) - 1)
        region = d <= len(cols) - 1
        if mask is not None:
            region &= mask
        k = np.clip(np.floor(d).astype(int), 0, len(cols) - 2)
        frac = d - k
        lvl = np.clip((frac - 0.5) / 0.5 * 16, 0, 16)
        out = np.where(b < lvl, cols[np.minimum(k + 1, len(cols) - 1)], cols[k])
        self.buf[region] = out[region]
        return self

    # ------------------------------------------------------------ light
    def darken(self, mask=None, steps=1, level=16):
        """Shade pixels darker inside their own ramp. level < 16 dithers."""
        return self._relight(mask, steps, level, LUT_DARK)

    def lighten(self, mask=None, steps=1, level=16):
        return self._relight(mask, steps, level, LUT_LIGHT)

    def _relight(self, mask, steps, level, lut):
        if mask is None:
            mask = np.ones(self.shape, bool)
        _, _, b = self._g()
        sel = mask & (b < level)
        v = self.buf[sel]
        for _ in range(int(steps)):
            v = lut[v]
        self.buf[sel] = v
        return self

    def tint(self, mask=None, to="warm", level=16):
        """Recolor pixels into another ramp at the same brightness, e.g. steam
        lit orange by a flame, a blue screen cast on a face. level < 16 dithers."""
        if mask is None:
            mask = np.ones(self.shape, bool)
        _, _, b = self._g()
        sel = mask & (b < level) & (self.buf != TRANSPARENT)
        self.buf[sel] = LUT_TINT[to][self.buf[sel]]
        return self

    def tint_radial(self, cx, cy, r, to="warm", mask=None, inner=0.45):
        """Tint that is solid near the center and dithers out by radius r."""
        yy, xx, b = self._g()
        d = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2) / max(1e-6, r)
        lvl = np.clip((1 - d) / max(1e-6, 1 - inner) * 16, 0, 16)
        sel = (b < lvl) & (self.buf != TRANSPARENT)
        if mask is not None:
            sel &= mask
        self.buf[sel] = LUT_TINT[to][self.buf[sel]]
        return self

    def glow(self, cx, cy, r, steps=2, mask=None):
        """Soft light pool: lightens in dithered rings, strongest at center."""
        yy, xx, b = self._g()
        d = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2) / max(1e-6, r)
        for s in range(int(steps)):
            # ring s covers d < (1 - s/steps), dithered falloff near its edge
            edge = 1 - s / steps
            lvl = np.clip((edge - d) / 0.25 * 16, 0, 16)
            sel = (b < lvl)
            if mask is not None:
                sel &= mask
            self.buf[sel] = LUT_LIGHT[self.buf[sel]]
        return self

    def shadow(self, cx, cy, rx, ry, steps=1):
        """Contact shadow ellipse on whatever is underneath."""
        m = self.m_ellipse(cx, cy, rx, ry)
        self.darken(m, steps)
        edge = self.m_ellipse(cx, cy, rx + 2, ry + 1) & ~m
        return self.darken(edge, 1, level=7)

    # ------------------------------------------------------------ compositing
    def blit(self, src, x, y, anchor="topleft", flip=False, mask=None):
        """Paste another Canvas/Sprite (transparent pixels skipped)."""
        a = src.buf[:, ::-1] if flip else src.buf
        h, w = a.shape
        x, y = int(round(x)), int(round(y))
        if anchor == "center":
            x -= w // 2
            y -= h // 2
        elif anchor == "bottom":
            x -= w // 2
            y -= h
        elif anchor == "bottomleft":
            y -= h
        x0, y0 = max(0, x), max(0, y)
        x1, y1 = min(self.w, x + w), min(self.h, y + h)
        if x0 >= x1 or y0 >= y1:
            return self
        sub = a[y0 - y:y1 - y, x0 - x:x1 - x]
        m = sub != TRANSPARENT
        if mask is not None:
            m &= mask[y0:y1, x0:x1]
        dst = self.buf[y0:y1, x0:x1]
        dst[m] = sub[m]
        return self

    def blit_rotated(self, src, angle_deg, pivot, at, smooth=True):
        """Rotate src around pivot (src coords) and place the pivot at `at`.
        smooth=True uses a RotSprite-style upscale so edges stay clean."""
        a = src.buf
        k = 8 if smooth else 1
        big = a
        if smooth:
            for _ in range(3):
                big = scale2x(big)
        th = math.radians(angle_deg)
        c, s = math.cos(th), math.sin(th)
        h, w = a.shape
        px, py = pivot
        ax, ay = at
        corners = [(-px, -py), (w - px, -py), (-px, h - py), (w - px, h - py)]
        xs = [ax + cx * c - cy * s for cx, cy in corners]
        ys = [ay + cx * s + cy * c for cx, cy in corners]
        x0, x1 = int(math.floor(min(xs))) - 1, int(math.ceil(max(xs))) + 1
        y0, y1 = int(math.floor(min(ys))) - 1, int(math.ceil(max(ys))) + 1
        x0, y0 = max(0, x0), max(0, y0)
        x1, y1 = min(self.w, x1), min(self.h, y1)
        if x0 >= x1 or y0 >= y1:
            return self
        yy, xx = np.mgrid[y0:y1, x0:x1]
        dx, dy = xx + 0.5 - ax, yy + 0.5 - ay
        sx = (dx * c + dy * s + px) * k
        sy = (-dx * s + dy * c + py) * k
        ix, iy = np.floor(sx).astype(int), np.floor(sy).astype(int)
        inside = (ix >= 0) & (iy >= 0) & (ix < w * k) & (iy < h * k)
        vals = np.full(ix.shape, TRANSPARENT, np.uint8)
        vals[inside] = big[iy[inside], ix[inside]]
        m = vals != TRANSPARENT
        dst = self.buf[y0:y1, x0:x1]
        dst[m] = vals[m]
        return self

    # ------------------------------------------------------------ text
    def text(self, s, x, y, color="ui.3", font="body", scale=1, align="left",
             spacing=1, shadow=None, outline=None, line_gap=0):
        """Draw text. Returns the width of the widest line."""
        f = _font.get(font)
        lines = str(s).split("\n")
        widest = 0
        for i, line in enumerate(lines):
            m = f.mask(line, scale, spacing)
            h, w = m.shape
            widest = max(widest, w)
            lx = int(round(x))
            if align == "center":
                lx -= w // 2
            elif align == "right":
                lx -= w
            ly = int(round(y)) + i * (f.line_height + line_gap) * scale
            full = np.zeros(self.shape, bool)
            _place(full, m, lx, ly)
            if outline is not None:
                self.outline_mask(full, outline, diagonal=True)
            if shadow is not None:
                sh = np.zeros(self.shape, bool)
                _place(sh, m, lx + max(1, scale // 2), ly + max(1, scale // 2))
                self.paint(sh & ~full, shadow)
            self.paint(full, color)
        return widest

    @staticmethod
    def measure(s, font="body", scale=1, spacing=1):
        return _font.get(font).measure(str(s), scale, spacing)

    # ------------------------------------------------------------ transforms
    def shift(self, dx, dy):
        """Move the whole picture (camera shake). Edges repeat, no wrap."""
        dx, dy = int(dx), int(dy)
        if not dx and not dy:
            return self
        p = max(abs(dx), abs(dy))
        a = np.pad(self.buf, p, mode="edge")
        self.buf = a[p - dy:p - dy + self.h, p - dx:p - dx + self.w].copy()
        return self

    def flip_x(self):
        c = self.copy()
        c.buf = c.buf[:, ::-1].copy()
        return c

    def scaled(self, n: int):
        c = Canvas(self.w * n, self.h * n)
        c.buf = np.kron(self.buf, np.ones((n, n), np.uint8))
        return c

    def recolor(self, mapping: dict):
        c = self.copy()
        for a, b in mapping.items():
            c.buf[self.buf == ref(a)] = ref(b)
        return c

    def trimmed(self):
        m = self.buf != TRANSPARENT
        if not m.any():
            return self.copy()
        ys, xs = np.where(m)
        c = Canvas(xs.max() - xs.min() + 1, ys.max() - ys.min() + 1)
        c.buf = self.buf[ys.min():ys.max() + 1, xs.min():xs.max() + 1].copy()
        return c

    def with_outline(self, color, diagonal=False):
        """Copy padded by 1px with an outline around opaque pixels."""
        c = Canvas(self.w + 2, self.h + 2)
        c.buf[1:-1, 1:-1] = self.buf
        m = c.buf != TRANSPARENT
        c.outline_mask(m, color, diagonal)
        return c

    # ------------------------------------------------------------ output
    def to_rgb(self, palette) -> np.ndarray:
        return palette.rgb[self.buf]

    def to_image(self, palette, scale=1) -> Image.Image:
        img = Image.fromarray(self.to_rgb(palette))
        if scale != 1:
            img = img.resize((self.w * scale, self.h * scale), Image.NEAREST)
        return img


# -------------------------------------------------------------------- helpers

def _place(dst, m, x, y):
    h, w = m.shape
    H, W = dst.shape
    x0, y0 = max(0, x), max(0, y)
    x1, y1 = min(W, x + w), min(H, y + h)
    if x0 < x1 and y0 < y1:
        dst[y0:y1, x0:x1] |= m[y0 - y:y1 - y, x0 - x:x1 - x]


def _dilate(m, diagonal=False):
    g = m.copy()
    g[1:, :] |= m[:-1, :]
    g[:-1, :] |= m[1:, :]
    g[:, 1:] |= m[:, :-1]
    g[:, :-1] |= m[:, 1:]
    if diagonal:
        g[1:, 1:] |= m[:-1, :-1]
        g[1:, :-1] |= m[:-1, 1:]
        g[:-1, 1:] |= m[1:, :-1]
        g[:-1, :-1] |= m[1:, 1:]
    return g


def _erode(m):
    return ~_dilate(~m)


def _bresenham(x0, y0, x1, y1):
    x0, y0, x1, y1 = int(round(x0)), int(round(y0)), int(round(x1)), int(round(y1))
    dx, dy = abs(x1 - x0), -abs(y1 - y0)
    sx, sy = (1 if x0 < x1 else -1), (1 if y0 < y1 else -1)
    err = dx + dy
    while True:
        yield x0, y0
        if x0 == x1 and y0 == y1:
            return
        e2 = 2 * err
        if e2 >= dy:
            err += dy
            x0 += sx
        if e2 <= dx:
            err += dx
            y0 += sy


def scale2x(a: np.ndarray) -> np.ndarray:
    """EPX / Scale2x on a slot grid (used for clean rotation)."""
    p = np.pad(a, 1, mode="constant", constant_values=TRANSPARENT)
    B, D, F, H = p[:-2, 1:-1], p[1:-1, :-2], p[1:-1, 2:], p[2:, 1:-1]
    E = a
    e0 = np.where((D == B) & (B != F) & (D != H), D, E)
    e1 = np.where((B == F) & (B != D) & (F != H), F, E)
    e2 = np.where((D == H) & (D != B) & (H != F), D, E)
    e3 = np.where((H == F) & (H != D) & (B != F), F, E)
    h, w = a.shape
    out = np.empty((h * 2, w * 2), a.dtype)
    out[0::2, 0::2] = e0
    out[0::2, 1::2] = e1
    out[1::2, 0::2] = e2
    out[1::2, 1::2] = e3
    return out

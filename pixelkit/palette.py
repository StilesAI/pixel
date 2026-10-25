"""Palettes.

Every palette fills the same set of named ramps, so any scene can be
re-rendered in any palette (multicolour preset, one hue, black and white,
or your own colors) without touching the scene code.

Ramps are ordered dark -> light. A color reference is "ramp.level",
for example "main.3", "acc.0" or "ui.-1" (negative counts from the light
end). A bare ramp name ("leaf") means its middle level.
"""
from __future__ import annotations

import colorsys
import json
import math
from pathlib import Path

import numpy as np

# name, number of levels (dark -> light)
SCHEMA = [
    ("bg", 5),    # sky / backdrop
    ("main", 6),  # the hero subject's material
    ("alt", 5),   # secondary material (wood, rust, brick, ground)
    ("acc", 4),   # accent: highlights, UI emphasis, glow
    ("warm", 4),  # fire, lamps, reds
    ("cool", 4),  # water, screens, teal
    ("leaf", 4),  # foliage, greens
    ("skin", 3),
    ("ui", 4),    # panel fill, panel line, dim text, text
]

TRANSPARENT = 255

INDEX: dict[str, list[int]] = {}
_i = 0
for _name, _n in SCHEMA:
    INDEX[_name] = list(range(_i, _i + _n))
    _i += _n
NUM_SLOTS = _i  # 39

SLOT_NAMES = [f"{n}.{k}" for n, c in SCHEMA for k in range(c)]

# step-darker / step-lighter lookup tables (stay inside the ramp)
LUT_DARK = np.arange(256, dtype=np.uint8)
LUT_LIGHT = np.arange(256, dtype=np.uint8)
for _name, _idx in INDEX.items():
    for _k, _s in enumerate(_idx):
        LUT_DARK[_s] = _idx[max(0, _k - 1)]
        LUT_LIGHT[_s] = _idx[min(len(_idx) - 1, _k + 1)]

# tint tables: move a pixel to another ramp at the same relative brightness
LUT_TINT: dict[str, np.ndarray] = {}
for _to, _tidx in INDEX.items():
    _lut = np.arange(256, dtype=np.uint8)
    for _name, _idx in INDEX.items():
        for _k, _s in enumerate(_idx):
            _rel = _k / max(1, len(_idx) - 1)
            _lut[_s] = _tidx[int(round(_rel * (len(_tidx) - 1)))]
    LUT_TINT[_to] = _lut


def ref(c) -> int:
    """Resolve a color reference to a slot index."""
    if c is None:
        return TRANSPARENT
    if isinstance(c, (int, np.integer)):
        return int(c)
    if isinstance(c, str):
        if c in ("clear", "none", "transparent"):
            return TRANSPARENT
        if "." in c:
            name, lvl = c.split(".", 1)
            idx = INDEX[name]
            k = int(lvl)
            if k < 0:
                k = len(idx) + k
            return idx[max(0, min(len(idx) - 1, k))]
        idx = INDEX[c]
        return idx[len(idx) // 2]
    raise ValueError(f"bad color reference: {c!r}")


def ramp(name: str) -> list[int]:
    return list(INDEX[name])


# ---------------------------------------------------------------- color math

def hex_to_rgb(h: str) -> tuple[int, int, int]:
    h = h.strip().lstrip("#")
    if len(h) == 3:
        h = "".join(ch * 2 for ch in h)
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def rgb_to_hex(rgb) -> str:
    return "#" + "".join(f"{int(v):02x}" for v in rgb)


def _srgb_to_lin(c):
    c = c / 255.0
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def _lin_to_srgb(c):
    c = np.clip(c, 0, 1)
    return np.where(c <= 0.0031308, c * 12.92, 1.055 * c ** (1 / 2.4) - 0.055) * 255


def rgb_to_oklab(rgb):
    r, g, b = _srgb_to_lin(np.asarray(rgb, float))
    l = 0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b
    m = 0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b
    s = 0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b
    l, m, s = np.cbrt(l), np.cbrt(m), np.cbrt(s)
    return (0.2104542553 * l + 0.7936177850 * m - 0.0040720468 * s,
            1.9779984951 * l - 2.4285922050 * m + 0.4505937099 * s,
            0.0259040371 * l + 0.7827717662 * m - 0.8086757660 * s)


def oklab_to_rgb(L, a, b):
    l = (L + 0.3963377774 * a + 0.2158037573 * b) ** 3
    m = (L - 0.1055613458 * a - 0.0638541728 * b) ** 3
    s = (L - 0.0894841775 * a - 1.2914855480 * b) ** 3
    r = 4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s
    g = -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s
    bb = -0.0041960863 * l - 0.7034186147 * m + 1.7076147010 * s
    return tuple(int(round(float(v))) for v in _lin_to_srgb(np.array([r, g, bb])))


def lightness(rgb) -> float:
    return float(rgb_to_oklab(rgb)[0])


def oklch_to_rgb(L, C, h_deg):
    # pull chroma down until the color fits in sRGB
    for _ in range(40):
        a = C * math.cos(math.radians(h_deg))
        b = C * math.sin(math.radians(h_deg))
        l = (L + 0.3963377774 * a + 0.2158037573 * b) ** 3
        m = (L - 0.1055613458 * a - 0.0638541728 * b) ** 3
        s = (L - 0.0894841775 * a - 1.2914855480 * b) ** 3
        r = 4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s
        g = -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s
        bb = -0.0041960863 * l - 0.7034186147 * m + 1.7076147010 * s
        if min(r, g, bb) >= -1e-4 and max(r, g, bb) <= 1 + 1e-4:
            break
        C *= 0.92
    return oklab_to_rgb(L, C * math.cos(math.radians(h_deg)), C * math.sin(math.radians(h_deg)))


def _shift_hue(h, target, amount):
    d = ((target - h + 180) % 360) - 180
    step = max(-abs(amount), min(abs(amount), d))
    return (h + step) % 360


def hue_ramp(base_hex: str, steps: int = 8, chroma: float | None = None) -> list[tuple[int, int, int]]:
    """A hand-tuned single-hue ramp: shadows lean cool, highlights lean warm,
    saturation peaks in the mids like a pixel artist would do it."""
    L0, a0, b0 = rgb_to_oklab(hex_to_rgb(base_hex))
    h = math.degrees(math.atan2(b0, a0)) % 360
    c0 = math.hypot(a0, b0) if chroma is None else chroma
    out = []
    for i in range(steps):
        u = i / (steps - 1)
        L = 0.14 + 0.83 * u
        C = c0 * (0.55 + 0.75 * math.sin(math.pi * min(1.0, u * 1.05))) * (1 - 0.55 * u ** 3)
        hh = _shift_hue(h, 285, 18 * (1 - u) ** 1.5) if u < 0.5 else _shift_hue(h, 95, 16 * (u - 0.5) * 2)
        out.append(oklch_to_rgb(L, C, hh))
    return out


def gray_ramp(steps: int = 7) -> list[tuple[int, int, int]]:
    out = []
    for i in range(steps):
        u = i / (steps - 1)
        L = 0.10 + 0.88 * u
        out.append(oklab_to_rgb(L, 0.0, 0.0))
    return out


# ------------------------------------------------------------------ palette

class Palette:
    def __init__(self, name: str, ramps: dict[str, list]):
        self.name = name
        self.ramps = {}
        for rname, n in SCHEMA:
            cols = ramps.get(rname)
            if cols is None or len(cols) != n:
                raise ValueError(f"palette {name}: ramp '{rname}' needs {n} colors")
            self.ramps[rname] = [hex_to_rgb(c) if isinstance(c, str) else tuple(c) for c in cols]
        self.rgb = np.zeros((256, 3), np.uint8)
        for rname, cols in self.ramps.items():
            for k, c in enumerate(cols):
                self.rgb[INDEX[rname][k]] = c
        # transparent shows as the darkest backdrop color
        self.rgb[TRANSPARENT] = self.rgb[INDEX["bg"][0]]

    # ---- loading
    @classmethod
    def load(cls, spec) -> "Palette":
        """spec: Palette, preset name, path to .json, or None (default)."""
        if isinstance(spec, Palette):
            return spec
        if spec is None:
            spec = "night"
        p = Path(str(spec))
        if p.suffix == ".json" and p.exists():
            data = json.loads(p.read_text())
        else:
            f = PRESET_DIR / f"{spec}.json"
            if not f.exists():
                raise FileNotFoundError(f"no palette '{spec}'. Presets: {', '.join(presets())}")
            data = json.loads(f.read_text())
        if "colors" in data and "ramps" not in data:
            return cls.from_colors(data["colors"], data.get("name", p.stem))
        return cls(data.get("name", p.stem), data["ramps"])

    def to_json(self) -> str:
        return json.dumps({"name": self.name,
                           "ramps": {k: [rgb_to_hex(c) for c in v] for k, v in self.ramps.items()}},
                          indent=2)

    # ---- color modes
    def _remap(self, target: list[tuple[int, int, int]], name: str) -> "Palette":
        """Map every slot onto a single ramp by lightness, keeping each ramp's
        levels distinct and in order so shading still reads."""
        tl = [lightness(c) for c in target]
        n = len(target)
        all_l = [lightness(c) for r in self.ramps.values() for c in r]
        lo, hi = min(all_l), max(all_l)
        new = {}
        for rname, cols in self.ramps.items():
            ls = [lightness(c) for c in cols]
            raw = []
            for L in ls:
                u = (L - lo) / max(1e-6, hi - lo)
                want = tl[0] + u * (tl[-1] - tl[0])
                raw.append(int(np.argmin([abs(want - x) for x in tl])))
            # keep levels distinct, in the ramp's own dark->light order
            order = sorted(range(len(cols)), key=lambda i: ls[i])
            lv = [raw[i] for i in order]
            for i in range(1, len(lv)):
                if lv[i] <= lv[i - 1]:
                    lv[i] = lv[i - 1] + 1
            over = lv[-1] - (n - 1)
            if over > 0:
                lv = [max(0, x - over) for x in lv]
                for i in range(1, len(lv)):
                    if lv[i] <= lv[i - 1]:
                        lv[i] = min(n - 1, lv[i - 1] + 1)
            out = [0] * len(cols)
            for pos, i in enumerate(order):
                out[i] = lv[pos]
            new[rname] = [target[x] for x in out]
        return Palette(name, new)

    def one_hue(self, base_hex: str, steps: int = 9) -> "Palette":
        return self._remap(hue_ramp(base_hex, steps), f"{self.name}-hue-{base_hex.lstrip('#')}")

    def mono(self, steps: int = 7) -> "Palette":
        return self._remap(gray_ramp(steps), f"{self.name}-mono")

    @classmethod
    def from_colors(cls, colors: list[str], name: str = "custom", base: str = "night") -> "Palette":
        """Your own colors. Neutrals (grays, near-blacks, off-whites) carry the
        backdrop, materials, and UI; colorful entries become the accent and any
        ramp whose hue they match. Shades in between are filled in so shading
        still works, without adding hues you did not pick."""
        rgbs = [hex_to_rgb(c) for c in colors]
        labs = [rgb_to_oklab(c) for c in rgbs]
        chroma = [math.hypot(a, b) for _, a, b in labs]
        if len(rgbs) >= 10:
            return cls._quantize_to(rgbs, name, base)
        neutrals = [c for c, ch in zip(rgbs, chroma) if ch < 0.06]
        accents = [c for c, ch in zip(rgbs, chroma) if ch >= 0.06]
        if len(neutrals) < 2:
            neutrals = sorted(rgbs, key=lightness)
        if not accents:
            accents = [max(rgbs, key=lambda c: math.hypot(*rgb_to_oklab(c)[1:]))]
        neutrals.sort(key=lightness)
        # neutral ramp: user's neutrals with in-between steps interpolated
        steps = []
        for a, b in zip(neutrals, neutrals[1:]):
            la, lb = np.array(rgb_to_oklab(a)), np.array(rgb_to_oklab(b))
            k = max(1, int(round((lb[0] - la[0]) / 0.09)))
            for i in range(k):
                v = la + (lb - la) * (i / k)
                steps.append(oklab_to_rgb(*v))
        steps.append(neutrals[-1])
        neutral_pal = Palette.load(base)._remap(steps, name)

        def hue(c):
            _, a, b = rgb_to_oklab(c)
            return math.degrees(math.atan2(b, a)) % 360

        def accent_ramp(acc, n, ref_cols):
            L0, a0, b0 = rgb_to_oklab(acc)
            h = math.degrees(math.atan2(b0, a0)) % 360
            C = math.hypot(a0, b0)
            Ls = [lightness(c) for c in ref_cols]
            # keep the user's color exactly at the level closest to its lightness
            k = int(np.argmin([abs(L0 - x) for x in Ls]))
            out = []
            for i, L in enumerate(Ls):
                if i == k:
                    out.append(acc)
                else:
                    out.append(oklch_to_rgb(L, C * (0.55 + 0.45 * (1 - abs(L - L0))), h))
            return out

        b = Palette.load(base)
        ramps = dict(neutral_pal.ramps)
        ramps["acc"] = accent_ramp(accents[0], 4, b.ramps["acc"])
        for rname in ("warm", "cool", "leaf", "skin"):
            mid = b.ramps[rname][len(b.ramps[rname]) // 2]
            hb = hue(mid)
            best = min(accents, key=lambda c: min(abs(hue(c) - hb), 360 - abs(hue(c) - hb)))
            d = min(abs(hue(best) - hb), 360 - abs(hue(best) - hb))
            if d < 70 or rname == "warm":
                ramps[rname] = accent_ramp(best, len(b.ramps[rname]), b.ramps[rname])
        return cls(name, ramps)

    @classmethod
    def _quantize_to(cls, rgbs, name, base):
        """Full palette (10+ colors, e.g. a Lospec palette): every slot takes
        the nearest of your colors, keeping each ramp's levels distinct."""
        b = Palette.load(base)
        labs = np.array([rgb_to_oklab(c) for c in rgbs])
        ramps = {}
        for rname, cols in b.ramps.items():
            used = []
            for c in cols:
                L, A, B = rgb_to_oklab(c)
                d = (labs[:, 0] - L) ** 2 * 1.4 + (labs[:, 1] - A) ** 2 + (labs[:, 2] - B) ** 2
                for k in np.argsort(d):
                    if int(k) not in used:
                        used.append(int(k))
                        break
            used.sort(key=lambda k: labs[k, 0])
            ramps[rname] = [rgbs[k] for k in used]
        return cls(name, ramps)

    def swatch(self, cell: int = 12):
        """PIL image of the palette, one row per ramp."""
        from PIL import Image
        rows = len(SCHEMA)
        w = max(n for _, n in SCHEMA)
        img = np.zeros((rows * cell, w * cell, 3), np.uint8)
        img[:] = self.rgb[INDEX["bg"][0]]
        for r, (name, n) in enumerate(SCHEMA):
            for k in range(n):
                img[r * cell:(r + 1) * cell, k * cell:(k + 1) * cell] = self.ramps[name][k]
        return Image.fromarray(img)


PRESET_DIR = Path(__file__).resolve().parent.parent / "palettes"


def presets() -> list[str]:
    return sorted(p.stem for p in PRESET_DIR.glob("*.json"))


def resolve_palette(spec=None, hue: str | None = None, mono: bool = False,
                    colors: list[str] | None = None) -> Palette:
    """One entry point for every color mode the kit offers."""
    if colors:
        return Palette.from_colors(colors, base=spec or "night")
    p = Palette.load(spec)
    if hue:
        return p.one_hue(hue)
    if mono:
        return p.mono()
    return p

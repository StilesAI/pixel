"""Timing: easing curves, tweens, keyframes, and helpers for pixel motion."""
from __future__ import annotations

import math


def clamp01(x):
    return 0.0 if x < 0 else 1.0 if x > 1 else x


def _out_bounce(t):
    n, d = 7.5625, 2.75
    if t < 1 / d:
        return n * t * t
    if t < 2 / d:
        t -= 1.5 / d
        return n * t * t + 0.75
    if t < 2.5 / d:
        t -= 2.25 / d
        return n * t * t + 0.9375
    t -= 2.625 / d
    return n * t * t + 0.984375


EASE = {
    "linear": lambda t: t,
    "inQuad": lambda t: t * t,
    "outQuad": lambda t: 1 - (1 - t) ** 2,
    "inOutQuad": lambda t: 2 * t * t if t < 0.5 else 1 - (-2 * t + 2) ** 2 / 2,
    "inCubic": lambda t: t ** 3,
    "outCubic": lambda t: 1 - (1 - t) ** 3,
    "inOutCubic": lambda t: 4 * t ** 3 if t < 0.5 else 1 - (-2 * t + 2) ** 3 / 2,
    "inQuart": lambda t: t ** 4,
    "outQuart": lambda t: 1 - (1 - t) ** 4,
    "inOutQuart": lambda t: 8 * t ** 4 if t < 0.5 else 1 - (-2 * t + 2) ** 4 / 2,
    "inExpo": lambda t: 0 if t == 0 else 2 ** (10 * t - 10),
    "outExpo": lambda t: 1 if t == 1 else 1 - 2 ** (-10 * t),
    "inOutSine": lambda t: -(math.cos(math.pi * t) - 1) / 2,
    "outSine": lambda t: math.sin(t * math.pi / 2),
    "inSine": lambda t: 1 - math.cos(t * math.pi / 2),
    "outBack": lambda t: 1 + 2.70158 * (t - 1) ** 3 + 1.70158 * (t - 1) ** 2,
    "inBack": lambda t: 2.70158 * t ** 3 - 1.70158 * t * t,
    "outElastic": lambda t: 0 if t == 0 else 1 if t == 1 else
    2 ** (-10 * t) * math.sin((t * 10 - 0.75) * (2 * math.pi / 3)) + 1,
    "outBounce": _out_bounce,
    "step": lambda t: 0.0 if t < 1 else 1.0,
}


def ease(t, kind="inOutCubic"):
    return EASE[kind](clamp01(t))


def prog(t, t0, t1):
    """0 before t0, 1 after t1, linear in between."""
    if t1 <= t0:
        return 1.0 if t >= t1 else 0.0
    return clamp01((t - t0) / (t1 - t0))


def tween(t, t0, t1, a, b, kind="inOutCubic"):
    u = ease(prog(t, t0, t1), kind)
    if isinstance(a, (tuple, list)):
        return tuple(x + (y - x) * u for x, y in zip(a, b))
    return a + (b - a) * u


class Keys:
    """Keyframes: Keys((0, 0), (1.5, 40, "outBack"), (3, 40), (4, 0, "inCubic"))
    The ease on a key shapes the segment that ends at that key."""

    def __init__(self, *keys):
        self.keys = [(k[0], k[1], k[2] if len(k) > 2 else "inOutCubic") for k in keys]

    def __call__(self, t):
        ks = self.keys
        if t <= ks[0][0]:
            return ks[0][1]
        for (t0, v0, _), (t1, v1, e) in zip(ks, ks[1:]):
            if t <= t1:
                return tween(t, t0, t1, v0, v1, e)
        return ks[-1][1]


def osc(t, period=1.0, amp=1.0, phase=0.0):
    return amp * math.sin(2 * math.pi * (t / period + phase))


def blink(t, period=1.0, duty=0.5, phase=0.0):
    return ((t / period + phase) % 1.0) < duty


def snap(t, fps):
    """Quantize time to a lower animation rate (12 = classic 'on twos' feel)."""
    return math.floor(t * fps + 1e-9) / fps


def count(t, t0, t1, a, b, kind="outCubic", decimals=0):
    """A number that counts from a to b, as a formatted string."""
    v = tween(t, t0, t1, a, b, kind)
    return f"{v:.{decimals}f}"


def typewriter(text, t, t0, cps=20):
    n = int(max(0, (t - t0) * cps))
    return text[:n]


def hold_frames(t, every):
    """Hold motion for `every` seconds at a time (choppy, deliberate)."""
    return math.floor(t / every) * every

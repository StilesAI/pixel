"""Pixel bar chart: bars grow in one by one, numbers count up, the biggest
bar gets called out, then a total lands. For any 'here are the numbers' beat.

Change DATA, TITLE, UNIT, and TOTAL_LABEL. Palette 'paper' gives a white
background; any other palette works too.
"""
from pixelkit import Scene, Keys, fx, ui
from pixelkit.anim import ease, prog, tween

TITLE = "TOKENS PER DAY"
UNIT = "M"
DATA = [("MON", 120), ("TUE", 180), ("WED", 150), ("THU", 260), ("FRI", 410), ("SAT", 330), ("SUN", 220)]
TOTAL_LABEL = "THIS WEEK"


class Chart(Scene):
    W, H = 180, 225
    duration = 7
    palette = "paper"
    background = "bg.4"
    anim_fps = 15

    def draw(self, c, t):
        c.clear("bg.4")
        x0, x1, base, top = 14, 168, 178, 58
        # title
        c.text(TITLE, 14, 16, "main.0", font="tiny")
        c.hline(14, 166, 25, "main.0")
        # grid
        for k in range(1, 5):
            gy = base - (base - top) * k / 4
            c.line(x0, gy, x1, gy, "bg.2", dash=(1, 2))
        c.hline(x0, x1, base, "main.0")

        n = len(DATA)
        vmax = max(v for _, v in DATA)
        slot = (x1 - x0) / n
        bw = int(slot * 0.62)
        best = max(range(n), key=lambda i: DATA[i][1])
        for i, (label, v) in enumerate(DATA):
            t0 = 0.4 + i * 0.28
            u = ease(prog(t, t0, t0 + 0.6), "outBack")
            h = max(0, (base - top) * v / vmax * u)
            bx = int(x0 + slot * i + (slot - bw) / 2)
            hl = i == best and t > 0.4 + n * 0.28 + 0.4
            fill = "acc.1" if hl else "main.1"
            c.rect(bx, base - h, bw, h, fill)
            c.vline(bx, base - h, base - 1, "acc.2" if hl else "main.2")
            c.hline(bx, bx + bw - 1, base - h, "acc.2" if hl else "main.3")
            c.text(label, bx + bw // 2, base + 4, "main.2", font="tiny", align="center")
            if u > 0.05:
                c.text(f"{v * min(1, u):.0f}", bx + bw // 2, base - h - 8, "acc.1" if hl else "main.0",
                       font="tiny", align="center")
        # call out the biggest day
        tc = 0.4 + n * 0.28 + 0.4
        if t > tc:
            bx = int(x0 + slot * best + slot / 2)
            vy = base - (base - top) * DATA[best][1] / vmax
            pop = ease(prog(t, tc, tc + 0.3), "outBack")
            if pop > 0.1:
                ui.tag(c, bx, int(vy - 22 - 3 * (1 - pop)), "PEAK", fill="acc.1", color="bg.4", align="center")
        # total
        tt = tc + 0.6
        total = sum(v for _, v in DATA)
        if t > tt:
            c.text(TOTAL_LABEL, 14, 196, "main.2", font="tiny")
            c.text(f"{tween(t, tt, tt + 1.0, 0, total, 'outCubic'):,.0f}{UNIT}", 14, 203, "main.0", scale=2)

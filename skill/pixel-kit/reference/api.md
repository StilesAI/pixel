# pixelkit API

```python
from pixelkit import Scene, Canvas, Keys, fx, props, shapes, sprite, ui, ramp
from pixelkit.anim import ease, prog, tween, osc, blink, count, typewriter
```

## Scene

```python
class MyScene(Scene):
    W, H = 180, 225        # canvas
    duration = 8           # seconds
    palette = "night"      # preset name or path to .json
    anim_fps = 12          # motion update rate (None = every frame)
    background = "bg.0"    # fill before draw()

    def setup(self): ...           # once: sprites, emitters, layers
    def draw(self, c, t): ...      # every frame; t in seconds
```
The file can hold helpers and constants; the renderer uses the last Scene subclass in the file.

## Color references

Ramps and their lengths (index 0 = darkest):
`bg` 5, `main` 6, `alt` 5, `acc` 4, `warm` 4, `cool` 4, `leaf` 4, `skin` 3, `ui` 4
(`ui.0` panel fill, `ui.1` panel line, `ui.2` dim text, `ui.3` text).
`"main"` alone = middle level. `"main.-1"` = lightest. `"clear"` = transparent.
`ramp("bg")` returns the slot numbers of a ramp (handy for masks: `np.isin(c.buf, ramp("bg"))`).
`Dither(a, b, level)` is a fill: ordered dither from a (level 0) to b (level 16).

## Canvas `c`

Shapes (color = reference, Dither, or fn(x, y)):
`c.rect(x, y, w, h, col)`, `c.frame(x, y, w, h, col, t=1)`, `c.hline(x0, x1, y, col)`,
`c.vline(x, y0, y1, col)`, `c.line(x0, y0, x1, y1, col, dash=(2, 2))`, `c.disc(cx, cy, r, col)`,
`c.ring(cx, cy, r, col)`, `c.ellipse(cx, cy, rx, ry, col)`, `c.poly([(x, y), ...], col)`,
`c.pset(x, y, col)`, `c.get(x, y)`, `c.clear(col)`

Masks (bool arrays; combine with `&`, `|`, `~`, then `c.paint(mask, col)`):
`c.m_rect`, `c.m_disc`, `c.m_ellipse`, `c.m_poly`, `c.m_line`, `c.m_ring`, `c.m_opaque()`

Fills: `c.gradient_v(x, y, w, h, [cols top->bottom])`, `c.gradient_radial(cx, cy, r, [cols])`

Light: `c.darken(mask=None, steps=1, level=16)`, `c.lighten(...)` (level < 16 dithers),
`c.glow(cx, cy, r, steps=2, mask=None)`, `c.tint(mask, to="warm", level=16)`,
`c.tint_radial(cx, cy, r, to="warm", mask=None, inner=0.45)`, `c.shadow(cx, cy, rx, ry)`,
`c.outline_mask(mask, col, diagonal=False)`

Compositing: `Canvas(w, h)` makes a transparent layer. `c.blit(src, x, y, anchor="topleft"|"center"|"bottom"|"bottomleft", flip=False, mask=None)`,
`c.blit_rotated(src, angle_deg, pivot=(px, py), at=(x, y))` (clean RotSprite-style rotation),
`c.copy()`, `c.shift(dx, dy)` (camera shake), `layer.flip_x()`, `layer.recolor({"main.3": "acc.1"})`,
`layer.with_outline(col)`, `layer.trimmed()`

Text: `c.text(s, x, y, col="ui.3", font="body"|"tiny", scale=1, align="left"|"center"|"right", shadow=None, outline=None)`,
`Canvas.measure(s, font, scale)`

## shapes

`cylinder(c, x, y, w, h, ramp_list, light=0.3)` towers, rockets, cans
`sphere(c, cx, cy, r, ramp_list, light=(-0.55, -0.65))` planets, balls, heads
`slab(c, x, y, w, h, ramp_list, top=2, side=None)` ledges, desks, platforms
`truss(c, x, y, w, h)` / `truss_h(...)` lattice towers and beams
`ground(c, y, ramp=("alt.0", "alt.1", "alt.2"))`

## props (scenery, all palette-aware)

Nature: `pine`, `round_tree`, `bush`, `mushroom`, `rock`, `mountain`, `cloud`, `sun`, `water(c, y0, y1, t)`, `fireflies(c, t)`
Built: `building`, `skyline(c, base, t, lit=0.5)`, `house`, `lamp_post`, `desk_lamp`, `laptop`, `crate`, `screen_panel`
Characters: `robot(c, x, base, s=22, t=t, blink=False, look=0, talk=False)`

## fx

`Emitter(seed, t0, t1, rate, origin=(x, y) or fn(t), angle, spread, speed=(a, b), life=(a, b), gravity, drag, colors=[birth..death], size=(r0, r1), wind)` then `.draw(c, t)`. Sparks, embers, exhaust, steam wisps.
`Billow(seed, center, t0, n, spread=(sx, sy), grow=(r0, r1), rise, dur, drift, ramp, fade_after, fade_dur)` then `.draw(c, t)`. Clouds of smoke, steam, dust, drawn as one lit mass.
`stars(c, t, n, region)`, `rain(c, t)`, `snow(c, t)`, `dust_motes(c, t)`, `puff(c, x, y, r, ramp)`
`vignette(c, strength)`, `fade(c, amount)`, `shake(t, t0, t1, amp)` -> (dx, dy) for `c.shift`, `heat_haze(c, t, y0, y1)`

## ui (overlay layer, draw last)

`readout(c, x, y, label, value, unit="", w=None, show=1.0)` instrument box: tiny label + big value; `show` 0..1 wipes it open
`tag(c, x, y, text, fill="acc.1")` solid label
`caption(c, text, y, font="tiny")` centered subtitle chip
`panel`, `bar(c, x, y, w, h, frac)`, `sparkline(c, x, y, w, h, values, upto)`,
`bracket(c, x, y0, y1)` dimension bracket, `guide_h` / `guide_v` dashed guides,
`arc(c, cx, cy, r, a0, a1)` angle arcs, `arrow`, `scan_reveal`, `scan_reveal_up(c, layer, t, t0, t1)` build-up reveal

## anim

`ease(u, kind)` kinds: linear, in/out/inOut + Quad, Cubic, Quart, Sine, Expo, outBack, inBack, outElastic, outBounce
`prog(t, t0, t1)` 0..1, `tween(t, t0, t1, a, b, kind)`, `Keys((t, v), (t, v, "outBack"), ...)` callable keyframes (values can be tuples),
`osc(t, period, amp)`, `blink(t, period, duty)`, `count(t, t0, t1, a, b, decimals=0)` counting string,
`typewriter(text, t, t0, cps)`

## sprites

`sprite.load("robot")` -> sheet; `sheet[0]`, `sheet.at(t, fps=8)` for a cycling frame.
Available: robot, cat, person (idle + 4-frame walk), bird, coin, heart.
New sprite = a text file in assets/sprites (format at the top of pixelkit/sprite.py).
`sprite.from_png(path, palette)` brings in the user's own pixel art, snapped to the palette.

## CLI

```
pk render scene.py [--sheet [--frames N]] [--still T] [--gif] [--video]
                   [--palette NAME|file.json] [--hue "#hex"] [--mono] [--colors "#a,#b,..."]
                   [--all-modes [--accent "#hex"]] [--duration S] [--best] [--out DIR]
pk new TEMPLATE scenes/name.py
pk palettes        swatches of every palette -> out/palettes.png
pk sprites         every sprite -> out/sprites.png
pk doctor          install check
```

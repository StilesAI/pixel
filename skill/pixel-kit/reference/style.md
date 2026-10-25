# Pixel Kit style rules

These are what make code-drawn frames read as hand-made pixel art instead of a filter.

## Canvas and scale

| Canvas | Export | Use |
|---|---|---|
| 180 x 225 | 1080 x 1350 (6x) | default, 4:5 feed post or the card inside a reel |
| 180 x 320 | 1080 x 1920 (6x) | full-screen 9:16 |
| 120 x 150 | 1080 x 1350 (9x) | character scenes, chunkier pixels |
| 180 x 180 | 1080 x 1080 (6x) | square |

Never mix pixel sizes. Do not scale sprites up with `scaled()` inside a scene unless every
object in the scene is scaled the same way; mixed pixel sizes look broken. If a character
is too small, use a smaller canvas instead.

## Color

- Only palette references (`"main.3"`, `"bg.0"`, `"acc.1"`). No hex in scenes. That is what lets
  one scene render in every color mode.
- Ramps go dark (0) to light (last). Shadows use lower levels of the same ramp, not black.
- Roles: `bg` sky and backdrop, `main` the hero material, `alt` secondary material and ground,
  `acc` the one accent (UI emphasis, the thing you want looked at), `warm` fire and lamps,
  `cool` water and screens, `leaf` plants, `skin`, `ui` panel fill, panel line, dim text, text.
- One accent per frame. If everything is bright, nothing is.
- Night scenes: keep the background in `bg.0`-`bg.2` and let lights pop with `warm.2`-`warm.3`.

## Light and form

- One light, upper left, unless a scene has a strong local light (a flame, a lamp, a screen).
- Use `shapes.cylinder`, `shapes.sphere`, `shapes.slab` for volume instead of flat fills.
- Local light: `c.glow(...)` for a pool of light, `c.tint(...)` / `c.tint_radial(...)` to push
  pixels into the light's color (steam lit orange by a flame). Restrict light on the sky with a
  mask when it should only hit objects.
- On large smooth surfaces (a booster, a wall), prefer clean solid bands over dithered glow.
  Dither noise on a hero object looks dirty.
- Contact shadows (`c.shadow`) under anything that sits on the ground.

## Dither

- Dither belongs at the seam between two bands (sky gradients, falloff of a light), not across
  a whole area.
- Never dither text, UI, or small sprites.

## Motion

- `anim_fps = 12` to `15` gives a hand-animated feel. Output is still 30fps.
- Positions are whole pixels. Slow motion under 1px per update reads as jitter; either move
  faster or hold.
- Anything with a number on screen should move physically: if a readout says it is slowing
  down, the object has to actually decelerate (see `booster_top` in examples/booster_catch.py).
- Ease in and out of every move (`Keys`, `tween`, `ease`). Overshoot with `outBack` for things
  that land or pop in.
- Randomness is always seeded (`np.random.default_rng(seed)`), so every frame renders the same
  every time and the preview sheet matches the final video.
- Add small ambient life to holds: twinkling stars, blinking lights, drifting smoke, a blink.

## Text and HUD

- Fonts: `tiny` (3x5 caps) for labels, `body` (5x7) for readable text, `scale=2` for big numbers.
- Draw HUD, readouts, tags, and captions last, after vignette and lighting, so effects never
  speckle them.
- Keep HUD out of the path of the subject. If the subject travels through the top-left, put the
  numbers in a bottom bar (see the telemetry bar in booster_catch).
- Labels are plain and literal: DISTANCE TO ARMS, HEIGHT, FALLEN. No slogans.

## Composition

- The subject is on screen in the first frame.
- Leave a quiet area for captions if the clip will be posted with subtitles (reels put captions
  over the lower third).
- Fill the frame: no large dead zones. If the ground eats a third of the frame, raise the horizon
  or use that space for a HUD bar.

## Review checklist (run on every contact sheet)

1. Is the subject visible and readable in the first frame?
2. Is there one clear focal point per frame?
3. Does anything flicker, jitter, or pop that should not?
4. Is any text or UI covered, clipped, speckled by dither, or running off the edge?
5. Do numbers match the motion (counting down while moving, stopping when it stops)?
6. Are there stray pixels, noisy dither on hero objects, or shapes that read as blobs?
7. Is there a large empty or dead area?
8. Does the ending hold long enough (about 1.5s) to land?
9. Does it still read in `--mono`? If not, the values (light vs dark) need more contrast.

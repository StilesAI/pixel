#!/usr/bin/env node
// Pin a pixelfx effect to a tracked joint and leave a fading trail of copies behind it.
//
//   node tools/fx_follow.mjs <effect-id> --track take.track.json --out out/aurora [--palette aurora] [--scale 4]
//
// aurora-ribbon is this kit's own (fx/); every other effect comes from pixelfx by Patch (github.com/patch-gg/pixelfx, MIT, method by Hugo Duprez). Nothing of
// pixelfx is copied here: this imports it from your own clone (--pixelfx, $PIXELFX, pk.config.json, or
// ../pixelfx next to this kit).
//
// Writes two passes at the take's size, upscaled with hard square pixels:
//   color.mov  ProRes 4444 with alpha: lay it over the take normally
//   light.mov  the glow on black: blend it with Add (or Screen)
//
// Options:
//   --palette  aurora | blue | "#hex,#hex,..." dark to bright (default aurora)
//   --palette-at "20.16:blue,22.3:aurora"  switch palette at these take times (s); the head flips at once and
//              the trail behind it keeps the old color as it fades, so the swap sweeps along the arm
//   --arm      how far down the forearm the trail reaches, 0 = wrist only, 1 = to the elbow (default 0.45)
//   --sweep    path effects: 0 = rays run straight down the forearm, 1 = square to the motion (default 0.35)
//   --thick    effect pixels the trail spreads to each side of the path (default 3)
//   --scale    output pixels per effect pixel (default 7; bigger = chunkier and bigger effect)
//   --life     seconds a trail copy lasts (default 0.6), or how long a path effect's trail is (default 1.2)
//   --spacing  effect pixels between copies (default 2)
//   --glow     overall light strength (default 1)          --max-copies N (default 90)          --seed N
//   --anchor   "x,y": the effect pixel that sits on the joint (default: the centre of the effect's box)
//   --face-pad extra margin round the head mask, as a fraction of head size (default 0.15)

import { readFileSync, existsSync, mkdirSync, statSync } from "node:fs";
import { join, dirname, resolve } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import { spawn } from "node:child_process";

const KIT = resolve(dirname(fileURLToPath(import.meta.url)), "..");

export const PALETTES = {
  aurora: ["#0a2f1a", "#19a64a", "#3fe36b", "#b8ff3c", "#f2ffb0"],
  blue: ["#030826", "#0a1a7a", "#1f3dff", "#4a68ff", "#a6b6ff"],
};

function args(argv) {
  const f = { _: [] };
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a.startsWith("--")) f[a.slice(2)] = argv[i + 1] && !argv[i + 1].startsWith("--") ? argv[++i] : true;
    else f._.push(a);
  }
  return f;
}

export function findPixelfx(flag) {
  const cfg = join(KIT, "pk.config.json");
  const tries = [flag, process.env.PIXELFX, existsSync(cfg) ? JSON.parse(readFileSync(cfg, "utf8")).pixelfx : null,
    join(KIT, "..", "pixelfx")].filter(Boolean).map((p) => resolve(KIT, p));
  const hit = tries.find((p) => existsSync(join(p, "src", "core", "index.js")));
  if (!hit) throw new Error(`can't find pixelfx (tried ${tries.join(", ")}). Clone github.com/patch-gg/pixelfx ` +
    `next to this kit, or pass --pixelfx PATH.`);
  return hit;
}

const parsePalette = (p) => PALETTES[p] ?? p.split(",").map((s) => s.trim());
const clamp = (v, a = 0, b = 1) => Math.min(b, Math.max(a, v));
const smooth = (a, b, v) => { const t = clamp((v - a) / (b - a)); return t * t * (3 - 2 * t); };
const BAYER = [0, 8, 2, 10, 12, 4, 14, 6, 3, 11, 1, 9, 15, 7, 13, 5].map((v) => (v + 0.5) / 16);

export async function follow(o) {
  const PFX = findPixelfx(o.pixelfx);
  const core = await import(pathToFileURL(join(PFX, "src", "core", "index.js")).href);
  // the kit's own effects (fx/, drawn with pixelfx's core) first, then pixelfx's
  const own = join(KIT, "fx", o.effect + ".js"), file = existsSync(own) ? own : join(PFX, "src", "fx", o.effect + ".js");
  if (!existsSync(file)) throw new Error(`no effect ${o.effect} in ${KIT}/fx or ${PFX}/src/fx (see docs/CATALOG.md)`);
  const m = await import(pathToFileURL(file).href);
  const mod = file === own ? { meta: m.meta, draw: (p, t, opts) => m.draw(p, t, opts, core) } : m;
  const meta = { loop: false, duration: 1, options: {}, ...mod.meta };
  if (meta.actor) console.warn(`  note: ${o.effect} is drawn round a character; the trail uses the effect alone`);

  const track = JSON.parse(readFileSync(o.track, "utf8"));
  const [VW, VH] = track.size, K = o.scale, fps = track.fps;
  const W = Math.ceil(VW / K), H = Math.ceil(VH / K);
  const frame = core.createFrame(W, H);
  // palette schedule in take time: [{ at, ramp }], first entry from t = -inf
  const sched = [{ at: -Infinity, ramp: parsePalette(o.palette) }, ...(o.paletteAt ? o.paletteAt.split(",").map((s) => {
    const [at, p] = s.split(/:(.*)/s);
    return { at: +at, ramp: parsePalette(p) };
  }) : [])].sort((a, b) => a.at - b.at);
  const rampAt = (tt) => sched.filter((s) => s.at <= tt).pop();
  const [SW, SH] = meta.size, [OX, OY] = meta.origin;
  const [ax, ay] = o.anchor ? o.anchor.split(",").map(Number) : [SW / 2, SH / 2];
  // painter.place puts the effect's origin at (x, y); shift so the anchor pixel lands on the joint instead
  const dx = OX - ax, dy = OY - ay;

  // an effect instance whose fade and light we set per frame (createFx owns its own fade, so this mirrors it)
  let nseed = 0;
  const make = (t0 = 0, palette = sched[0].ramp) => {
    const opts = core.resolveOptions(meta, { palette, seed: (o.seed ?? meta.options.seed ?? 1) + nseed++ * 7 });
    const impl = mod.create ? mod.create(opts) : mod;
    let t = t0;
    return {
      opts,
      age: 0,
      get t() { return t; },
      update(dt) {
        t += dt;
        this.age += dt;
        if (!impl.update) return;
        const n = Math.max(1, Math.ceil(dt * 120 - 1e-9));
        for (let i = 0; i < n; i++) impl.update(dt / n, opts);
      },
      draw(x, y, fade, lightK) {
        if (fade <= 0.01) return;
        const p = core.painterFor(frame);
        p.place(Math.round(x + dx), Math.round(y + dy), false, 0);
        p.fade = fade;
        p.lightK = lightK;
        const tt = meta.loop ? t % meta.duration : Math.min(t, meta.duration);
        if (impl.drawBack) { p.layer = "back"; impl.drawBack(p, tt, opts); }
        p.layer = "front";
        impl.draw(p, tt, opts);
      },
    };
  };

  // path effects (tagged "path", like aurora-ribbon) draw the whole trail themselves from the joint's
  // recent path, so no copies: just hand them the path each frame
  if ((meta.tags ?? []).includes("path")) return followPath(o, { core, mod, meta, track, frame, W, H, K, VW, sched, rampAt });

  // fast-forward the head so a looping effect starts already going
  let cur = sched[0];
  let head = make(meta.loop ? meta.duration * 0.37 : 0, cur.ramp);
  const trail = [];
  let headFade = 0, last = null, boost = 0, rnd = 12345;
  const rand = () => ((rnd = (rnd * 1103515245 + 12345) >>> 0) / 4294967296);
  const dt = 1 / fps, life = o.life, glow = o.glow;

  const { C, L, write, finish } = encoders(o, W, H, K, track);

  const colorBuf = Buffer.alloc(W * H * 4), lightBuf = Buffer.alloc(W * H * 4);
  const stats = { maxCopies: 0, spawned: 0 };
  for (const f of track.frames) {
    const x = f.xy[0] / K, y = f.xy[1] / K;
    // a palette change: a fresh head in the new colors, same phase, and a short bloom so the swap reads
    const want = rampAt((track.start ?? 0) + f.t);
    if (want !== cur) {
      cur = want;
      head = make(head.t, cur.ramp);
      boost = 1;
      stats.swaps = (stats.swaps ?? 0) + 1;
    }
    // how hard the hand is moving, in frame widths per second: drives the glow and the trail
    const g = f.lost ? 0 : Math.max(smooth(0.06, 0.9, f.speed / VW), 0.5 * boost);
    headFade += ((f.lost ? 0 : 1) - headFade) * 0.35;

    if (!f.lost && g > 0.02 && (!last || Math.hypot(x - last[0], y - last[1]) >= o.spacing)) {
      // across the path: copies to each side of the line of motion make the trail thick
      const mx = last ? x - last[0] : 1, my = last ? y - last[1] : 0, ml = Math.hypot(mx, my) || 1;
      const nx = -my / ml, ny = mx / ml;
      const spots = [[x, y, 1]];
      for (const side of [-1, 1]) {
        const d = o.thick * (0.6 + 0.6 * rand());
        spots.push([x + nx * d * side, y + ny * d * side, 0.75]);
      }
      // down the forearm towards the elbow, dimmer the further from the hand
      if (f.elbow && o.arm > 0) {
        const ex = f.elbow[0] / K, ey = f.elbow[1] / K, len = Math.hypot(ex - x, ey - y) * o.arm;
        const n = Math.min(8, Math.floor(len / Math.max(2, o.thick * 1.2)));
        for (let j = 1; j <= n; j++) {
          const u = (j / n) * o.arm, wob = (rand() - 0.5) * o.thick * 1.4;
          spots.push([x + (ex - x) * u + nx * wob, y + (ey - y) * u + ny * wob, 0.85 - 0.5 * (j / n)]);
        }
      }
      for (const [sx, sy, w] of spots) {
        const c = make(head.t + rand() * meta.duration, cur.ramp);
        c.x = sx; c.y = sy; c.k = (0.35 + 0.65 * g) * w;
        trail.push(c);
        stats.spawned++;
      }
      last = [x, y];
    }
    if (f.lost) last = null;
    boost = Math.max(0, boost - dt / 0.5);

    core.clearFrame(frame);
    // oldest first, so the head lands on top
    for (let i = trail.length - 1; i >= 0; i--) if (trail[i].age >= life) trail.splice(i, 1);
    trail.sort((a, b) => b.age - a.age);
    if (trail.length > o.maxCopies) trail.splice(0, trail.length - o.maxCopies);
    for (const c of trail) {
      const a = 1 - c.age / life;
      // light stacks up across overlapping copies, so each one only adds a little
      c.draw(c.x, c.y, c.k * a ** 1.4, glow * (0.1 + 0.3 * g) * c.k * a * a);
    }
    head.draw(x, y, headFade, glow * (0.35 + 0.6 * g + 0.6 * boost));
    stats.maxCopies = Math.max(stats.maxCopies, trail.length);

    if (f.face && o.facePad >= 0) maskFace(frame, f.face.map((v) => v / K), o.facePad);
    split(frame, colorBuf, lightBuf);
    await write(C, colorBuf);
    await write(L, lightBuf);

    head.update(dt);
    for (const c of trail) c.update(dt);
  }
  await finish();
  return { dir: o.out, world: [W, H], scale: K, frames: track.frames.length, ...stats };
}

async function followPath(o, { core, mod, meta, track, frame, W, H, K, VW, sched, rampAt }) {
  const fps = track.fps, dt = 1 / fps, life = o.pathLife;
  const opts = core.resolveOptions(meta, { palette: sched[0].ramp, seed: o.seed ?? meta.options.seed ?? 1 });
  opts.ramps = sched.map((s) => s.ramp);
  const { C, L, write, finish } = encoders(o, W, H, K, track);
  const colorBuf = Buffer.alloc(W * H * 4), lightBuf = Buffer.alloc(W * H * 4);
  const hist = [];
  let t = 0, boost = 0, cur = sched[0], arm = null, act = 0, gap = false;
  for (const f of track.frames) {
    const now = f.t, want = rampAt((track.start ?? 0) + f.t);
    if (want !== cur) { cur = want; boost = 1; }
    // a lost hand (out of frame, hidden) adds nothing: the trail it left keeps fading out instead of vanishing,
    // and when the hand comes back its new trail starts fresh rather than joining up across the gap
    if (f.lost) gap = true;
    else {
      const g = Math.max(smooth(0.04, 0.8, f.speed / VW), 0.6 * boost);
      // activity: up at once when the hand moves, down over ~0.8 s once it rests, so a still hand goes dark
      const want = Math.max(smooth(0.03, 0.22, f.speed / VW), boost);
      act = want > act ? act + (want - act) * 0.5 : Math.max(want, act - dt / 0.8);
      const x = f.xy[0] / K, y = f.xy[1] / K;
      // the arm side: towards the elbow (or straight down without one); rays hang off the path that way
      // when the elbow drops out of frame, keep the last forearm we saw (for up to a second)
      if (f.elbow) {
        const ex = f.elbow[0] / K - x, ey = f.elbow[1] / K - y;
        arm = { ex, ey, t: now };
      } else if (arm && now - arm.t > 1) arm = null;
      let ax = 0, ay = 1, len = 44;
      if (arm) {
        const el = Math.hypot(arm.ex, arm.ey) || 1;
        ax = arm.ex / el; ay = arm.ey / el; len = Math.max(40, el * o.pathArm);
      }
      hist.unshift({ t: now, x, y, ax, ay, len, k: (0.45 + 0.55 * g) * act, pal: sched.indexOf(cur), brk: gap && hist.length > 0 });
      gap = false;
    }
    while (hist.length && now - hist[hist.length - 1].t > life) hist.pop();
    // rays square to the path (a curtain hanging off it), turned to the arm side, eased with the arm direction
    for (let i = 0; i < hist.length; i++) {
      // neighbours for the path direction, without reaching across a gap (h.brk: no line from h to the next older)
      let ia = i, ib = i;
      while (ia > i - 3 && ia > 0 && !hist[ia - 1].brk) ia--;
      while (ib < i + 3 && ib < hist.length - 1 && !hist[ib].brk) ib++;
      const h = hist[i], a = hist[ia], b = hist[ib];
      h.age = (now - h.t) / life;
      let tx = b.x - a.x, ty = b.y - a.y;
      const tl = Math.hypot(tx, ty);
      let nx = h.ax, ny = h.ay;
      if (tl > 1.5) {
        nx = -ty / tl; ny = tx / tl;
        if (nx * h.ax + ny * h.ay < 0) { nx = -nx; ny = -ny; }
        // mostly down the forearm, leaning back along the sweep: the light pours off the whole arm
        nx = nx * o.sweep + h.ax * (1 - o.sweep); ny = ny * o.sweep + h.ay * (1 - o.sweep);
      }
      const nl = Math.hypot(nx, ny) || 1;
      h.dx = nx / nl; h.dy = ny / nl;
    }
    core.clearFrame(frame);
    if (hist.length > 1) {
      const p = core.painterFor(frame);
      p.place(0, 0, false, 0);
      p.fade = 1;
      p.lightK = o.glow;
      opts.path = hist;
      mod.draw(p, t, opts);
    }
    if (f.face && o.facePad >= 0) maskFace(frame, f.face.map((v) => v / K), o.facePad);
    split(frame, colorBuf, lightBuf);
    await write(C, colorBuf);
    await write(L, lightBuf);
    t += dt;
    boost = Math.max(0, boost - dt / 0.5);
  }
  await finish();
  return { dir: o.out, world: [W, H], scale: K, frames: track.frames.length, spawned: 0, maxCopies: 0 };
}

function encoders(o, W, H, K, track) {
  const [VW, VH] = track.size, fps = track.fps;
  mkdirSync(o.out, { recursive: true });
  const enc = (name, alpha) => {
    const ff = spawn("ffmpeg", ["-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgba", "-s", `${W}x${H}`,
      "-r", String(fps), "-i", "-", "-vf", `scale=${W * K}:${H * K}:flags=neighbor,crop=${VW}:${VH}:0:0`,
      "-c:v", "prores_ks", "-profile:v", alpha ? "4444" : "3", "-pix_fmt", alpha ? "yuva444p10le" : "yuv422p10le",
      ...(alpha ? ["-alpha_bits", "16"] : []), join(o.out, name)], { stdio: ["pipe", "inherit", "inherit"] });
    const done = new Promise((ok, no) => ff.on("close", (c) => (c ? no(new Error(`ffmpeg ${name} exit ${c}`)) : ok())));
    return { ff, done };
  };
  const C = enc("color.mov", true), L = enc("light.mov", false);
  const write = (s, buf) => new Promise((ok) => (s.ff.stdin.write(buf) ? ok() : s.ff.stdin.once("drain", ok)));
  const finish = async () => { C.ff.stdin.end(); L.ff.stdin.end(); await Promise.all([C.done, L.done]); };
  return { C, L, write, finish };
}

// keep the effect off the face: nothing inside an ellipse round the head box, a dithered edge round it
function maskFace(f, [x0, y0, x1, y1], pad) {
  const cx = (x0 + x1) / 2, cy = (y0 + y1) / 2, rx = ((x1 - x0) / 2) * (1 + pad), ry = ((y1 - y0) / 2) * (1 + pad);
  const ya = Math.max(0, Math.floor(cy - ry * 1.3)), yb = Math.min(f.h - 1, Math.ceil(cy + ry * 1.3));
  const xa = Math.max(0, Math.floor(cx - rx * 1.3)), xb = Math.min(f.w - 1, Math.ceil(cx + rx * 1.3));
  for (let y = ya; y <= yb; y++)
    for (let x = xa; x <= xb; x++) {
      const e = Math.hypot((x + 0.5 - cx) / rx, (y + 0.5 - cy) / ry);
      const keep = clamp((e - 1) / 0.3);
      if (keep >= 1) continue;
      const i = y * f.w + x;
      if (keep <= BAYER[((y & 3) << 2) | (x & 3)]) f.color[i] = 0;
      const l = f.light[i];
      if (l) f.light[i] = ((l & 255) * keep) | ((((l >>> 8) & 255) * keep) << 8) | ((((l >>> 16) & 255) * keep) << 16);
    }
}

// the color buffer as RGBA over transparency, the light buffer as RGB on black
function split(f, cb, lb) {
  for (let i = 0, j = 0; i < f.w * f.h; i++, j += 4) {
    const c = f.color[i], l = f.light[i];
    cb[j] = c & 255; cb[j + 1] = (c >>> 8) & 255; cb[j + 2] = (c >>> 16) & 255; cb[j + 3] = c >>> 24;
    lb[j] = l & 255; lb[j + 1] = (l >>> 8) & 255; lb[j + 2] = (l >>> 16) & 255; lb[j + 3] = 255;
  }
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const a = args(process.argv.slice(2));
  if (!a._[0] || !a.track) {
    console.error("usage: node tools/fx_follow.mjs <effect-id> --track take.track.json --out DIR [--palette aurora]");
    process.exit(1);
  }
  const t0 = Date.now();
  const r = await follow({
    effect: a._[0], track: a.track, out: a.out ?? join("out", a._[0].replace("/", "_")), pixelfx: a.pixelfx,
    palette: a.palette ?? "aurora", scale: +(a.scale ?? 7), life: +(a.life ?? 0.6), spacing: +(a.spacing ?? 2), arm: +(a.arm ?? 0.45),
    thick: +(a.thick ?? 3), pathLife: +(a.life ?? 1.2), pathArm: +(a.arm ?? 1.6), sweep: +(a.sweep ?? 0.35), maxCopies: +(a["max-copies"] ?? 90), paletteAt: a["palette-at"],
    glow: +(a.glow ?? 1), seed: a.seed ? +a.seed : undefined, anchor: a.anchor, facePad: +(a["face-pad"] ?? 0.15),
  });
  console.log(`  ${a._[0]}: ${r.frames} frames, ${r.world.join("x")} px x${r.scale}, ${r.spawned} trail copies ` +
    `(max ${r.maxCopies} at once), ${((Date.now() - t0) / 1000).toFixed(1)}s -> ${r.dir}/color.mov + light.mov`);
}

// An aurora ribbon that follows a path: a thin bright hem with posterized bands of light behind it and fine rays
// streaming off it, fading out along the path. Built on the look of weather/aurora (posterized steps from a bright
// hem out to deep color, fine strands, a soft bloom), whose banded light is adapted from Sprite Fusion's
// open-source holy light (https://www.spritefusion.com/pixel-art-vfx/holy-light), MIT License, Copyright (c) 2026
// Hugo Duprez.
//
// o.path: [{ x, y, age (0 newest..1 oldest), k (strength 0..1), dx, dy (ray direction, unit), len (ray length),
// pal (index into o.ramps), brk (true: no ribbon from here to the next point) }] in local pixels. Without a path it
// draws its own swaying S so it can be previewed.
//
// A Pixel Kit effect, not part of pixelfx: tools/fx_follow.mjs loads it and hands it pixelfx's core (from your
// pixelfx clone) as the fourth argument to draw, so it paints with the same painter and colors as the pixelfx effects.
let clamp, smooth, mix, hex, TAU;

export const meta = {
  name: "Aurora ribbon",
  desc: "A ribbon of northern lights trailing along a path: a pale hem, posterized green bands and fine rays streaming off it, the far end fading away in dithered steps.",
  tags: ["weather", "aurora", "northern lights", "ribbon", "trail", "path", "loop"],
  size: [160, 200],
  origin: [0, 0],
  duration: 4,
  loop: true,
  fps: 30,
  bg: "sky",
  options: {
    palette: ["#0a2f1a", "#19a64a", "#3fe36b", "#b8ff3c", "#f2ffb0"],
    upper: ["#1a1040", "#2e1d6b", "#4b2a9e", "#7444c8", "#a476ee"],
    violet: 0.7,
    width: 4,
    rays: 34,
    floor: 3,
    glow: 0.8,
    halo: 0.45,
    body: 0.55,
    seed: 4,
  },
};

const BAY = [0, 8, 2, 10, 12, 4, 14, 6, 3, 11, 1, 9, 15, 7, 13, 5].map((v) => (v + 0.5) / 16);
const STEPS = 8;
// a ramp blended out to n distinct steps (a 5-color palette would otherwise repeat steps and lose the banding)
const steps = (r, n) => Array.from({ length: n }, (_, i) => {
  const f = (i / (n - 1)) * (r.length - 1), k = Math.min(r.length - 2, Math.floor(f));
  return mix(hex(r[k]), hex(r[k + 1]), f - k);
});
let I, U, PI, BL, HB, TMP, FW = 0, FH = 0;

// light across a ray, from the hem (v = 0) out to its tip (v = 1): a pale hem, a body that holds, rays fading out
const PROF = Float32Array.from({ length: 201 }, (_, i) => {
  const v = i / 200;
  return v < 0.04 ? 0.86 : v < 0.3 ? 0.74 - 0.4 * v : 0.62 * (1 - v) ** 1.4;
});

// seeded 1D value noise, smooth, 0..1
const hash = (n, s) => {
  const x = Math.sin(n * 127.1 + s * 311.7) * 43758.5453;
  return x - Math.floor(x);
};
const noise = (x, s) => {
  const i = Math.floor(x), f = x - i, u = f * f * (3 - 2 * f);
  return hash(i, s) * (1 - u) + hash(i + 1, s) * u;
};

function demoPath(t) {
  const pts = [], n = 90;
  for (let i = 0; i < n; i++) {
    const a = i / (n - 1), ph = (TAU * t) / 4 - a * 2.4;
    pts.push({ x: 20 + a * 120 + Math.sin(ph * 1.3) * 10, y: 150 + Math.sin(ph) * 26, age: a, k: 1, dx: 0.15, dy: -1, len: 70, pal: 0 });
  }
  return pts;
}

function blur(src, dst, w, h, r) {
  const n = 2 * r + 1;
  for (let y = 0; y < h; y++) {
    let acc = 0;
    const o = y * w;
    for (let x = -r; x < w + r; x++) {
      if (x + r < w) acc += src[o + Math.min(w - 1, x + r)];
      if (x - r - 1 >= 0) acc -= src[o + x - r - 1];
      if (x >= 0 && x < w) TMP[o + x] = acc / n;
    }
  }
  for (let x = 0; x < w; x++) {
    let acc = 0;
    for (let y = -r; y < h + r; y++) {
      if (y + r < h) acc += TMP[Math.min(h - 1, y + r) * w + x];
      if (y - r - 1 >= 0) acc -= TMP[(y - r - 1) * w + x];
      if (y >= 0 && y < h) dst[y * w + x] = acc / n;
    }
  }
}

export function draw(p, t, o, core) {
  ({ clamp, smooth, mix, hex, TAU } = core);
  const w = p.w, h = p.h;
  if (w !== FW || h !== FH) {
    [I, U, BL, HB, TMP] = [0, 0, 0, 0, 0].map(() => new Float32Array(w * h));
    PI = new Uint8Array(w * h);
    FW = w; FH = h;
  }
  I.fill(0);
  U.fill(0);
  PI.fill(0);
  const ramps = (o.ramps ?? [o.palette]).map((r) => steps(r, STEPS));
  const UP = steps(o.upper, STEPS);
  const path = o.path ?? demoPath(t);
  if (path.length < 2) return;

  // resample the path to about one pixel per step, tracking distance along it for the strands
  let dist = 0;
  const S = o.seed;
  for (let i = 0; i < path.length - 1; i++) {
    const A = path[i], B = path[i + 1];
    if (A.brk) continue; // the hand was lost between these two: no ribbon across the gap
    const ax = p.toX(A.x, A.y) - p.ox, ay = p.toY(A.x, A.y) - p.oy, bx = p.toX(B.x, B.y) - p.ox, by = p.toY(B.x, B.y) - p.oy;
    const seg = Math.hypot(bx - ax, by - ay), n = Math.max(1, Math.ceil(seg * 1.5));
    for (let j = 0; j < n; j++) {
      const f = j / n, x = ax + (bx - ax) * f, y = ay + (by - ay) * f;
      const age = A.age + (B.age - A.age) * f, k = A.k + (B.k - A.k) * f;
      const rdx = A.dx + (B.dx - A.dx) * f, rdy = A.dy + (B.dy - A.dy) * f, rl = Math.hypot(rdx, rdy) || 1;
      const len = A.len + (B.len - A.len) * f;
      dist += seg / n;
      // fade out along the path, ease in right at the hand so the newest end isn't a hot spot
      const fade = (1 - age) ** 1.25 * (0.55 + 0.45 * smooth(0, 0.08, age)) * k;
      if (fade < 0.02) continue;
      // strands: rays of different lengths and strengths, drifting slowly
      const u = dist * (o.rays / 100), st = noise(u + t * 0.7, S), st2 = noise(u * 2.7 - t * 1.1, S + 3);
      const L = len * (0.45 + 0.75 * st) * (0.7 + 0.3 * (1 - age));
      // fine strands on top of the broad ones: the streaky curtain look
      const fine = noise(u * 7.3 + t * 0.4, S + 7);
      const strength = fade * (0.5 + 0.3 * st2 + 0.2 * fine);
      const ux = rdx / rl, uy = rdy / rl, hx = -uy, hy = ux, pal = A.pal ?? 0;
      // a short skirt behind the hem, then the ray out to its tip
      for (let s = -o.width; s <= L; s += 0.7) {
        const v = s < 0 ? 0 : s / Math.max(1, L);
        let val = (s < 0 ? 0.55 * (1 + s / o.width) : PROF[Math.round(v * 200)]) * strength;
        // posterized bands across the ribbon: a little wave in where each band starts
        val *= 0.85 + 0.15 * Math.sin(v * 9 - t * 2 + u * 0.4);
        for (let q = -o.width; q <= o.width; q++) {
          const px = Math.round(x + ux * s + hx * q * 0.5), py = Math.round(y + uy * s + hy * q * 0.5);
          if (px < 0 || py < 0 || px >= w || py >= h) continue;
          const id = py * w + px;
          // max, not sum: crossing rays don't burn out, the ribbon keeps its banding
          if (val > I[id]) { I[id] = val; U[id] = v; PI[id] = pal; }
        }
      }
    }
  }

  blur(I, BL, w, h, 3);
  blur(I, HB, w, h, 7);
  for (let y = 0; y < h; y++)
    for (let x = 0; x < w; x++) {
      const id = y * w + x, v = I[id], bl = BL[id], hb = HB[id];
      if (v < 0.03 && bl < 0.02 && hb < 0.015) continue;
      const R = ramps[PI[id]] ?? ramps[0];
      const sx = x + p.ox, sy = y + p.oy;
      // a soft halo of colored light round the curtain: light alone vanishes over bright footage, this doesn't
      if (hb > 0.015 && o.halo > 0) {
        const near = PI[id] || PI[Math.max(0, id - 3)] || PI[Math.min(w * h - 1, id + 3)];
        const HR = ramps[near] ?? ramps[0];
        // in hard steps, not a smooth fade, so even the glow reads as pixels
        const ha = clamp(hb * 2.6) * o.halo, hq = ha > 0.32 ? 0.5 : ha > 0.14 ? 0.3 : ha > 0.05 && BAY[((sy & 3) << 2) | (sx & 3)] < 0.5 ? 0.3 : 0;
        if (hq) p.blendPx(sx, sy, HR[STEPS - 2], hq);
      }
      if (v >= 0.03) {
        // bands run along the ribbon: the pale hem, then each step deeper the further up the rays the light
        // reaches, with the strands nudging steps up and down so the bands shimmer (never the darkest steps: over
        // bright footage they read as dirt)
        const u = U[id], band = (1 - u) ** 1.15 * (0.7 + 0.45 * v);
        const step = u < 0.05 && v > 0.45 ? STEPS - 1 : clamp(Math.round(band * (STEPS - 1)), o.floor, STEPS - 2);
        // up the rays the green gives way to violet, like the top of a real curtain
        const c = mix(R[step], UP[Math.min(STEPS - 1, step + 2)], clamp((u - 0.3) / 0.45) * o.violet);
        if (step === STEPS - 1) p.put(sx, sy, c, 1);
        else {
          // the body is light, not paint: see-through, more so out along the rays, the tips dithering away
          const a = clamp(v * 4) * (o.body + (1 - o.body) * (1 - u));
          if (a > 0.5 * BAY[((sy & 3) << 2) | (sx & 3)]) p.blendPx(sx, sy, c, a > 0.6 ? 0.88 : 0.62);
        }
      }
      if (bl > 0.02) p.add(sx, sy, R[Math.min(STEPS - 1, 3 + Math.floor(bl * 5))], bl * o.glow);
    }
}

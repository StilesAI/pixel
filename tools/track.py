"""Track a joint through a take with MediaPipe Pose Landmarker (video mode) and smooth it.

    .venv/bin/python tools/track.py take.mov --joint right_wrist --seconds 5 --out take.track.json --sheet take.jpg

Writes one record per frame: smoothed pixel position, raw position, visibility, speed (px/s), whether the joint
was lost, and a head box (so the trail can stay off the face). "right_wrist" is the subject's own right hand
(MediaPipe landmark 16), whatever side of the frame it's on.

Smoothing: single-frame spikes are dropped (median test), points near the frame edge need visibility 0.9, gaps up
to 6 frames are interpolated, longer gaps are marked lost, and a One Euro filter runs forward and backward and the two are averaged, so there's no lag.
"""
import argparse, json, math, sys, urllib.request
from pathlib import Path

import cv2
import numpy as np
import mediapipe as mp
from mediapipe.tasks.python import BaseOptions, vision

ROOT = Path(__file__).resolve().parent.parent
MODEL = ROOT / "models" / "pose_landmarker_full.task"
MODEL_URL = ("https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_full/float16/latest/"
             "pose_landmarker_full.task")
MAX_GAP = 6
EDGE_VIS = 0.9
JOINTS = {"nose": 0, "left_shoulder": 11, "right_shoulder": 12, "left_elbow": 13, "right_elbow": 14,
          "left_wrist": 15, "right_wrist": 16, "left_index": 19, "right_index": 20}
FACE = range(0, 11)  # nose, eyes, ears, mouth


class OneEuro:
    """One Euro filter: steady when the hand is slow, low lag when it moves fast."""

    def __init__(self, min_cutoff=1.5, beta=0.004, d_cutoff=1.0):
        self.min_cutoff, self.beta, self.d_cutoff = min_cutoff, beta, d_cutoff
        self.x = self.dx = None

    @staticmethod
    def _a(cutoff, dt):
        r = 2 * math.pi * cutoff * dt
        return r / (r + 1)

    def __call__(self, x, dt):
        if self.x is None:
            self.x, self.dx = x, np.zeros_like(x)
            return x
        dx = (x - self.x) / dt
        self.dx = self.dx + self._a(self.d_cutoff, dt) * (dx - self.dx)
        cutoff = self.min_cutoff + self.beta * np.linalg.norm(self.dx)
        self.x = self.x + self._a(cutoff, dt) * (x - self.x)
        return self.x


def ensure_model():
    if not MODEL.exists():
        MODEL.parent.mkdir(parents=True, exist_ok=True)
        print("downloading the pose model (9 MB, once)...")
        urllib.request.urlretrieve(MODEL_URL, MODEL)


def smooth(xs, ys, fps, **kw):
    """One Euro forward and backward, averaged: steady when slow, no lag when fast."""
    pts = np.stack([xs, ys], 1)
    fwd = np.array([f(p, 1 / fps) for f in [OneEuro(**kw)] for p in pts])
    bwd = np.array([f(p, 1 / fps) for f in [OneEuro(**kw)] for p in pts[::-1]])[::-1]
    return (fwd + bwd) / 2


def swap_side(joint):
    return joint.replace("right", "\0").replace("left", "right").replace("\0", "left")


def clean(raw_pts, vis, W, H, fps, min_vis):
    """Raw per-frame points -> (smoothed xy, speed px/s, sighted, lost). None if never sighted."""
    n = len(raw_pts)
    raw = np.array([r if r else [np.nan, np.nan] for r in raw_pts], float)
    # off-frame points are the model's guesses (a hand past the edge), not sightings
    inside = lambda r: -0.03 * W <= r[0] <= 1.03 * W and -0.03 * H <= r[1] <= 1.03 * H
    # near the edges a half-hidden hand gets confident-looking guesses that jump around: ask for more there
    edge = lambda r: min(r[0], W - r[0]) < 0.08 * W or min(r[1], H - r[1]) < 0.08 * H
    ok = np.array([bool(r) and v >= (EDGE_VIS if edge(r) else min_vis) and inside(r) for r, v in zip(raw_pts, vis)])
    # spike test: a point far from the median of its +-3 neighbours is a misdetection, not a fast hand
    diag = math.hypot(W, H)
    for k in np.flatnonzero(ok):
        nb = [j for j in range(max(0, k - 3), min(n, k + 4)) if j != k and ok[j]]
        if len(nb) >= 3 and np.linalg.norm(raw[k] - np.median(raw[nb], 0)) > 0.12 * diag:
            ok[k] = False
    good = np.flatnonzero(ok)
    if not len(good):
        return None, None, ok, None
    # lost = outside the first/last sighting, or inside a gap longer than MAX_GAP
    lost = np.zeros(n, bool)
    lost[:good[0]] = lost[good[-1] + 1:] = True
    for a, b in zip(good[:-1], good[1:]):
        if b - a - 1 > MAX_GAP:
            lost[a + 1:b] = True
    xs = np.interp(np.arange(n), good, raw[good, 0])
    ys = np.interp(np.arange(n), good, raw[good, 1])
    # smooth each run of tracked frames on its own, so a lost stretch doesn't drag the path
    sm = np.stack([xs, ys], 1)
    runs, k = [], 0
    while k < n:
        if lost[k]:
            k += 1
            continue
        j = k
        while j < n and not lost[j]:
            j += 1
        runs.append((k, j))
        k = j
    for a, b in runs:
        sm[a:b] = smooth(xs[a:b], ys[a:b], fps)
    speed = np.zeros(n)
    speed[1:] = np.linalg.norm(np.diff(sm, axis=0), axis=1) * fps
    speed[lost] = 0
    speed[1:][lost[:-1]] = 0
    return sm, speed, ok, lost


def track(video, joint="right_wrist", seconds=None, start=0.0, min_vis=0.5, analyze_width=960, mirrored=False):
    """mirrored: the take is a mirrored selfie (iPhone front camera with Mirror Front Camera on), so MediaPipe's
    sides are swapped; asking for right_wrist then follows the subject's real right hand."""
    cap = cv2.VideoCapture(str(video))
    if not cap.isOpened():
        sys.exit(f"can't open {video}")
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    W, H = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    cap.set(cv2.CAP_PROP_POS_MSEC, start * 1000)
    n_max = int(round(seconds * fps)) if seconds else None
    jid = JOINTS[swap_side(joint) if mirrored else joint]
    elbow = joint.replace("wrist", "elbow").replace("index", "elbow")
    eid = JOINTS[swap_side(elbow) if mirrored else elbow] if elbow in JOINTS and elbow != joint else None
    # the same joint on the other side, only to warn when it's the one actually moving (a mirrored selfie)
    other = swap_side(joint)
    oid = JOINTS[swap_side(other) if mirrored else other] if other in JOINTS and other != joint else None
    other_pts = []

    ensure_model()
    opts = vision.PoseLandmarkerOptions(
        base_options=BaseOptions(model_asset_path=str(MODEL)),
        running_mode=vision.RunningMode.VIDEO,
        num_poses=1, min_pose_detection_confidence=0.5, min_tracking_confidence=0.5)
    frames = []
    scale = min(1.0, analyze_width / max(W, H))
    with vision.PoseLandmarker.create_from_options(opts) as lm:
        i = 0
        while n_max is None or i < n_max:
            ok, bgr = cap.read()
            if not ok:
                break
            small = cv2.resize(bgr, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA) if scale < 1 else bgr
            img = mp.Image(image_format=mp.ImageFormat.SRGB, data=cv2.cvtColor(small, cv2.COLOR_BGR2RGB))
            res = lm.detect_for_video(img, int(round((start + i / fps) * 1000)))
            rec = {"i": i, "t": round(i / fps, 4), "vis": 0.0, "raw": None, "face": None,
                   "elbow_raw": None, "elbow_vis": 0.0}
            if res.pose_landmarks:
                L = res.pose_landmarks[0]
                p = L[jid]
                rec["vis"] = round(float(p.visibility or 0), 3)
                rec["raw"] = [round(p.x * W, 1), round(p.y * H, 1)]
                if eid is not None:
                    e = L[eid]
                    rec["elbow_raw"], rec["elbow_vis"] = [round(e.x * W, 1), round(e.y * H, 1)], float(e.visibility or 0)
                fx = [L[k].x * W for k in FACE]
                fy = [L[k].y * H for k in FACE]
                # landmarks only span eyes-ears-mouth; pad out to the whole head
                ew = max(fx) - min(fx)
                rec["face"] = [round(min(fx) - 0.35 * ew), round(min(fy) - 0.9 * ew),
                               round(max(fx) + 0.35 * ew), round(max(fy) + 0.55 * ew)]
                rec["shoulders_y"] = round(min(L[11].y, L[12].y) * H, 1)
                if oid is not None and (L[oid].visibility or 0) > 0.5:
                    other_pts.append((L[oid].x * W, L[oid].y * H))
            frames.append(rec)
            i += 1
    cap.release()

    sm, speed, ok, lost = clean([f["raw"] for f in frames], [f["vis"] for f in frames], W, H, fps, min_vis)
    if sm is None:
        sys.exit(f"never found {joint} with visibility >= {min_vis}")
    motion = float(np.median(speed[~lost])) if (~lost).any() else 0.0
    op = np.array(other_pts) if len(other_pts) > 2 else None
    other_motion = float(np.median(np.linalg.norm(np.diff(op, axis=0), axis=1)) * fps) if op is not None else None
    for k, f in enumerate(frames):
        f["xy"] = [round(float(sm[k, 0]), 1), round(float(sm[k, 1]), 1)]
        f["speed"] = round(float(speed[k]), 1)
        f["filled"] = bool(not ok[k] and not lost[k])
        f["lost"] = bool(lost[k])
    # the elbow on the same side, cleaned the same way, so effects can run down the forearm
    if eid is not None:
        esm, _, _, elost = clean([f.pop("elbow_raw") for f in frames], [f.pop("elbow_vis") for f in frames],
                                 W, H, fps, min_vis)
        for k, f in enumerate(frames):
            f["elbow"] = None if esm is None or elost[k] else [round(float(esm[k, 0]), 1), round(float(esm[k, 1]), 1)]
    return {"video": str(video), "joint": joint, "mirrored": mirrored, "motion": motion, "other_motion": other_motion,
            "fps": fps, "size": [W, H], "start": start, "frames": frames}


def debug_video(data, out, trail=0.5):
    """The take with the tracked joint drawn on it, full size: electric blue dot and its last `trail` seconds of
    path, nothing where it's lost. For the "finds my wrist" card."""
    import subprocess
    cap = cv2.VideoCapture(data["video"])
    cap.set(cv2.CAP_PROP_POS_MSEC, data["start"] * 1000)
    W, H = data["size"]
    fps, fr = data["fps"], data["frames"]
    ff = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{W}x{H}",
                           "-r", str(fps), "-i", "-", "-c:v", "libx264", "-crf", "18", "-pix_fmt", "yuv420p",
                           str(out)], stdin=subprocess.PIPE)
    BLUE, r = (255, 61, 31), max(6, W // 90)
    for k, f in enumerate(fr):
        ok, img = cap.read()
        if not ok:
            break
        tail = [p for p in fr[max(0, k - int(fps * trail)):k + 1] if not p["lost"]]
        if len(tail) > 1:
            pts = np.array([p["xy"] for p in tail], np.int32)
            cv2.polylines(img, [pts], False, BLUE, max(3, r // 2), cv2.LINE_AA)
        if not f["lost"]:
            c = (int(f["xy"][0]), int(f["xy"][1]))
            cv2.circle(img, c, r, BLUE, -1, cv2.LINE_AA)
            cv2.circle(img, c, r, (255, 255, 255), max(2, r // 4), cv2.LINE_AA)
        ff.stdin.write(img.tobytes())
    ff.stdin.close()
    ff.wait()
    cap.release()


def contact_sheet(data, out, cols=4, rows=3, thumb_w=360):
    """Grid of evenly spaced frames: blue dot + path = smoothed (last 0.5 s), red ring = raw detection,
    white box = head. Label: frame, time, visibility, speed, FILL (interpolated) or LOST."""
    cap = cv2.VideoCapture(data["video"])
    fr, fps = data["frames"], data["fps"]
    picks = np.linspace(0, len(fr) - 1, cols * rows).astype(int)
    W, H = data["size"]
    s = thumb_w / W
    th = int(H * s)
    sheet = np.full((rows * (th + 4) + 4, cols * (thumb_w + 4) + 4, 3), 255, np.uint8)
    for n, k in enumerate(picks):
        cap.set(cv2.CAP_PROP_POS_MSEC, (data["start"] + k / fps) * 1000)
        ok, img = cap.read()
        if not ok:
            continue
        img = cv2.resize(img, (thumb_w, th), interpolation=cv2.INTER_AREA)
        f = fr[k]
        if f["face"]:
            x0, y0, x1, y1 = (int(v * s) for v in f["face"])
            cv2.rectangle(img, (x0, y0), (x1, y1), (255, 255, 255), 1)
        BLUE = (255, 61, 31)  # #1f3dff in BGR
        tail = [p for p in fr[max(0, k - int(fps * 0.5)):k + 1] if not p["lost"]]
        if len(tail) > 1:
            pts = np.array([[p["xy"][0] * s, p["xy"][1] * s] for p in tail], np.int32)
            cv2.polylines(img, [pts], False, BLUE, 2, cv2.LINE_AA)
        if f["raw"]:
            cv2.circle(img, (int(f["raw"][0] * s), int(f["raw"][1] * s)), 7, (40, 40, 230), 1, cv2.LINE_AA)
        if not f["lost"]:
            cv2.circle(img, (int(f["xy"][0] * s), int(f["xy"][1] * s)), 5, BLUE, -1, cv2.LINE_AA)
            cv2.circle(img, (int(f["xy"][0] * s), int(f["xy"][1] * s)), 5, (255, 255, 255), 1, cv2.LINE_AA)
        label = f"#{k} {f['t']:.2f}s v={f['vis']:.2f} {int(f['speed'])}px/s" + (
            " LOST" if f["lost"] else " FILL" if f["filled"] else "")
        cv2.rectangle(img, (0, 0), (thumb_w, 18), (0, 0, 0), -1)
        cv2.putText(img, label, (4, 13), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1, cv2.LINE_AA)
        r, c = divmod(n, cols)
        y, x = 4 + r * (th + 4), 4 + c * (thumb_w + 4)
        sheet[y:y + th, x:x + thumb_w] = img
    cap.release()
    cv2.imwrite(str(out), sheet, [cv2.IMWRITE_JPEG_QUALITY, 88])


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("video")
    ap.add_argument("--joint", default="right_wrist", choices=JOINTS)
    ap.add_argument("--start", type=float, default=0.0)
    ap.add_argument("--seconds", type=float)
    ap.add_argument("--out")
    ap.add_argument("--sheet")
    ap.add_argument("--mirrored", action="store_true", help="the take is a mirrored selfie: swap left and right")
    a = ap.parse_args()
    d = track(a.video, a.joint, a.seconds, a.start, mirrored=a.mirrored)
    out = a.out or str(Path(a.video).with_suffix(".track.json"))
    Path(out).write_text(json.dumps(d))
    fr = d["frames"]
    print(f"{len(fr)} frames @ {d['fps']:.2f} fps, {d['size'][0]}x{d['size'][1]}; "
          f"tracked {sum(not f['filled'] and not f['lost'] for f in fr)}, filled {sum(f['filled'] for f in fr)}, "
          f"lost {sum(f['lost'] for f in fr)}; max speed {max(f['speed'] for f in fr):.0f} px/s -> {out}")
    if a.sheet:
        contact_sheet(d, a.sheet)
        print("sheet ->", a.sheet)

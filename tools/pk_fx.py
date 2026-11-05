"""pk fx: put a pixelfx effect on a real take, pinned to a joint, in one command.

    pk fx aurora-ribbon --take take.mov --joint right_wrist
    pk fx aurora-ribbon --take take.mov --joint right_wrist --mirrored --seconds 5 --debug
    pk fx fire/spirit-flame --take take.mov --joint right_wrist --palette blue
    pk fx aurora-ribbon --take take.mov --joint right_wrist --palette-at "20.16:blue,22.32:aurora"

1. tracks the joint (tools/track.py, MediaPipe Pose, cached next to the output)
2. renders the effect along it (tools/fx_follow.mjs, which imports pixelfx from your clone)
3. composites onto the take with ffmpeg: the color pass laid over normally, the glow pass added on top

aurora-ribbon lives in this kit (fx/); every other effect id comes from your pixelfx clone. Both draw with pixelfx by
Patch (github.com/patch-gg/pixelfx, MIT), method by Hugo Duprez. Credit them when you post: "pixelfx by Patch, method
by Hugo Duprez".
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

KIT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KIT / "tools"))


def _run(cmd, **kw):
    r = subprocess.run(cmd, **kw)
    if r.returncode:
        sys.exit(f"failed: {' '.join(map(str, cmd[:3]))}...")


def add_parser(sub):
    f = sub.add_parser("fx", help="pin a pixelfx effect to a joint in a real take")
    f.add_argument("effect", help="aurora-ribbon (in this kit's fx/), or any pixelfx effect id, e.g. fire/spirit-flame (see pixelfx docs/CATALOG.md)")
    f.add_argument("--take", required=True, help="the video to put it on")
    f.add_argument("--joint", default="right_wrist")
    f.add_argument("--mirrored", action="store_true", help="the take is a mirrored selfie: swap left and right")
    f.add_argument("--start", type=float, default=0.0, help="start this many seconds in")
    f.add_argument("--seconds", type=float, help="only this many seconds (try 5 first)")
    f.add_argument("--palette", default="aurora", help='aurora | blue | "#hex,#hex,..." dark to bright')
    f.add_argument("--palette-at", help='palette changes in take time, e.g. "20.16:blue,22.32:aurora"')
    f.add_argument("--scale", type=int, help="output pixels per effect pixel (default 7)")
    f.add_argument("--life", type=float, help="trail length in seconds")
    f.add_argument("--arm", type=float, help="how far down the forearm it reaches")
    f.add_argument("--glow", type=float, help="glow strength (default 1)")
    f.add_argument("--pixelfx", help="path to your pixelfx clone (default: ../pixelfx next to this kit)")
    f.add_argument("--out", help="output video (default out/<take>_<effect>.mp4)")
    f.add_argument("--debug", action="store_true", help="also write the wrist-track render (blue dot and path)")
    f.add_argument("--sheet", action="store_true", help="also write a 12-frame contact sheet of the result")
    f.add_argument("--retrack", action="store_true", help="ignore the cached track")
    f.set_defaults(fn=cmd_fx)


def cmd_fx(a):
    take = Path(a.take).resolve()
    if not take.exists():
        sys.exit(f"no take at {take}")
    if not shutil.which("ffmpeg") or not shutil.which("node"):
        sys.exit("pk fx needs ffmpeg and node on your PATH")
    name = f"{take.stem}_{a.effect.replace('/', '-')}"
    out = Path(a.out).resolve() if a.out else (KIT / "out" / f"{name}.mp4")
    work = out.with_suffix("")
    work = work.parent / (work.name + "_work")
    work.mkdir(parents=True, exist_ok=True)

    # 1. track (cached on the take, the range and the joint)
    key = hashlib.sha1(json.dumps([str(take), take.stat().st_mtime, a.start, a.seconds, a.joint, a.mirrored]).encode())
    tpath = work / f"track_{key.hexdigest()[:10]}.json"
    import track as T
    if a.retrack or not tpath.exists():
        print(f"  tracking {a.joint} in {take.name}...")
        d = T.track(take, a.joint, a.seconds, a.start, mirrored=a.mirrored)
        tpath.write_text(json.dumps(d))
    else:
        d = json.loads(tpath.read_text())
    fr = d["frames"]
    print(f"  track: {len(fr)} frames, {sum(not f['lost'] for f in fr)} with the {a.joint}"
          + (", elbow too" if any(f.get("elbow") for f in fr) else ""))
    if d.get("other_motion") and d.get("motion") is not None and d["motion"] < 0.4 * d["other_motion"]:
        print(f"  heads up: the other {a.joint.split('_')[1]} moves {d['other_motion'] / max(1, d['motion']):.1f}x more. "
              f"If the take is a mirrored selfie, add --mirrored.")

    # 2. render the effect along it
    passes = work / "passes"
    cmd = ["node", str(KIT / "tools" / "fx_follow.mjs"), a.effect, "--track", str(tpath), "--out", str(passes),
           "--palette", a.palette]
    for flag, v in [("--palette-at", a.palette_at), ("--scale", a.scale), ("--life", a.life), ("--arm", a.arm),
                    ("--glow", a.glow), ("--pixelfx", a.pixelfx)]:
        if v is not None:
            cmd += [flag, str(v)]
    _run(cmd)

    # 3. composite: color normally, glow added
    trim = ["-ss", str(a.start)] + (["-t", str(a.seconds)] if a.seconds else [])
    graph = ("[0:v]format=gbrp[t];[1:v]format=gbrap[c];[t][c]overlay=format=rgb,format=gbrp[tc];"
             "[2:v]format=gbrp[l];[tc][l]blend=all_mode=addition,format=yuv420p[v]")
    _run(["ffmpeg", "-v", "error", "-y", *trim, "-i", str(take), "-i", str(passes / "color.mov"),
          "-i", str(passes / "light.mov"), "-filter_complex", graph, "-map", "[v]", "-map", "0:a?",
          "-c:v", "libx264", "-crf", "16", "-preset", "medium", "-colorspace", "bt709", "-color_primaries", "bt709",
          "-color_trc", "bt709", "-movflags", "+faststart", "-c:a", "aac", "-b:a", "192k", "-shortest", str(out)])
    print(f"  wrote {out}")

    if a.debug:
        dbg = out.with_name(out.stem + "_wrist-track.mp4")
        T.debug_video(d, dbg)
        print(f"  wrote {dbg}")
    if a.sheet:
        sheet = out.with_name(out.stem + "_sheet.jpg")
        n = len(fr)
        picks = "+".join(f"eq(n\\,{round(i * (n - 3) / 11)})" for i in range(12))
        _run(["ffmpeg", "-v", "error", "-y", "-i", str(out), "-vf",
              f"select='{picks}',scale=330:-2,pad=iw+4:ih+4:2:2:white,tile=6x2", "-frames:v", "1", "-q:v", "3",
              str(sheet)])
        print(f"  wrote {sheet}")
    print("  credit: pixelfx by Patch (github.com/patch-gg/pixelfx), method by Hugo Duprez")

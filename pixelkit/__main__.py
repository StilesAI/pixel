"""Command line.

  python -m pixelkit render scenes/foo.py                 -> out/foo.mp4
  python -m pixelkit render scenes/foo.py --sheet         -> out/foo_sheet.png (8 frames, fast)
  python -m pixelkit render scenes/foo.py --still 2.5     -> out/foo_2.50s.png
  python -m pixelkit render scenes/foo.py --gif
  python -m pixelkit render scenes/foo.py --palette ember
  python -m pixelkit render scenes/foo.py --hue "#1f3dff" -> one-hue version
  python -m pixelkit render scenes/foo.py --mono          -> black and white
  python -m pixelkit render scenes/foo.py --colors "#0b0b0f,#3a3d4a,#ff5a1f,#f4efe6"
  python -m pixelkit render scenes/foo.py --all-modes     -> one video per color mode
  python -m pixelkit new explainer scenes/my_scene.py     -> copy a template
  python -m pixelkit palettes                             -> out/palettes.png
  python -m pixelkit sprites                              -> out/sprites.png
  python -m pixelkit doctor                               -> check the install
"""
from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _pal(args, scene):
    from .palette import resolve_palette
    colors = [c.strip() for c in args.colors.split(",")] if args.colors else None
    return resolve_palette(args.palette or scene.palette, hue=args.hue, mono=args.mono, colors=colors)


def cmd_render(args):
    from .render import contact_sheet, load_scene, render_gif, render_still, render_video
    scene = load_scene(args.scene)
    if args.duration:
        scene.duration = args.duration
    stem = Path(args.scene).stem
    out_dir = Path(args.out or "out")
    out_dir.mkdir(parents=True, exist_ok=True)
    suffix = ""
    if args.hue:
        suffix = "_hue-" + args.hue.lstrip("#")
    elif args.mono:
        suffix = "_mono"
    elif args.colors:
        suffix = "_custom"
    elif args.palette:
        suffix = "_" + Path(args.palette).stem

    if args.all_modes:
        from .palette import Palette
        base = Palette.load(args.palette or scene.palette)
        modes = [("", base), ("_hue-" + args.accent.lstrip("#"), base.one_hue(args.accent)),
                 ("_mono", base.mono())]
        for sfx, pal in modes:
            render_video(scene, out_dir / f"{stem}{sfx}.mp4", pal, best=args.best)
        return

    pal = _pal(args, scene)
    if args.sheet:
        p = contact_sheet(scene, str(out_dir / f"{stem}{suffix}_sheet.png"), n=args.frames, palette=pal)
        print(f"  wrote {p}")
    if args.still is not None:
        p = render_still(scene, args.still, str(out_dir / f"{stem}{suffix}_{args.still:.2f}s.png"), pal)
        print(f"  wrote {p}")
    if args.gif:
        p = render_gif(scene, str(out_dir / f"{stem}{suffix}.gif"), pal)
        print(f"  wrote {p}")
    if not (args.sheet or args.still is not None or args.gif) or args.video:
        render_video(scene, out_dir / f"{stem}{suffix}.mp4", pal, best=args.best)


def cmd_new(args):
    src = ROOT / "templates" / f"{args.template}.py"
    if not src.exists():
        names = ", ".join(sorted(p.stem for p in (ROOT / "templates").glob("*.py")))
        sys.exit(f"no template '{args.template}'. Templates: {names}")
    dst = Path(args.dest)
    if dst.exists():
        sys.exit(f"{dst} already exists")
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(src, dst)
    print(f"  created {dst} from {args.template}")


def cmd_palettes(args):
    from .render import palette_sheet
    out = Path(args.out or "out") / "palettes.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    palette_sheet(str(out))
    print(f"  wrote {out}")


def cmd_sprites(args):
    from PIL import Image, ImageDraw
    from .palette import Palette
    from .sprite import available, load
    pal = Palette.load(args.palette or "night")
    names = available()
    tiles = []
    for n in names:
        sh = load(n)
        frames = [f.to_image(pal, 4) for f in sh.frames[:4]]
        w = sum(f.size[0] for f in frames) + 4 * (len(frames) - 1)
        h = max(f.size[1] for f in frames)
        tile = Image.new("RGB", (max(w, 90), h + 16), tuple(pal.rgb[0]))
        x = 0
        for f in frames:
            tile.paste(f, (x, 16))
            x += f.size[0] + 4
        ImageDraw.Draw(tile).text((0, 2), n, fill=(230, 230, 230))
        tiles.append(tile)
    cols = 4
    cw = max(t.size[0] for t in tiles) + 12
    rh = max(t.size[1] for t in tiles) + 12
    rows = (len(tiles) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * cw + 12, rows * rh + 12), tuple(pal.rgb[0]))
    for i, t in enumerate(tiles):
        sheet.paste(t, (12 + (i % cols) * cw, 12 + (i // cols) * rh))
    out = Path(args.out or "out") / "sprites.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out)
    print(f"  wrote {out}")


def cmd_doctor(args):
    ok = True
    print(f"  python {sys.version.split()[0]}")
    for mod in ("numpy", "PIL"):
        try:
            m = __import__(mod)
            print(f"  {mod} {getattr(m, '__version__', '')} ok")
        except ImportError:
            ok = False
            print(f"  {mod} MISSING  ->  pip install -r requirements.txt")
    try:
        from .render import _ffmpeg
        print(f"  ffmpeg ok ({_ffmpeg()})")
    except RuntimeError as e:
        ok = False
        print(f"  {e}")
    print("  ready" if ok else "  not ready yet")


def main(argv=None):
    p = argparse.ArgumentParser(prog="pixelkit")
    sub = p.add_subparsers(dest="cmd", required=True)

    r = sub.add_parser("render")
    r.add_argument("scene")
    r.add_argument("--out")
    r.add_argument("--palette")
    r.add_argument("--hue")
    r.add_argument("--mono", action="store_true")
    r.add_argument("--colors")
    r.add_argument("--all-modes", action="store_true")
    r.add_argument("--accent", default="#1f3dff", help="hue used by --all-modes")
    r.add_argument("--sheet", action="store_true")
    r.add_argument("--frames", type=int, default=8)
    r.add_argument("--still", type=float)
    r.add_argument("--gif", action="store_true")
    r.add_argument("--video", action="store_true", help="also render video with --sheet/--still")
    r.add_argument("--duration", type=float)
    r.add_argument("--best", action="store_true", help="slower encode, smaller file")
    r.set_defaults(fn=cmd_render)

    n = sub.add_parser("new")
    n.add_argument("template")
    n.add_argument("dest")
    n.set_defaults(fn=cmd_new)

    pl = sub.add_parser("palettes")
    pl.add_argument("--out")
    pl.set_defaults(fn=cmd_palettes)

    sp = sub.add_parser("sprites")
    sp.add_argument("--out")
    sp.add_argument("--palette")
    sp.set_defaults(fn=cmd_sprites)

    d = sub.add_parser("doctor")
    d.set_defaults(fn=cmd_doctor)

    args = p.parse_args(argv)
    args.fn(args)


if __name__ == "__main__":
    main()

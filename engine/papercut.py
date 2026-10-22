"""papercut: one story.json in, one stop-motion paper-collage documentary out. Free, local, no credits.

  python papercut.py search "Apollo 13" sheet.png      find public-domain photos (prints + contact sheet)
  python papercut.py make story.json                   images -> cutouts -> voice -> timings -> animation -> sound
  python papercut.py make story.json --render          ...and render the MP4
  python papercut.py snap story.json 3.2,7.5           stills at those seconds, to check a frame before rendering
"""
import hashlib
import json
import os
import shutil
import subprocess
import sys

import numpy as np
import soundfile as sf
from scipy.signal import resample_poly

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import build  # noqa: E402
import fetch  # noqa: E402
import sfx  # noqa: E402
import voice  # noqa: E402
from cutout import cut_piece  # noqa: E402

NPX = shutil.which("npx") or "npx"


def _h(o):
    return hashlib.sha1(json.dumps(o, sort_keys=True).encode()).hexdigest()[:10]


def load(path):
    story = json.load(open(path, encoding="utf-8"))
    root = os.path.dirname(os.path.abspath(path))
    proj = os.path.join(root, story.get("project", "project"))
    return story, root, proj


def images(story, root, proj):
    src_dir = os.path.join(root, "sources")
    out_dir = os.path.join(proj, "assets", "img")
    os.makedirs(src_dir, exist_ok=True)
    os.makedirs(out_dir, exist_ok=True)
    credits = os.path.join(root, "CREDITS.txt")
    done = {}
    for key, spec in story.get("images", {}).items():
        if isinstance(spec, str):
            spec = {"commons": spec}
        if "file" in spec:
            raw = os.path.join(root, spec["file"])
        else:
            ext = os.path.splitext(spec["commons"])[1].lower()
            ext = ".jpg" if ext in (".tif", ".tiff", ".webp", ".svg") else ext
            raw = os.path.join(src_dir, key + ext)
            if not os.path.exists(raw):
                fetch.get(spec["commons"], raw, credits=credits, allow_by=spec.get("allow_by", False))
        params = {k: spec.get(k) for k in ("cut", "accent", "size", "contrast", "crop", "dots")}
        tag = _h([params, os.path.getsize(raw)])
        out = os.path.join(out_dir, f"{key}-{tag}.png")
        if not os.path.exists(out):
            src = raw
            if spec.get("crop"):  # [l, t, r, b] as fractions, to frame a face or an object before cutting
                from PIL import Image
                im = Image.open(raw).convert("RGB")
                l, t, r, b = spec["crop"]
                im = im.crop((int(l * im.width), int(t * im.height), int(r * im.width), int(b * im.height)))
                src = os.path.join(src_dir, key + "-crop.png")
                im.save(src)
            piece = cut_piece(src, size=spec.get("size", 1000), cut=spec.get("cut", True),
                              accent=spec.get("accent", "red"), contrast=spec.get("contrast", 1.1), seed=len(key),
                              dots=spec.get("dots", True))
            piece.save(out)
            print("  piece", key)
        done[key] = os.path.relpath(out, proj).replace("\\", "/")
    # one sheet of every cut-out, so a bad cut is caught before it reaches a scene
    from PIL import Image
    tiles = []
    for key, rel in done.items():
        im = Image.open(os.path.join(proj, rel))
        im.thumbnail((360, 420))
        t = Image.new("RGBA", (380, 440), (90, 110, 110, 255))
        t.alpha_composite(im, ((380 - im.width) // 2, (440 - im.height) // 2))
        tiles.append(t)
    if tiles:
        cols = 4
        sheet = Image.new("RGB", (380 * cols, 440 * ((len(tiles) + cols - 1) // cols)), (60, 60, 60))
        for i, t in enumerate(tiles):
            sheet.paste(t.convert("RGB"), ((i % cols) * 380, (i // cols) * 440))
        sheet.save(os.path.join(root, "pieces.jpg"), quality=85)
    return done


def narrate(story, proj):
    ad = os.path.join(proj, "assets", "audio")
    os.makedirs(ad, exist_ok=True)
    key = _h([[b["say"] for b in story["beats"]], story.get("voice", "af_heart"), story.get("speed", 1.0)])
    cache = os.path.join(ad, "timing.json")
    if os.path.exists(cache):
        c = json.load(open(cache))
        if c.get("key") == key:
            return c["timing"], c["words"], c["total"]
    vo, timing, total = voice.synth(story["beats"], ad, story.get("voice", "af_heart"), story.get("speed", 1.0),
                                    lang=story.get("lang", "en-us"))
    words = voice.words(vo, story["beats"], timing)
    json.dump({"key": key, "timing": timing, "words": words, "total": total}, open(cache, "w"), indent=1)
    print(f"  voice {total:.1f}s, {len(timing)} beats")
    return timing, words, total


def mix(story, proj, events, total):
    ad = os.path.join(proj, "assets", "audio")
    vo, sr = sf.read(os.path.join(ad, "vo.wav"), dtype="float32")
    vo = resample_poly(vo, 2, 1) if sr == 24000 else vo
    n = int((total + 0.5) * sfx.SR)
    out = np.zeros(n, np.float32)
    out[: min(n, len(vo))] += vo[:n]
    fx = sfx.make_events(events, total)[:n]
    out[: len(fx)] += fx * story.get("sfx_gain", 0.32)
    if story.get("music", "bed") == "bed":
        bd = sfx.bed(total, bpm=story.get("bpm", 72))[:n]
        out[: len(bd)] += bd * story.get("music_gain", 0.22)
    elif story.get("music") not in (None, "none"):
        m, msr = sf.read(os.path.join(os.path.dirname(proj), story["music"]), dtype="float32")
        if m.ndim > 1:
            m = m.mean(1)
        if msr != sfx.SR:
            m = resample_poly(m, sfx.SR, msr)
        m = m[:n]
        out[: len(m)] += m * story.get("music_gain", 0.12)
    raw = os.path.join(ad, "mix_raw.wav")
    sf.write(raw, out / (np.max(np.abs(out)) or 1) * 0.7, sfx.SR)
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", raw, "-af",
                    "loudnorm=I=-14:TP=-1.5:LRA=9,alimiter=limit=0.84:level=0", "-ar", "48000",
                    os.path.join(ad, "mix.wav")], check=True)


def make(path, render=False):
    story, root, proj = load(path)
    os.makedirs(proj, exist_ok=True)
    print("images")
    imgs = images(story, root, proj)
    print("voice")
    timing, words, total = narrate(story, proj)
    print("animation")
    events = build.write_project(story, timing, words, total, proj, imgs)
    print("sound")
    mix(story, proj, events, total)
    r = subprocess.run([NPX, "hyperframes", "check", proj], capture_output=True, text=True, encoding="utf-8", errors="replace")
    errs = [ln.strip() for ln in (r.stdout + r.stderr).splitlines() if ln.strip().startswith("✗")]
    print(f"check: {len(errs)} errors")
    for e in errs[:10]:
        print("  ", e[:220])
    if render:
        out = os.path.join(root, story.get("slug", "video") + ".mp4")
        subprocess.run([NPX, "hyperframes", "render", proj, "-o", out, "-q", "delivery", "--quiet"], check=True)
        print("rendered", out)
    return proj


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    cmd = sys.argv[1]
    if cmd == "make":
        make(sys.argv[2], render="--render" in sys.argv)
    elif cmd == "search":
        c = fetch.search(sys.argv[2], allow_by="--allow-by" in sys.argv)
        for i, x in enumerate(c, 1):
            print(f"{i:2d}. {x['title']}  [{x['license']}]  {x['w']}x{x['h']}")
        if len(sys.argv) > 3 and not sys.argv[3].startswith("--"):
            fetch.contact_sheet(c, sys.argv[3])
            print("sheet:", sys.argv[3])
    elif cmd == "snap":
        story, root, proj = load(sys.argv[2])
        out = os.path.join(root, "snaps")
        subprocess.run([NPX, "hyperframes", "snapshot", proj, "--at", sys.argv[3], "-o", out, "--no-end"], check=True)
        print(out)

"""papercut: one story.json in, one stop-motion paper-collage documentary out. Free, local, no credits.

  python papercut.py search "Apollo 13" sheet.png      find public-domain photos (prints + contact sheet)
  python papercut.py make story.json                   images -> cutouts -> voice -> timings -> animation -> sound
  python papercut.py make story.json --render          ...and render the MP4 (add --check for HyperFrames' lint only)
  python papercut.py sheet story.json                  one still near the end of every beat -> snaps/ (+ contact-sheet-N.jpg)
  python papercut.py snap story.json 3.2,7.5           stills at those seconds -> snaps-at/ (the sheet's stills are kept)
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
                # "px": how wide to download (Wikimedia serves 1280 / 1920 / 2560 / 3840). Ask for more when a photo
                # is cropped hard or printed full frame.
                fetch.get(spec["commons"], raw, credits=credits, allow_by=spec.get("allow_by", False), width=spec.get("px", 1920))
        params = {k: spec.get(k) for k in ("cut", "accent", "size", "contrast", "crop", "dots", "cell", "color")} | {"v": 2}
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
                              dots=spec.get("dots", False), cell=spec.get("cell"), color=spec.get("color", False))
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
    take = story.get("voice_file")
    take = os.path.join(os.path.dirname(proj), take) if take else None
    key = _h([[b["say"] for b in story["beats"]], story.get("voice", "af_heart"), story.get("speed", 1.0),
              [take, os.path.getsize(take), os.path.getmtime(take)] if take else None])
    cache = os.path.join(ad, "timing.json")
    if os.path.exists(cache):
        c = json.load(open(cache))
        if c.get("key") == key:
            return c["timing"], c["words"], c["total"]
    if take:
        # a real narration take (your own voice, or any voice tool you like) instead of the built-in Kokoro voice
        vo, timing, total = voice.from_take(take, story["beats"], ad, lang=story.get("lang", "en-us")[:2])
    else:
        vo, timing, total = voice.synth(story["beats"], ad, story.get("voice", "af_heart"), story.get("speed", 1.0),
                                        lang=story.get("lang", "en-us"))
    words = voice.words(vo, story["beats"], timing, lang=story.get("lang", "en-us")[:2])
    json.dump({"key": key, "timing": timing, "words": words, "total": total}, open(cache, "w"), indent=1)
    print(f"  voice {total:.1f}s, {len(timing)} beats")
    return timing, words, total


# Music that ships with the engine: Kevin MacLeod (incompetech.com), CC BY 4.0. The credit is written to CREDITS.txt.
MUSIC = {
    "investigations": ("investigations.ogg", "Investigations"),
    "sneaky-snitch": ("sneaky-snitch.ogg", "Sneaky Snitch"),
    "dark-fog": ("dark-fog.ogg", "Dark Fog"),
}


def mix(story, proj, events, total, timing=None):
    ad = os.path.join(proj, "assets", "audio")
    root = os.path.dirname(proj)
    vo, sr = sf.read(os.path.join(ad, "vo.wav"), dtype="float32")
    if vo.ndim > 1:
        vo = vo.mean(1)
    if sr != sfx.SR:
        vo = resample_poly(vo, sfx.SR, sr).astype(np.float32)
    n = int((total + 0.5) * sfx.SR)
    out = np.zeros(n, np.float32)
    out[: min(n, len(vo))] += vo[:n]
    voice = out.copy()
    # foley: recorded paper and card handling (v2, default) or the old synthesised set ("foley": "v1")
    fx = (sfx.make_events(events, total) if story.get("foley") == "v1" else sfx.make_events_v2(events, total))[:n]
    out[: len(fx)] += fx * story.get("sfx_gain", 0.5)
    music = story.get("music", "investigations")
    if music == "bed":
        bd = sfx.bed(total, bpm=story.get("bpm", 72))[:n]
        out[: len(bd)] += bd * story.get("music_gain", 0.22)
    elif music not in (None, "none"):
        if music in MUSIC:
            path = os.path.join(HERE, "music", MUSIC[music][0])
            line = (f'"{MUSIC[music][1]}" Kevin MacLeod (incompetech.com). '
                    f"Licensed under Creative Commons: By Attribution 4.0. http://creativecommons.org/licenses/by/4.0/")
            cred = os.path.join(root, "CREDITS.txt")
            old = open(cred, encoding="utf-8").read() if os.path.exists(cred) else ""
            if line not in old:
                open(cred, "a", encoding="utf-8").write(("\n" if old and not old.endswith("\n") else "") + "music: " + line + "\n")
        else:
            path = os.path.join(root, music)
        # a stop-down before every beat marked "drop": the music cuts out for a breath, then the line lands
        cuts = [tm["start"] for b, tm in zip(story["beats"], timing or []) if b.get("drop")]
        m = sfx.music_track(path, total, cuts=cuts, start=story.get("music_start", 0.0))[:n]
        m = sfx.duck(m, voice, depth_db=story.get("duck_db", -8.0))
        out[: len(m)] += m * story.get("music_gain", 0.16)
        for c in cuts:  # the hit that the stop-down sets up
            for kind, g in (("sub", 0.75), ("heavy", 0.35)):
                x = sfx._take(kind, np.random.default_rng(int(c * 100)), {})
                if x is not None:
                    s = int(c * sfx.SR)
                    e = min(n, s + len(x))
                    out[s:e] += x[: e - s] * g * story.get("sfx_gain", 0.5)
    raw = os.path.join(ad, "mix_raw.wav")
    sf.write(raw, out / (np.max(np.abs(out)) or 1) * 0.7, sfx.SR)
    # One static gain to the target loudness, then a limiter for the few peaks that would clip. No gain riding, so
    # the voice is never pumped up and down. A second pass corrects the little the limiter took off.
    target = story.get("lufs", -14)
    final = os.path.join(ad, "mix.wav")
    gain = target - (_lufs(raw) or target)
    for _ in range(3):
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", raw, "-af", f"volume={gain:.2f}dB,alimiter=limit=0.84:level=0",
                        "-ar", "48000", final], check=True)
        got = _lufs(final)
        if got is None or abs(got - target) < 0.3:
            break
        gain += target - got


def _lufs(path):
    """Integrated loudness of a file (EBU R128), or None if ffmpeg could not read it."""
    r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", path, "-af", "ebur128", "-f", "null", "-"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    vals = [ln.split()[1] for ln in r.stderr.splitlines() if ln.strip().startswith("I:") and "LUFS" in ln]
    try:
        return float(vals[-1])
    except (IndexError, ValueError):
        return None


def make(path, render=False, check=False):
    story, root, proj = load(path)
    os.makedirs(proj, exist_ok=True)
    print("images")
    imgs = images(story, root, proj)
    print("voice")
    timing, words, total = narrate(story, proj)
    print("animation")
    events = build.write_project(story, timing, words, total, proj, imgs)
    print("sound")
    mix(story, proj, events, total, timing)
    if check or render:
        # HyperFrames' own lint. "text_occluded" fires for every piece that has not entered yet and for the light
        # layer, so it is counted apart: anything else is a real problem.
        r = subprocess.run([NPX, "hyperframes", "check", proj], capture_output=True, text=True, encoding="utf-8", errors="replace")
        errs = [ln.strip() for ln in (r.stdout + r.stderr).splitlines() if ln.strip().startswith("✗")]
        real = [e for e in errs if "text_occluded" not in e]
        print(f"check: {len(real)} errors ({len(errs) - len(real)} known false alarms hidden)")
        for e in real[:20]:
            print("  ", e[:220])
    if render:
        out = os.path.join(root, story.get("slug", "video") + ".mp4")
        subprocess.run([NPX, "hyperframes", "render", proj, "-o", out, "-q", "delivery", "--quiet"], check=True)
        # the renderer re-levels the sound (about 3 dB hot), so the finished mix is laid back in untouched
        tmp = out + ".a.mp4"
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", out, "-i", os.path.join(proj, "assets", "audio", "mix.wav"),
                        "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-b:a", "256k", "-shortest",
                        "-movflags", "+faststart", tmp], check=True)
        os.replace(tmp, out)
        print("rendered", out, f"({_lufs(out)} LUFS)")
    return proj


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    cmd = sys.argv[1]
    if cmd == "make":
        make(sys.argv[2], render="--render" in sys.argv, check="--check" in sys.argv)
    elif cmd == "search":
        c = fetch.search(sys.argv[2], allow_by="--allow-by" in sys.argv)
        for i, x in enumerate(c, 1):
            print(f"{i:2d}. {x['title']}  [{x['license']}]  {x['w']}x{x['h']}")
        if len(sys.argv) > 3 and not sys.argv[3].startswith("--"):
            fetch.contact_sheet(c, sys.argv[3])
            if c:
                print("sheet:", sys.argv[3])
    elif cmd == "sheet":
        story, root, proj = load(sys.argv[2])
        c = json.load(open(os.path.join(proj, "assets", "audio", "timing.json")))
        tm, total = c["timing"], c["total"]
        ats = []
        for k, x in enumerate(tm):
            end = tm[k + 1]["start"] if k + 1 < len(tm) else total
            last = k + 1 == len(tm)
            ats.append(round(max(x["start"] + 0.3, end - (0.12 if last else 0.4)), 2))  # the last pose before the next paper wipe
        out = os.path.join(root, "snaps")
        subprocess.run([NPX, "hyperframes", "snapshot", proj, "--at", ",".join(str(a) for a in ats), "-o", out, "--no-end"], check=True)
        print(out)
    elif cmd == "snap":
        story, root, proj = load(sys.argv[2])
        out = os.path.join(root, "snaps-at")  # its own folder: a quick check must not wipe the per-beat sheet
        subprocess.run([NPX, "hyperframes", "snapshot", proj, "--at", sys.argv[3], "-o", out, "--no-end"], check=True)
        print(out)

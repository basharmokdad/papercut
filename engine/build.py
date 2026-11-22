"""story.json + voice timings -> a HyperFrames project (index.html + assets) of a stop-motion paper collage.

Everything moves on twos (12 steps per second), every piece boils a pixel or two like a real animation table,
scenes change with a paper wipe, and every entrance logs a foley event for sfx.py.

Scene kinds: hero, photo, duo, map, number, document, timeline, quote  (see SKILL.md for each kind's fields)
"""
import json
import math
import os
import re
import shutil

import numpy as np
from PIL import Image

from paper import CARDS, card, scrap, tape
from worlds import DARK, cloud, folds, moon, text_ratio, window_light
from worlds import world as make_world

HERE = os.path.dirname(os.path.abspath(__file__))
FPS_STEP = 12  # stop-motion cadence: one pose every 1/12 s
INK = "#1a1714"
RED = "rgb(%d,%d,%d)" % CARDS["red"]
CREAM = "#efe8da"


def rgb(c):
    return "rgb(%d,%d,%d)" % CARDS.get(c, c)


class B:
    """Collects markup, timeline lines and sfx events for one film."""

    def __init__(self, W, H, seed=11):
        self.W, self.H = W, H
        self.html, self.js, self.events = [], [], []
        self.rng = np.random.default_rng(seed)
        self.n = 0

    def id(self, p):
        self.n += 1
        return f"{p}{self.n}"

    def ev(self, t, k, **kw):
        self.events.append({"t": round(t, 3), "k": k, **kw})

    def r(self, a, b):
        return float(a + (b - a) * self.rng.random())


# ---------- JS helpers injected once ----------
JS_HEAD = r"""
const W = %(W)d, H = %(H)d;
// on twos: quantise any ease to 12 poses per second of its own duration
function st(base, dur){ const n = Math.max(1, Math.round(dur * 12)); const f = gsap.parseEase(base || "none");
  return p => f(Math.min(1, Math.floor(p * n + 1e-6) / n)); }
// deterministic jitter, one value per 1/12 s step
function jit(seed, dur){ const n = Math.max(1, Math.round(dur * 12));
  return p => { const k = Math.floor(p * n) + seed * 97.13; const v = Math.sin(k * 12.9898 + seed * 78.233) * 43758.5453; return v - Math.floor(v); }; }
const tl = gsap.timeline({ paused: true });
function boil(sel, t0, dur, seed, amp){
  const e = document.querySelector(sel); if (!e) return;
  e.style.setProperty("--amp", amp || 1);
  tl.fromTo(e, {"--bx": 0}, {"--bx": 1, duration: dur, ease: jit(seed, dur)}, t0);
  tl.fromTo(e, {"--by": 0}, {"--by": 1, duration: dur, ease: jit(seed + 3, dur)}, t0);
  tl.fromTo(e, {"--br": 0}, {"--br": 1, duration: dur, ease: jit(seed + 7, dur)}, t0);
}
"""

CSS = r"""
@font-face { font-family: "Anton"; src: url("assets/fonts/Anton-Regular.ttf"); }
@font-face { font-family: "Elite"; src: url("assets/fonts/SpecialElite-Regular.ttf"); }
@font-face { font-family: "Archivo"; src: url("assets/fonts/ArchivoBlack-Regular.ttf"); }
@font-face { font-family: "Marker"; src: url("assets/fonts/PermanentMarker-Regular.ttf"); }
* { margin: 0; padding: 0; box-sizing: border-box; }
html, body { width: %(W)dpx; height: %(H)dpx; overflow: hidden; background: #1a1714; }
#root { position: relative; width: %(W)dpx; height: %(H)dpx; overflow: hidden; }
.scene { position: absolute; inset: 0; overflow: hidden; }
.wipe { position: absolute; inset: 0; }
.cam { position: absolute; inset: 0; transform-origin: 50%% 45%%; }
.bg { position: absolute; inset: 0; width: 100%%; height: 100%%; }
.el { position: absolute; opacity: 0; }
.boil { --bx: .5; --by: .5; --br: .5; --amp: 1;
  transform: translate(calc((var(--bx) - .5) * 3px * var(--amp)), calc((var(--by) - .5) * 3px * var(--amp))) rotate(calc((var(--br) - .5) * .7deg * var(--amp))); }
.boil img, .boil svg { display: block; width: 100%%; height: auto; }
.strip { position: relative; padding: 14px 34px 10px; background: url("assets/paper/cream.jpg") center/cover; color: #1a1714;
  font-family: "Anton"; text-transform: uppercase; letter-spacing: 1px; line-height: 1; white-space: nowrap;
  filter: drop-shadow(5px 8px 6px rgba(20,14,8,.45)); }
.strip.ink { background: #1f1c19; color: #efe8da; }
.strip.red { background: url("assets/paper/red.jpg") center/cover; color: #efe8da; }
.strip.type { font-family: "Elite"; text-transform: none; letter-spacing: 0; padding: 10px 26px 8px; }
.stamp { font-family: "Anton"; color: %(RED)s; border: 9px solid %(RED)s; padding: 6px 26px 2px; line-height: 1; text-transform: uppercase;
  letter-spacing: 3px; white-space: nowrap; -webkit-mask-image: url("assets/paper/grunge.png"); mask-image: url("assets/paper/grunge.png");
  -webkit-mask-size: 420px; mask-size: 420px; mix-blend-mode: multiply; }
.chip { position: absolute; display: flex; align-items: center; justify-content: center; line-height: 1;
  filter: drop-shadow(5px 8px 5px rgba(20,14,8,.5)); }
.doc { position: relative; background: url("assets/paper/cream.jpg") center/cover; padding: 70px 64px; font-family: "Elite"; color: #1a1714;
  filter: drop-shadow(8px 12px 10px rgba(20,14,8,.45)); }
.doc .ln { position: relative; font-size: var(--fs, 46px); line-height: 1.55; white-space: nowrap; overflow: hidden; }
.doc .ln .tx { display: inline-block; }
.doc .bar { position: absolute; left: -6px; top: 10px; height: 46px; background: #141210; transform-origin: 0 50%%; }
.doc .hl { position: absolute; left: -8px; bottom: 4px; height: 18px; background: rgba(214,165,52,.75); transform-origin: 0 50%%; mix-blend-mode: multiply; }
#grain { position: absolute; inset: -40px; pointer-events: none; opacity: .16; mix-blend-mode: multiply; z-index: 900;
  background: url("assets/paper/grain.png"); --gx: 0; --gy: 0; background-position: calc(var(--gx) * 300px) calc(var(--gy) * 300px); }
#vig { position: absolute; inset: 0; pointer-events: none; z-index: 901;
  background: radial-gradient(ellipse at 50%% 45%%, rgba(0,0,0,0) 55%%, rgba(20,12,4,.38) 100%%); }
.cap { position: absolute; left: 0; right: 0; top: %(CAPY)dpx; display: flex; justify-content: center; z-index: 800; }
.cap .strip { font-family: "Archivo"; font-size: 62px; padding: 16px 30px 14px; letter-spacing: 0; }
.cap .w { display: inline-block; margin: 0 9px; }
@font-face { font-family: "Abril"; src: url("assets/fonts/AbrilFatface-Regular.ttf"); }
.strip.mustard { background: url("assets/paper/mustard.jpg") center/cover; color: #1a1714; }
.strip.teal { background: url("assets/paper/teal.jpg") center/cover; color: #efe8da; }
.strip.navy { background: url("assets/paper/navy.jpg") center/cover; color: #efe8da; }
.strip.fat { font-family: "Abril"; letter-spacing: 0; padding: 18px 42px 12px; }
@font-face { font-family: "DMSerif"; src: url("assets/fonts/DMSerifDisplay-Italic.ttf"); }
/* type is printed, not rendered: rough ink edges and a few missed specks, re-inked several times a second */
.ink { filter: url(#ink); }
.inkb { filter: url(#inkb); }
.strip .tx { display: inline-block; filter: url(#ink); }
.kwline { white-space: nowrap; line-height: 1; }
.kw { display: inline-block; opacity: 0; font-family: "Anton"; text-transform: uppercase; line-height: 1; white-space: nowrap;
  letter-spacing: 1px; filter: url(#ink); }
.kw.em { font-family: "DMSerif"; text-transform: lowercase; letter-spacing: 0; }
.big { font-family: "Abril"; line-height: 1; white-space: nowrap; text-transform: uppercase; filter: url(#inkb); }
.kick { font-family: "Anton"; line-height: 1; white-space: nowrap; text-transform: uppercase; letter-spacing: 2px; filter: url(#ink); }
.note { font-family: "Marker"; line-height: 1.04; white-space: nowrap; text-align: center; }
.note .c { opacity: 0; }
.kw .mk { position: absolute; left: -5%%; width: 110%%; top: 22%%; height: 70%%; background: rgb(240,206,58); z-index: -1;
  transform-origin: 0 50%%; transform: scaleX(0); mix-blend-mode: multiply; }
.pinhead { filter: drop-shadow(6px 10px 4px rgba(20,14,8,.45)); }
.cap.build { align-items: center; }
.cap .cw { display: inline-block; margin: 0 5px; padding: 13px 20px 9px; font-family: "Archivo"; line-height: 1;
  text-transform: uppercase; opacity: 0; background: #1f1c19; color: #efe8da; white-space: nowrap;
  filter: drop-shadow(4px 7px 5px rgba(20,14,8,.5)); }
"""


def torn_clip(rng, w=100, h=100, tear=3.0, ends=True):
    """A CSS clip-path polygon (percent) with torn left/right ends and slightly uneven top/bottom."""
    pts = []
    n = 14
    for i in range(n + 1):
        pts.append((i / n * 100, rng.random() * 3))
    for i in range(1, 8):
        pts.append((100 - rng.random() * tear * (1 if ends else 0.2), i / 8 * 100))
    for i in range(n + 1):
        pts.append((100 - i / n * 100, 100 - rng.random() * 3))
    for i in range(1, 8):
        pts.append((rng.random() * tear * (1 if ends else 0.2), 100 - i / 8 * 100))
    return "polygon(" + ",".join(f"{x:.1f}% {y:.1f}%" for x, y in pts) + ")"


def torn_band(rng, amp=5.0, n=46):
    """A clip-path for a strip torn along its top and bottom (the short ends run off the frame)."""
    top, bot, a, c = [], [], 0.0, 0.0
    for i in range(n + 1):
        a = 0.8 * a + rng.normal(0, 0.5)
        c = 0.8 * c + rng.normal(0, 0.5)
        ya = float(np.clip(amp * (0.5 + a * 0.3), 0, amp)) + rng.random() * amp * 0.15
        yc = float(np.clip(amp * (0.5 + c * 0.3), 0, amp)) + rng.random() * amp * 0.15
        top.append((i / n * 100, ya))
        bot.append((100 - i / n * 100, 100 - yc))
    return "polygon(" + ",".join(f"{x:.1f}% {y:.1f}%" for x, y in top + bot) + ")"


def stable(s):
    """A seed from a name that is the same on every run (Python's own hash() is salted per process)."""
    return sum((i + 1) * ord(ch) for i, ch in enumerate(str(s))) % 1000


def wobble_ellipse(rng, w, h):
    """A hand-drawn marker loop: an ellipse that overshoots its start, as SVG path data."""
    cx, cy, rx, ry = w / 2, h / 2, w / 2 - 10, h / 2 - 10
    pts = []
    for i in range(0, 41):
        a = -math.pi / 2 + i / 36 * 2 * math.pi
        k = 1 + 0.04 * math.sin(i * 0.9) + rng.normal(0, 0.012)
        pts.append((cx + math.cos(a) * rx * k, cy + math.sin(a) * ry * k))
    d = f"M{pts[0][0]:.1f},{pts[0][1]:.1f} " + " ".join(f"L{x:.1f},{y:.1f}" for x, y in pts[1:])
    return d


class Film:
    def __init__(self, story, timing, words, proj, images):
        self.s, self.timing, self.words, self.proj, self.img = story, timing, words, proj, images
        self.root = os.path.dirname(os.path.abspath(proj))
        fmt = story.get("format", "9:16")
        self.W, self.H = (1080, 1920) if fmt == "9:16" else (1920, 1080)
        self.v = fmt == "9:16"
        self.b = B(self.W, self.H, story.get("seed", 11))
        self.press_tag = "_%d" % stable(story.get("title", "") + "|".join(bt.get("say", "") for bt in story["beats"]))
        self.cap_y = 1520 if self.v else 900
        # content box (kept clear of captions and platform UI)
        self.box = (60, 230, self.W - 60, 1460) if self.v else (120, 90, self.W - 120, 840)

    # ----- element factory -----
    def el(self, inner, x, y, w, z, cls="", style=""):
        i = self.b.id("e")
        self.cur.append(f'<div class="el {cls}" id="{i}" style="left:{x:.0f}px;top:{y:.0f}px;width:{w:.0f}px;z-index:{z};{style}">'
                        f'<div class="boil" id="{i}b">{inner}</div></div>')
        return i

    def enter(self, i, t, how="slide", dur=0.45, rot=0.0, frm=None, sfx=True, amp=1.0, push=None, drift=None):
        b, js = self.b, self.b.js
        js.append(f'tl.set("#{i}", {{opacity: 1}}, {t:.3f});')
        if push or drift:
            # after it lands a piece never sits dead still: a slow push in, or a sideways drift, on twos
            rest = max(0.4, self.scene_end - (t + dur))
            to = (f"scale: {push}" if push else "") + (", " if push and drift else "") + (f"x: {drift}" if drift else "")
            js.append(f'tl.set("#{i}", {{transformOrigin: "50% 100%"}}, 0);')
            js.append(f'tl.to("#{i}", {{{to}, duration: {rest:.3f}, ease: st("sine.inOut", {rest:.3f})}}, {t + dur:.3f});')
        if how == "rise":
            dy = frm or 1000
            js.append(f'tl.fromTo("#{i}", {{y: {dy:.0f}, rotation: {rot + b.r(-5, 5):.1f}}}, '
                      f'{{y: 0, rotation: {rot:.1f}, duration: {dur}, ease: st("back.out(0.55)", {dur})}}, {t:.3f});')
            self.blur(i, t, dur, 0, 34)
            if sfx:
                b.ev(t, "whoosh", g=0.8)
                b.ev(t + dur * 0.8, "heavy", g=0.7)
        elif how == "slide":
            dx, dy = frm or (b.r(-1, 1) * 260, 1300 if b.rng.random() < .5 else -1300)
            js.append(f'tl.fromTo("#{i}", {{x: {dx:.0f}, y: {dy:.0f}, rotation: {rot + b.r(-14, 14):.1f}}}, '
                      f'{{x: 0, y: 0, rotation: {rot:.1f}, duration: {dur}, ease: st("back.out(1.15)", {dur})}}, {t:.3f});')
            big = abs(dy) >= abs(dx)
            self.blur(i, t, dur, 0 if big else 34, 34 if big else 0)
            if sfx:
                b.ev(t, "whoosh", g=0.55)
                b.ev(t + dur * 0.8, "slide", g=0.7)
                b.ev(t + dur * 0.9, "drop", g=0.7)
        elif how == "side":
            dx = frm if frm is not None else (-1400 if b.rng.random() < .5 else 1400)
            js.append(f'tl.fromTo("#{i}", {{x: {dx}, rotation: {rot - 6:.1f}}}, '
                      f'{{x: 0, rotation: {rot:.1f}, duration: {dur}, ease: st("power3.out", {dur})}}, {t:.3f});')
            self.blur(i, t, dur, 38, 0)
            if sfx:
                b.ev(t, "slide")
        elif how == "drop":
            js.append(f'tl.fromTo("#{i}", {{scale: 1.35, rotation: {rot + b.r(-6, 6):.1f}}}, '
                      f'{{scale: 1, rotation: {rot:.1f}, duration: 0.17, ease: st("power2.in", 0.17)}}, {t:.3f});')
            if sfx:
                b.ev(t + 0.15, "drop")
        elif how == "stamp":
            js.append(f'tl.fromTo("#{i}", {{scale: 1.6, rotation: {rot - 4:.1f}}}, '
                      f'{{scale: 1, rotation: {rot:.1f}, duration: 0.17, ease: st("power3.in", 0.17)}}, {t:.3f});')
            if sfx:
                b.ev(t + 0.15, "stamp")
        elif how in ("print", "slap"):
            # Type and labels are never flown in. They are simply there, a hair off register, and are knocked into
            # place over the next two poses, the way a hand sets a piece of paper down ("slap" is the bigger hit).
            k = 1.8 if how == "slap" else 1.0
            sgn = 1 if b.rng.random() < 0.5 else -1
            ox, oy = b.r(-14, 14) * k, -b.r(8, 20) * k
            js.append(f'tl.set("#{i}", {{x: {ox:.0f}, y: {oy:.0f}, rotation: {rot + sgn * b.r(4, 7) * k:.1f}, scale: {1 + 0.1 * k:.2f}}}, {t:.3f});')
            js.append(f'tl.set("#{i}", {{x: {-ox * 0.3:.0f}, y: {b.r(2, 6):.0f}, rotation: {rot - sgn * b.r(1, 2.2):.1f}, scale: 0.985}}, {t + 1 / 12:.3f});')
            js.append(f'tl.set("#{i}", {{x: 0, y: 0, rotation: {rot:.1f}, scale: 1}}, {t + 2 / 12:.3f});')
            if sfx:
                b.ev(t, "pop", g=0.8 if how == "slap" else 0.6)
                if how == "slap":
                    b.ev(t + 0.02, "drop", g=0.6)
        elif how == "pop":
            js.append(f'tl.fromTo("#{i}", {{scale: 0.55, rotation: {rot + b.r(-10, 10):.1f}}}, '
                      f'{{scale: 1, rotation: {rot:.1f}, duration: 0.34, ease: st("back.out(2)", 0.34)}}, {t:.3f});')
            if sfx:
                b.ev(t, "drop", g=0.8)
        elif how == "set":
            js.append(f'tl.set("#{i}", {{rotation: {rot:.1f}}}, {t:.3f});')
        return i

    def blur(self, i, t, dur, bx, by):
        """Motion blur along the move: strong while the piece flies, gone the moment it lands."""
        if not self.s.get("motion_blur", True) or (bx == 0 and by == 0):
            return
        fid = f"mb{i}"
        self.blurs.append(fid)
        self.b.js.append(f'document.getElementById("{i}").style.filter = "url(#{fid})";')
        self.b.js.append(f'tl.fromTo("#{fid} feGaussianBlur", {{attr: {{stdDeviation: "{bx} {by}"}}}}, '
                         f'{{attr: {{stdDeviation: "0 0"}}, duration: {dur * 0.75:.3f}, ease: st("power2.in", {dur * 0.75:.3f})}}, {t:.3f});')
        # no blur filter at all once landed (a resting piece must stay sharp, and the filter costs render time)
        self.b.js.append(f'tl.set("#{i}", {{filter: "none"}}, {t + dur * 0.8:.3f});')

    def boil_all(self, ids, t0, dur, amp=1.0):
        for k, i in enumerate(ids):
            self.b.js.append(f'boil("#{i}b", {t0:.3f}, {dur:.3f}, {self.b.n + k}, {amp});')

    def media(self, path):
        """Copy a footage file into the project (once) and return (src, w, h)."""
        import subprocess
        src = os.path.join(self.root, path)
        name = os.path.basename(path)
        dst = os.path.join(self.proj, "assets", "clips", name)
        if not os.path.exists(dst):
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            # a light 720p copy keeps the render fast; footage sits small inside a paper print anyway
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", src, "-vf", "scale='min(720,iw)':-2", "-an",
                            "-c:v", "libx264", "-crf", "20", "-g", "15", dst], check=True)
        out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height",
                              "-of", "csv=p=0", dst], capture_output=True, text=True).stdout.strip().split(",")
        return f"assets/clips/{name}", int(out[0]), int(out[1])

    # ----- reusable pieces -----
    def piece(self, key, box_w, box_h):
        """Fit an image piece into a box; returns (src, w, h)."""
        p = self.img[key]
        im = Image.open(os.path.join(self.proj, p))
        s = min(box_w / im.width, box_h / im.height)
        return p.replace("\\", "/"), im.width * s, im.height * s

    def img_el(self, key, cx, cy, bw, bh, z, rot=0.0):
        src, w, h = self.piece(key, bw, bh)
        i = self.el(f'<img src="{src}">', cx - w / 2, cy - h / 2, w, z, style=f"height:{h:.0f}px")
        return i, (cx - w / 2, cy - h / 2, w, h)

    def strip(self, text, x, y, size, z, kind="", anchor="c", max_w=None):
        b = self.b
        clip = torn_clip(b.rng)
        text = text.replace(chr(10), "<br>").replace("|", "<br>")
        tx = "translateX(-50%)" if anchor == "c" else "none"
        inner = (f'<div style="position:absolute;left:0;top:0;transform:{tx}">'
                 f'<div class="strip {kind}" style="font-size:{size}px;clip-path:{clip};display:inline-block;'
                 f'text-align:center"><span class="tx">{text}</span></div></div>')
        return self.el(inner, x, y, 0, z)

    def stamp(self, text, x, y, size, z):
        # red ink vanishes on red card: stamp in black there
        ink = "color:#efe8da;border-color:#efe8da;mix-blend-mode:normal;" if self.cur_bg in ("red", "pink") else ""
        half = (len(text) * size * 0.52 + 70) / 2  # keep long stamps inside the frame
        x = min(max(x, 60 + half), self.W - 60 - half)
        inner = (f'<div style="position:absolute;left:0;top:0;transform:translateX(-50%)">'
                 f'<div class="stamp" style="font-size:{size}px;display:inline-block;{ink}">{text}</div></div>')
        return self.el(inner, x, y, 0, z)

    def scraps(self, n, z=2):
        ids = []
        spots = [(-0.06, 0.12), (0.78, 0.2), (-0.1, 0.62), (0.8, 0.7), (0.3, -0.04), (0.55, 0.88)]
        order = self.b.rng.permutation(len(spots))
        for k in range(n):
            v = int(self.b.rng.integers(0, 4))
            w = 430 if v < 2 else 330
            fx, fy = spots[order[k % len(spots)]]
            x = fx * self.W + self.b.r(-30, 30)
            y = fy * self.H + self.b.r(-40, 40)
            ids.append(self.el(f'<img src="assets/paper/scrap{v}.png">', x, y, w, z))
        return ids

    def tape_on(self, x, y, rot, z):
        return self.el('<img src="assets/paper/tape.png">', x - 90, y - 26, 180, z), rot

    # ----- scene kinds -----
    def scene(self, k, beat, t0, dur, scene_end, trans):
        b = self.b
        self.cur = []
        ids, t = [], t0  # t0 = when the narration of this beat starts
        x0, y0, x1, y1 = self.box
        cx = (x0 + x1) / 2
        kind = beat.get("kind", "hero")
        fresh = []  # (id, entrance kwargs)

        full = beat.get("size") == "full"
        layered = bool(beat.get("band")) or full or self.cur_bg not in CARDS
        self.dark = self.cur_bg in DARK
        self.hero_box = None
        n_scraps = beat.get("scraps", 0 if layered else (2 if kind in ("hero", "duo", "number", "quote") else 1))
        for i in self.scraps(n_scraps):
            fresh.append((i, dict(how="drop", rot=b.r(-18, 18)), t - 0.22))

        if beat.get("burst"):
            col = rgb(beat.get("burst_color", "cream"))
            rays = "".join(
                f'<path d="M500,500 L{500 + 900 * math.cos(a):.0f},{500 + 900 * math.sin(a):.0f} '
                f'L{500 + 900 * math.cos(a + 0.13):.0f},{500 + 900 * math.sin(a + 0.13):.0f} Z" fill="{col}" opacity=".55"/>'
                for a in np.linspace(0, 2 * math.pi, 24, endpoint=False))
            size = 1500
            i = self.el(f'<svg viewBox="0 0 1000 1000" width="{size}" height="{size}">{rays}</svg>',
                        cx - size / 2, (y0 + y1) / 2 - size / 2 - 60, size, 1)
            b.js.append(f'tl.fromTo("#{i}", {{rotation: -25, scale: .6}}, {{rotation: 0, scale: 1, duration: .5, ease: st("power3.out", .5)}}, {t:.3f});')
            fresh.append((i, dict(how="set"), t))

        if kind == "hero" and full:
            # the subject fills the frame and runs off the bottom edge, the way a real collage is cropped
            bh = beat.get("hero_h", self.H + 80 - beat.get("hero_top", 0.33 if self.v else 0.18) * self.H)
            bw = self.W * (1.3 if self.v else 0.6)
            _, pw, ph = self.piece(beat["hero"], bw, bh)
            cy = beat.get("hero_y", self.H + 80 - ph / 2)
            i, (hx, hy, hw, hh) = self.img_el(beat["hero"], cx + beat.get("hero_x", 0), cy, bw, bh, 10)
            self.hero_box = (hx, hy, hw, hh)
            fresh.append((i, dict(how="rise", dur=0.5, rot=b.r(-1.5, 1.5), push=1.045), t + 0.26))
            self._labels(beat, t, dur, fresh, top=hy, bottom=hy + hh, cx=cx)

        elif kind == "hero":
            bh = beat.get("hero_h", 1000 if self.v else 640)
            cy = beat.get("hero_y", 900 if self.v else 470)
            i, (hx, hy, hw, hh) = self.img_el(beat["hero"], cx, cy, 960 if self.v else 900, bh, 10)
            fresh.append((i, dict(how="slide", dur=0.5, rot=b.r(-3, 3)), t + 0.08))
            if beat.get("circle"):
                cw, ch = hw * 0.62, hh * 0.42
                d = wobble_ellipse(b.rng, cw, ch)
                ci = self.el(f'<svg viewBox="0 0 {cw:.0f} {ch:.0f}" width="{cw:.0f}" height="{ch:.0f}" style="overflow:visible">'
                             f'<path d="{d}" fill="none" stroke="{RED}" stroke-width="11" stroke-linecap="round" pathLength="1" '
                             f'stroke-dasharray="1" stroke-dashoffset="1" class="draw"/></svg>',
                             hx + hw * 0.19, hy + hh * 0.02, cw, 30)
                ta = t + min(dur * 0.5, 1.4)
                b.js.append(f'tl.fromTo("#{ci} path", {{strokeDashoffset: 1}}, {{strokeDashoffset: 0, duration: .5, ease: st("power1.inOut", .5)}}, {ta:.3f});')
                fresh.append((ci, dict(how="set"), ta))
                b.ev(ta, "draw")
            self._labels(beat, t, dur, fresh, top=hy, bottom=hy + hh, cx=cx)

        elif kind == "photo":
            cy = beat.get("hero_y", 880 if self.v else 470)
            rot = b.r(-4, 4)
            i, (hx, hy, hw, hh) = self.img_el(beat["photo"], cx, cy, 1000 if self.v else 1000, 940 if self.v else 640, 10)
            fresh.append((i, dict(how="slide", dur=0.5, rot=rot), t + 0.08))
            for tx, ty, tr in ((hx + 70, hy + 18, -30), (hx + hw - 70, hy + 18, 28)):
                ti, _ = self.tape_on(tx, ty, tr, 12)
                fresh.append((ti, dict(how="drop", rot=tr), t + 0.6))
                b.ev(t + 0.6, "tape", g=0.6)
            self._labels(beat, t, dur, fresh, top=hy, bottom=hy + hh, cx=cx)

        elif kind == "duo":
            bw = 470 if self.v else 640
            bh = 760 if self.v else 640
            cy = 900 if self.v else 470
            li, (lx, ly, lw, lh) = self.img_el(beat["left"], cx - bw / 2 - 10, cy, bw, bh, 10)
            ri, (rx, ry, rw, rh) = self.img_el(beat["right"], cx + bw / 2 + 10, cy, bw, bh, 11)
            fresh.append((li, dict(how="side", frm=-1400, rot=b.r(-4, 1)), t + 0.05))
            fresh.append((ri, dict(how="side", frm=1400, rot=b.r(-1, 4)), t + 0.35))
            if beat.get("string", True):
                p1 = (lx + lw * 0.5, ly + lh * 0.12)
                p2 = (rx + rw * 0.5, ry + rh * 0.12)
                sag = 90
                mid = ((p1[0] + p2[0]) / 2, max(p1[1], p2[1]) + sag)
                si = self.el(f'<svg viewBox="0 0 {self.W} {self.H}" width="{self.W}" height="{self.H}">'
                             f'<path d="M{p1[0]:.0f},{p1[1]:.0f} Q{mid[0]:.0f},{mid[1]:.0f} {p2[0]:.0f},{p2[1]:.0f}" fill="none" '
                             f'stroke="{RED}" stroke-width="6" pathLength="1" stroke-dasharray="1" stroke-dashoffset="1"/>'
                             f'<circle cx="{p1[0]:.0f}" cy="{p1[1]:.0f}" r="14" fill="#c9a24a" stroke="#5b4a1c" stroke-width="3"/>'
                             f'<circle cx="{p2[0]:.0f}" cy="{p2[1]:.0f}" r="14" fill="#c9a24a" stroke="#5b4a1c" stroke-width="3"/></svg>',
                             0, 0, self.W, 25)
                ta = t + 0.85
                b.js.append(f'tl.fromTo("#{si} path", {{strokeDashoffset: 1}}, {{strokeDashoffset: 0, duration: .45, ease: st("power2.inOut", .45)}}, {ta:.3f});')
                fresh.append((si, dict(how="set"), ta))
                b.ev(ta - 0.1, "pin")
                b.ev(ta, "draw", g=0.6)
            self._labels(beat, t, dur, fresh, top=min(ly, ry), bottom=max(ly + lh, ry + rh), cx=cx)

        elif kind == "clip":
            # taped prints with real footage playing inside (one big, or a grid of up to four)
            items = beat.get("clips") or [{"clip": beat["clip"], "from": beat.get("from", 0)}]
            n = len(items)
            cols = 1 if n == 1 else 2
            rows = (n + cols - 1) // cols
            area_w = (x1 - x0) - 40
            area_h = (900 if self.v else 640) if n == 1 else (1060 if self.v else 680)
            cy = beat.get("hero_y", 870 if self.v else 470)
            cell_w, cell_h = area_w / cols, area_h / rows
            tops = []
            for j, it in enumerate(items):
                src, vw, vh = self.media(it["clip"])
                sc = min((cell_w - 50) / vw, (cell_h - 50) / vh)
                w, h = vw * sc, vh * sc
                ccx = x0 + 20 + cell_w * (j % cols + 0.5)
                ccy = cy - area_h / 2 + cell_h * (j // cols + 0.5)
                vid = b.id("v")
                d0 = max(0.0, t0 - 0.3)
                inner = (f'<div style="position:relative;width:{w + 28:.0f}px;padding:14px;background:url(assets/paper/cream.jpg) center/cover;'
                         f'box-shadow:{14 if j % 2 else -14}px 12px 0 {rgb(beat.get("accent", "red"))}, 6px 12px 18px rgba(20,14,8,.45)">'
                         f'<video id="{vid}" class="clip" src="{src}" muted playsinline data-start="{d0:.3f}" '
                         f'data-duration="{self.scene_end - d0:.3f}" data-media-start="{it.get("from", 0):.3f}" data-track-index="3" '
                         f'style="display:block;width:{w:.0f}px;height:{h:.0f}px;object-fit:cover"></video></div>')
                rot = b.r(-4, 4)
                i = self.el(inner, ccx - (w + 28) / 2, ccy - (h + 28) / 2, w + 28, 10 + j)
                fresh.append((i, dict(how="slide", dur=0.45, rot=rot), t + 0.05 + j * 0.16))
                ti, _ = self.tape_on(ccx, ccy - (h + 28) / 2 + 6, b.r(-6, 6), 30 + j)
                fresh.append((ti, dict(how="drop", rot=b.r(-6, 6)), t + 0.4 + j * 0.16))
                tops.append(ccy - (h + 28) / 2)
            self._labels(beat, t, dur, fresh, top=min(tops), bottom=cy + area_h / 2, cx=cx)

        elif kind == "kinetic":
            # the sentence itself is the picture: one word lands each time it is spoken, the last line biggest
            lines = beat.get("lines")
            if not lines:
                lines, cur = [], []
                for w in beat["say"].split():
                    w = w.strip(".,;:!?\"")
                    if not w:
                        continue
                    if cur and (len(cur) >= 2 or len(" ".join(cur + [w])) > 11):
                        lines.append(" ".join(cur))
                        cur = []
                    cur.append(w)
                if cur:
                    lines.append(" ".join(cur))
            em = {x.lower() for x in beat.get("em", [])}
            # each word lands when it is spoken; the lines may be a shorter version of the sentence
            times, ptr, last = [], 0, t + 0.1
            for w in " ".join(lines).split():
                hit = self.find_word(w, ptr)
                if hit:
                    ptr, last = hit[0] + 1, hit[1]
                else:
                    last += 0.22
                times.append(last)
            # two voices of type: a condensed heavy sans for the plain words, an italic serif for the ones that matter
            fn, fe = "Anton-Regular.ttf", "DMSerifDisplay-Italic.ttf"

            def is_em(w):
                return w.lower() in em or w.lower().strip("'\".,;:!?") in em

            def ratio(ln):  # width of a line in units of its own font size, gaps included
                ws = ln.split()
                return sum(text_ratio(fe, w.lower()) * 1.12 if is_em(w) else text_ratio(fn, w.upper()) + 0.01 * len(w) for w in ws) + 0.25 * (len(ws) - 1)

            room = (x1 - x0) - 60
            hero = beat.get("hero")
            ink_c = CREAM if self.dark else INK
            em_c = rgb("mustard") if self.dark else RED
            hl = {x.lower().strip("'\".,;:!?") for x in beat.get("hl", [])}
            # yellow marker, except on yellow and brown card where it would vanish: there it is a cream paper strip
            mk_bg = "background:rgb(242,236,222);mix-blend-mode:normal" if self.cur_bg in ("mustard", "kraft", "olive") else ""
            # a solid second print under every word, so it reads on any paper (rings, newsprint, sky)
            shade = INK if self.dark else "rgba(239,232,218,.8)"
            swap = beat.get("swap", False)
            base = beat.get("size", (340 if swap else 200) if self.v else (260 if swap else 150))
            sizes = [min(base * (1.45 if not swap and j == len(lines) - 1 and len(lines) > 1 else 1.0), room / max(0.1, ratio(ln)))
                     for j, ln in enumerate(lines)]
            block = sum(s * 1.02 for s in sizes)
            ty = beat.get("text_y") or ((y0 + 40) if hero else ((y0 + y1) / 2 - block / 2))
            wn, line_ids, starts = 0, [], []
            for j, ln in enumerate(lines):
                size = sizes[j]
                spans = []
                starts.append(times[wn])
                for w in ln.split():
                    e = is_em(w)
                    wid = b.id("k")
                    mark = w.lower().strip("'\".,;:!?") in hl
                    if mark:
                        # a highlighter swipe behind the word, drawn on just after it is printed
                        spans.append((wid, f'<span class="kw{" em" if e else ""}" id="{wid}" style="font-size:{size * (1.12 if e else 1):.0f}px;'
                                           f'color:{INK};margin-right:{size * 0.25:.0f}px;position:relative">'
                                           f'<i class="mk" style="clip-path:{torn_clip(b.rng, tear=2.5)};{mk_bg}"></i>{w}</span>'))
                        tm = times[wn] + 0.3
                        b.js.append(f'tl.fromTo("#{wid} .mk", {{scaleX: 0}}, {{scaleX: 1, duration: .24, ease: st("power2.out", .24)}}, {tm:.3f});')
                        b.ev(tm, "draw", g=0.9)
                    else:
                        spans.append((wid, f'<span class="kw{" em" if e else ""}" id="{wid}" style="font-size:{size * (1.12 if e else 1):.0f}px;'
                                           f'color:{em_c if e else ink_c};margin-right:{size * 0.25:.0f}px;'
                                           f'text-shadow:{size * 0.03:.0f}px {size * 0.042:.0f}px 0 {shade}">{w}</span>'))
                    # the word is on screen the instant it is spoken (the entrance loop takes 0.18 s off)
                    fresh.append((wid, dict(how="print", rot=b.r(-1.6, 1.6)), times[wn] + 0.15))
                    wn += 1
                if swap:
                    # one phrase at a time in the same spot: each one replaces the last
                    yy = beat.get("text_y") or ((y0 + 300) if hero else (y0 + y1) / 2) - size * 0.55
                    li = self.el(f'<div class="kwline" style="text-align:center;margin-right:-{size * 0.25:.0f}px">{"".join(s for _, s in spans)}</div>',
                                 x0 + 30, yy, room, 40 + j)
                else:
                    li = self.el(f'<div class="kwline">{"".join(s for _, s in spans)}</div>', x0 + 30, ty, room, 40 + j)
                    # an italic serif hangs below the line: give its descenders room
                    ty += size * (1.16 if any(is_em(w) for w in ln.split()) else 1.02)
                line_ids.append(li)
                fresh.append((li, dict(how="set", sfx=False), t0 - 0.07))
            if swap:
                for j in range(len(lines) - 1):
                    b.js.append(f'tl.set("#{line_ids[j]}", {{opacity: 0}}, {max(starts[j] + 0.1, starts[j + 1] - 0.03):.3f});')
            if hero:
                bh = beat.get("hero_h", 900 if self.v else 560)
                _, pw, ph = self.piece(hero, self.W - 80, bh)
                i, _ = self.img_el(hero, cx + beat.get("hero_x", 0), beat.get("hero_y", self.H + 80 - ph / 2), self.W - 80, bh, 10)
                fresh.append((i, dict(how="rise", dur=0.5, rot=b.r(-1.5, 1.5), push=1.04), t + 0.2))

        elif kind == "board":
            # an evidence board: one photo in the middle, up to four around it, pinned, joined by red string
            ccy = beat.get("hero_y", 985 if self.v else 520)
            cw_, ch_ = (580, 520) if self.v else (620, 480)
            ci, (hx, hy, hw, hh) = self.img_el(beat["center"], cx, ccy, cw_, ch_, 12)
            fresh.append((ci, dict(how="slide", dur=0.45, rot=b.r(-2, 2), frm=(0, 1400)), t + 0.05))
            # top row under the title, bottom row clear of the captions
            spots = ([(0.25, 0.30), (0.76, 0.315), (0.24, 0.655), (0.77, 0.64)] if self.v
                     else [(0.17, 0.26), (0.83, 0.28), (0.18, 0.74), (0.82, 0.72)])
            sw, sh_ = (430, 330) if self.v else (420, 300)
            pin_c = (hx + hw / 2, hy + 26)
            pins = []
            around = beat.get("around", [])[:4]
            land = t + 0.5
            for j, it in enumerate(around):
                key = it["img"] if isinstance(it, dict) else it
                fx, fy = spots[j]
                sx, sy = fx * self.W, fy * self.H
                si, (px, py, pw, ph) = self.img_el(key, sx, sy, sw, sh_, 8 + j)
                frm = (-1300 if fx < 0.5 else 1300, b.r(-200, 200))
                te = t + 0.28 + j * 0.16
                fresh.append((si, dict(how="slide", dur=0.42, rot=b.r(-7, 7), frm=frm), te))
                land = max(land, te + 0.3)
                if isinstance(it, dict) and it.get("tag"):
                    ti = self.strip(it["tag"], px + pw / 2, py + ph - 26, 40, 30 + j, kind="type")
                    fresh.append((ti, dict(how="slap", rot=b.r(-6, 6)), te + 0.35))
                pins.append((px + pw / 2 + b.r(-30, 30), py + 24))
            pin_svg = ('<svg width="54" height="54" viewBox="0 0 54 54" class="pinhead"><circle cx="27" cy="25" r="17" fill="{c}"/>'
                       '<circle cx="21" cy="19" r="6" fill="rgba(255,255,255,.55)"/><circle cx="27" cy="25" r="17" fill="none" '
                       'stroke="rgba(0,0,0,.35)" stroke-width="3"/></svg>').format(c=RED)
            allp = [pin_c] + pins
            for j, (qx, qy) in enumerate(allp):
                pi = self.el(pin_svg, qx - 27, qy - 27, 54, 60 + j)
                fresh.append((pi, dict(how="drop", rot=0), land + 0.05 + j * 0.08))
                b.ev(land + 0.05 + j * 0.08, "pin", g=0.8)
            # string from every outer pin to the middle one, drawn one after another
            ta = land + 0.15 + len(allp) * 0.08
            paths = []
            for (qx, qy) in pins:
                mx, my = (qx + pin_c[0]) / 2, max(qy, pin_c[1]) + 70
                paths.append(f'<path d="M{qx:.0f},{qy:.0f} Q{mx:.0f},{my:.0f} {pin_c[0]:.0f},{pin_c[1]:.0f}" fill="none" stroke="{RED}" '
                             f'stroke-width="7" stroke-linecap="round" pathLength="1" stroke-dasharray="1" stroke-dashoffset="1"/>')
            if paths:
                si = self.el(f'<svg viewBox="0 0 {self.W} {self.H}" width="{self.W}" height="{self.H}" '
                             f'style="overflow:visible;filter:drop-shadow(4px 8px 3px rgba(20,14,8,.4))">{"".join(paths)}</svg>', 0, 0, self.W, 55)
                fresh.append((si, dict(how="set"), ta - 0.02))
                for j in range(len(paths)):
                    b.js.append(f'tl.fromTo("#{si} path:nth-of-type({j + 1})", {{strokeDashoffset: 1}}, {{strokeDashoffset: 0, duration: .32, '
                                f'ease: st("power1.inOut", .32)}}, {ta + j * 0.2:.3f});')
                    b.ev(ta + j * 0.2, "draw", g=0.5)
            if beat.get("circle"):
                cw2, ch2 = hw * 0.62, hh * 0.46
                d = wobble_ellipse(b.rng, cw2, ch2)
                cc = self.el(f'<svg viewBox="0 0 {cw2:.0f} {ch2:.0f}" width="{cw2:.0f}" height="{ch2:.0f}" style="overflow:visible">'
                             f'<path d="{d}" fill="none" stroke="{RED}" stroke-width="12" stroke-linecap="round" pathLength="1" '
                             f'stroke-dasharray="1" stroke-dashoffset="1"/></svg>', hx + hw * 0.19, hy + hh * 0.04, cw2, 58)
                tc = self.word_time(beat.get("circle_on")) or (ta + len(paths) * 0.2 + 0.1)
                b.js.append(f'tl.fromTo("#{cc} path", {{strokeDashoffset: 1}}, {{strokeDashoffset: 0, duration: .5, ease: st("power1.inOut", .5)}}, {tc:.3f});')
                fresh.append((cc, dict(how="set"), tc))
                b.ev(tc, "draw", g=0.9)
            # the title sits at the very top, above the pinned photos, never across them
            self._labels(beat, t, dur, fresh, top=y0 + 10 + beat.get("label_size", 110) + 70, bottom=hy + hh, cx=cx)

        elif kind == "number":
            text = str(beat["number"])
            if " " in text and len(text) > 5:
                rows = text.split(" ", 1)
            elif len(text) > 7:
                rows = [text[: len(text) // 2 + 1], text[len(text) // 2 + 1:]]
            else:
                rows = [text]
            fit = (x1 - x0 - 40) / (max(len(r) for r in rows) * 0.78)
            size = min(beat.get("size", 250), fit)
            cy0 = (beat.get("number_y") or (700 if self.v else 380)) - (len(rows) - 1) * size * 0.6
            fonts = ["Anton", "Archivo", "Elite", "Anton"]
            bgs = [("cream", INK), ("ink", CREAM), ("red", CREAM), ("mustard", INK), ("cream", RED)]
            k = 0
            for r_i, row in enumerate(rows):
                cw = size * 0.78
                xs = cx - len(row) * cw / 2
                for j, ch in enumerate(row):
                    if ch == " ":
                        continue
                    bgn, fg = bgs[(k * 3 + r_i) % len(bgs)]
                    f = fonts[k % len(fonts)]
                    rot = b.r(-7, 7)
                    bg_css = f'url(assets/paper/{bgn}.jpg) center/cover' if bgn != "ink" else "#1f1c19"
                    inner = (f'<div class="chip" style="position:relative;width:{cw - 6:.0f}px;height:{size * 1.08:.0f}px;'
                             f'background:{bg_css};color:{fg};font-family:{f};font-size:{size * (0.86 if f != "Elite" else 0.8):.0f}px;'
                             f'clip-path:{torn_clip(b.rng, tear=4)}">{ch}</div>')
                    i = self.el(inner, xs + j * cw, cy0 + r_i * size * 1.2 + b.r(-12, 12), cw, 20 + k)
                    fresh.append((i, dict(how="drop", rot=rot), t + 0.1 + k * 0.09))
                    k += 1
            sub_y = cy0 + len(rows) * size * 1.2 + 40
            if beat.get("hero"):
                i, _ = self.img_el(beat["hero"], cx, sub_y + 330, 600, 520, 9)
                fresh.append((i, dict(how="slide", rot=b.r(-3, 3)), t + 0.05))
            if beat.get("sub"):
                si = self.strip(beat["sub"], cx, sub_y if not beat.get("hero") else cy0 - size * 0.9, 74, 40, kind="ink")
                fresh.append((si, dict(how="side", rot=b.r(-2, 2)), t + 0.2 + k * 0.09))
            if beat.get("stamp"):
                st_ = self.stamp(beat["stamp"], cx + 210, cy0 - size * 0.75, 84, 60)
                ta = t + min(dur * 0.6, 1.6)
                fresh.append((st_, dict(how="stamp", rot=-9), ta))

        elif kind == "document":
            lines = beat.get("lines", [])
            fs = 58 if max((len(x) for x in lines), default=0) <= 20 else 46  # short lines read bigger on a phone
            dw = 900 if self.v else 1000
            est_h = 140 + (92 if beat.get("head") else 0) + len(lines) * 74
            dy = beat.get("doc_y", (845 - est_h / 2) if self.v else 120)
            rows = []
            for li, ln in enumerate(lines):
                bar = '<div class="bar" style="width:{w}px;transform:scaleX(0)"></div>'.format(w=len(ln) * fs * 0.6 + 12) if li in beat.get("redact", []) else ""
                hl = '<div class="hl" style="width:{w}px;transform:scaleX(0)"></div>'.format(w=len(ln) * fs * 0.6 + 16) if li == beat.get("mark") else ""
                rows.append(f'<div class="ln ln{li}"><span class="tx" style="clip-path:inset(0 100% 0 0)">{ln}</span>{hl}{bar}</div>')
            head = beat.get("head")
            hh = f'<div style="font-family:Anton;font-size:64px;letter-spacing:4px;margin-bottom:28px">{head}</div>' if head else ""
            inner = (f'<div class="doc" style="clip-path:{torn_clip(b.rng, tear=1.2, ends=False)};--fs:{fs}px">'
                     f'{hh}{"".join(rows)}</div>')
            di = self.el(inner, cx - dw / 2, dy, dw, 10)
            fresh.append((di, dict(how="slide", dur=0.5, rot=b.r(-2.5, 2.5)), t + 0.02))
            tt = t + 0.35
            per = max(0.18, min(0.9, (dur * 0.7 - 0.4) / max(1, len(lines))))
            for li, ln in enumerate(lines):
                b.js.append(f'tl.fromTo("#{di} .ln{li} .tx", {{clipPath: "inset(0 100% 0 0)"}}, '
                            f'{{clipPath: "inset(0 0% 0 0)", duration: {per:.2f}, ease: st("none", {per:.2f})}}, {tt:.3f});')
                b.ev(tt, "type", n=max(4, int(len(ln) * 0.6)), g=0.7)
                if li in beat.get("redact", []):
                    b.js.append(f'tl.fromTo("#{di} .ln{li} .bar", {{scaleX: 0}}, {{scaleX: 1, duration: .25, ease: st("power2.out", .25)}}, {tt + per + 0.1:.3f});')
                    b.ev(tt + per + 0.1, "draw", g=0.8)
                if li == beat.get("mark"):
                    b.js.append(f'tl.fromTo("#{di} .ln{li} .hl", {{scaleX: 0}}, {{scaleX: 1, duration: .3, ease: st("power2.out", .3)}}, {tt + per + 0.1:.3f});')
                    b.ev(tt + per + 0.1, "draw", g=0.7)
                tt += per + 0.05
            if beat.get("hero"):
                i, _ = self.img_el(beat["hero"], cx + 230, dy + 120, 360, 420, 14)
                fresh.append((i, dict(how="drop", rot=b.r(4, 9)), t + 0.3))
                ti, _ = self.tape_on(cx + 230, dy - 60, 8, 15)
                fresh.append((ti, dict(how="drop", rot=8), t + 0.45))
            if beat.get("stamp"):
                st_ = self.stamp(beat["stamp"], cx + 120, dy + 60 + len(lines) * 62 + (100 if head else 0) + 40, 96, 60)
                fresh.append((st_, dict(how="stamp", rot=-12), min(tt + 0.1, t + dur - 0.3)))
            if beat.get("label"):
                li_ = self.strip(beat["label"], cx, dy - 150, 100, 45)
                fresh.append((li_, dict(how="side", rot=b.r(-2, 2)), t + 0.25))

        elif kind == "timeline":
            dates = beat["dates"]
            act = beat.get("active", len(dates) - 1)
            ly = beat.get("line_y", 1060 if self.v else 640)
            lx0, lx1 = x0 + 130, x1 - 130
            li = self.el(f'<div style="height:16px;background:{INK};clip-path:{torn_clip(b.rng, tear=1)}"></div>', lx0, ly, lx1 - lx0, 8)
            b.js.append(f'tl.fromTo("#{li}", {{scaleX: 0, transformOrigin: "0% 50%"}}, {{scaleX: 1, duration: .5, ease: st("power2.out", .5)}}, {t + 0.05:.3f});')
            fresh.append((li, dict(how="set"), t + 0.05))
            b.ev(t + 0.05, "slide")
            gap = (lx1 - lx0) / max(1, len(dates) - 1) if len(dates) > 1 else 0
            for j, d in enumerate(dates):
                x = lx0 + gap * j if len(dates) > 1 else cx
                kind_ = "red" if j == act else ("ink" if j % 2 else "")
                above = j % 2 == 0
                si = self.strip(d, x, ly - 130 if above else ly + 50, 64, 20 + j, kind=kind_)
                fresh.append((si, dict(how="drop", rot=b.r(-5, 5)), t + 0.35 + j * 0.18))
                pi = self.el(f'<svg width="30" height="30"><circle cx="15" cy="15" r="12" fill="#c9a24a" stroke="#5b4a1c" stroke-width="3"/></svg>', x - 15, ly - 7, 30, 30)
                fresh.append((pi, dict(how="drop"), t + 0.3 + j * 0.18))
            if beat.get("hero"):
                i, _ = self.img_el(beat["hero"], cx, ly - 470 if self.v else ly - 320, 760, 560 if self.v else 380, 9)
                fresh.append((i, dict(how="slide", rot=b.r(-3, 3)), t + 0.1))
            if beat.get("label"):
                lb = self.strip(beat["label"], cx, (y0 + 30) if not beat.get("hero") else ly + 220, 96, 45)
                fresh.append((lb, dict(how="side", rot=b.r(-2, 2)), t + 0.6 + len(dates) * 0.18))

        elif kind == "quote":
            q = beat["quote"]
            if beat.get("hero"):
                i, (hx, hy, hw, hh) = self.img_el(beat["hero"], cx, (520 if self.v else 380), 640, 560 if self.v else 520, 9)
                fresh.append((i, dict(how="slide", rot=b.r(-3, 3)), t + 0.05))
                qy = hy + hh + 30
            else:
                qy = 600 if self.v else 300
            words = q.split()
            lines, cur = [], ""
            lim = 18 if self.v else 34
            for w in words:
                if len(cur) + len(w) + 1 > lim and cur:
                    lines.append(cur)
                    cur = w
                else:
                    cur = (cur + " " + w).strip()
            lines.append(cur)
            for j, ln in enumerate(lines):
                kind_ = "ink" if j % 2 else ""
                si = self.strip(("&ldquo;" if j == 0 else "") + ln + ("&rdquo;" if j == len(lines) - 1 else ""),
                                cx + b.r(-30, 30), qy + j * 118, 84, 30 + j, kind=kind_)
                fresh.append((si, dict(how="side", rot=b.r(-2.5, 2.5)), t + 0.25 + j * 0.22))
            if beat.get("by"):
                bi = self.strip(beat["by"], cx + 160, qy + len(lines) * 118 + 20, 44, 50, kind="type")
                fresh.append((bi, dict(how="drop", rot=b.r(-3, 3)), t + 0.4 + len(lines) * 0.22))

        elif kind == "map":
            m = beat["map"]
            mw = 960 if self.v else 1100
            mh = 900 if self.v else 680
            my = beat.get("map_y", 420 if self.v else 150)
            sheet = f'<div style="position:absolute;inset:0;background:url(assets/paper/{m.get("sea", "teal")}.jpg) center/cover;clip-path:{torn_clip(b.rng, tear=1.5)}"></div>'
            mid = b.id("map")
            svg = (f'<svg id="{mid}" viewBox="0 0 {mw} {mh}" width="{mw}" height="{mh}" style="position:relative">'
                   f'<defs><pattern id="{mid}dots" width="9" height="9" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">'
                   f'<rect width="9" height="9" fill="#e9dfc8"/><circle cx="4.5" cy="4.5" r="1.7" fill="#b9ab8c"/></pattern></defs>'
                   f'<g class="land"></g><g class="hit"></g></svg>')
            i = self.el(f'<div style="position:relative;width:{mw}px;height:{mh}px">{sheet}{svg}</div>', cx - mw / 2, my, mw, 10)
            fresh.append((i, dict(how="slide", dur=0.5, rot=b.r(-2, 2)), t))
            self.maps.append({"id": mid, "w": mw, "h": mh, **m})
            hl_t = t + 0.6
            b.js.append(f'tl.fromTo("#{mid} .hit path", {{opacity: 0}}, {{opacity: 1, duration: .34, ease: st("none", .34)}}, {hl_t:.3f});')
            b.ev(hl_t, "draw", g=0.6)
            if m.get("pin"):
                # pin + place tag are placed by the map script; their containers are timed here
                pin_id = f"{mid}pin"
                self.cur.append(f'<div class="el" id="{pin_id}" style="left:0;top:0;width:44px;z-index:30"><div class="boil" id="{pin_id}b">'
                                f'<svg width="44" height="44"><circle cx="22" cy="22" r="17" fill="{RED}" stroke="#1a1714" stroke-width="5"/>'
                                f'<circle cx="22" cy="22" r="6" fill="#efe8da"/></svg></div></div>')
                self.pins.append((pin_id, mid, cx - mw / 2, my))
                fresh.append((pin_id, dict(how="drop"), t + 0.95))
                if m.get("place"):
                    tag = self.strip(m["place"], 0, 0, 56, 31, kind="ink", anchor="l")
                    self.tags.append((tag, mid, cx - mw / 2, my))
                    fresh.append((tag, dict(how="side", rot=b.r(-3, 3)), t + 1.1))
            if beat.get("label"):
                lb = self.strip(beat["label"], cx, my - 150 if self.v else my - 60, 100, 45)
                fresh.append((lb, dict(how="side", rot=b.r(-2, 2)), t + 0.3))
            if beat.get("stamp"):
                st_ = self.stamp(beat["stamp"], cx + 140, my + mh - 40, 90, 60)
                fresh.append((st_, dict(how="stamp", rot=-10), t + min(dur * 0.6, 1.6)))

        # layers every kind can take: a torn strip behind the subject, loose sky pieces, and text that builds
        if beat.get("band"):
            self.band(beat, t, fresh)
        if beat.get("clouds", 3 if self.cur_bg == "sky" else 0):
            self.sky_pieces(beat.get("clouds", 3), t, fresh)
        if beat.get("moon", self.cur_bg == "night"):
            # "moon": true, or [centre x, centre y, size] as fractions of the frame and pixels
            mo = beat.get("moon")
            mx, my, ms = mo if isinstance(mo, (list, tuple)) else (0.26, 0.17, 300)
            mi = self.el('<img src="assets/paper/moon.png">', mx * self.W - ms / 2, my * self.H - ms / 2, ms, 2)
            self.use_moon = True
            fresh.append((mi, dict(how="rise", frm=700, dur=0.55, rot=b.r(-8, 8), sfx=False, push=1.03), t + 0.2))
        if kind == "scene":
            # an empty stage: only the layers below (band, letters, headline, tags, notes) plus label / tag / stamp
            self._labels(beat, t, dur, fresh, top=y0 + 260, bottom=y1 - 120, cx=cx)
        if beat.get("letters"):
            self.letters(beat, t, dur, fresh)
        if beat.get("headline"):
            self.headline(beat, t, dur, fresh)
        if beat.get("tags"):
            self.tags_on(beat, t, dur, fresh)
        if beat.get("notes"):
            self.notes(beat, t, dur, fresh)

        # entrances + boil
        for i, kw, te in fresh:
            ta = max(0.0, te - 0.18, t0 - 0.25)
            if self.k == 0 and ta < 0.4:
                # the film opens with its first pieces already on the table: frame 0 is never an empty page
                kw = {a: v for a, v in kw.items() if a in ("rot", "push", "drift")}
                self.enter(i, 0.0, how="set", dur=0.0, **kw)
            else:
                self.enter(i, ta, **kw)
        self.boil_all([i for i, _, _ in fresh], max(0.0, t0 - 0.25), scene_end - max(0.0, t0 - 0.25) + 0.05)
        return self.cur

    # ----- layers shared by every scene kind -----
    def band(self, beat, t, fresh):
        """A strip of torn paper across the frame, behind the subject: sky, night, a colour, or one of the photos."""
        b = self.b
        what = beat["band"]
        y = beat.get("band_y", 0.29) * self.H
        h = beat.get("band_h", 0.31) * self.H
        wd = self.W + 160
        rest = self.scene_end - t
        inside = ""
        if what in self.img:
            fill = ""
            inside = (f'<img src="{self.img[what]}" style="position:absolute;left:0;top:0;width:100%;height:100%;'
                      f'object-fit:cover">')
        else:
            tag = self.press_tag if what.startswith("press") else ""
            self.need_band.add((what, tag))
            fill = f"background:url(assets/paper/band_{what}{tag}.jpg) center/cover;"
        if what == "sky":
            self.use_clouds = True
            for j in range(3):
                cw = b.r(300, 430)
                cid = b.id("cl")
                inside += (f'<img id="{cid}" src="assets/paper/cloud{j}.png" style="position:absolute;'
                           f'left:{80 + j * wd * 0.31 + b.r(-40, 40):.0f}px;top:{h * (0.10 + 0.22 * ((j * 2) % 3)) + b.r(-10, 10):.0f}px;width:{cw:.0f}px">')
                b.js.append(f'tl.fromTo("#{cid}", {{x: 0}}, {{x: {b.r(60, 130) * (1 if j % 2 else -1):.0f}, duration: {rest + 0.4:.3f}, '
                            f'ease: st("none", {rest + 0.4:.3f})}}, {max(0.0, t - 0.3):.3f});')
        elif what == "night":
            self.use_moon = True
            inside += (f'<img src="assets/paper/moon.png" style="position:absolute;left:{wd * 0.16:.0f}px;top:{h * 0.14:.0f}px;'
                       f'width:{min(260, h * 0.5):.0f}px">')
        inner = (f'<div style="position:relative;width:{wd}px;height:{h:.0f}px;filter:drop-shadow(0 13px 10px rgba(20,14,8,.5))">'
                 f'<div style="position:absolute;left:0;right:0;top:-10px;bottom:-10px;background:url(assets/paper/cream.jpg) center/cover;'
                 f'clip-path:{torn_band(b.rng, amp=3.2)}"></div>'
                 f'<div style="position:absolute;inset:0;{fill}clip-path:{torn_band(b.rng, amp=5.5)};overflow:hidden">{inside}</div></div>')
        bi = self.el(inner, -80, y, wd, 3, style=f"height:{h:.0f}px")
        side = -1500 if b.rng.random() < 0.5 else 1500
        fresh.append((bi, dict(how="side", frm=side, rot=beat.get("band_rot", b.r(-2.2, 2.2)), dur=0.36,
                               drift=-40 if side < 0 else 40), t + 0.1))

    def sky_pieces(self, n, t, fresh):
        b = self.b
        self.use_clouds = True
        for j in range(n):
            w = b.r(360, 560)
            x = b.r(-80, self.W - w + 80)
            y = self.H * (0.05 + 0.5 * j / max(1, n - 1)) + b.r(-40, 40) if n > 1 else self.H * 0.12
            ci = self.el(f'<img src="assets/paper/cloud{j % 4}.png">', x, y, w, 2)
            fresh.append((ci, dict(how="side", frm=-1400 if j % 2 else 1400, rot=b.r(-2, 2), dur=0.4, sfx=j == 0,
                               drift=b.r(50, 110) * (1 if j % 2 else -1)), t + 0.05 + j * 0.1))

    def headline(self, beat, t, dur, fresh):
        """Stacked paper strips, one line at a time: each lands on the word it starts with."""
        b = self.b
        lines = beat["headline"]
        lines = lines.split("|") if isinstance(lines, str) else lines
        x0, y0, x1, y1 = self.box
        fat = beat.get("headline_font", "fat") == "fat"
        fn = "AbrilFatface-Regular.ttf" if fat else "Anton-Regular.ttf"
        widest = max(text_ratio(fn, ln.upper()) for ln in lines)
        size = min(beat.get("headline_size", 150), (self.W - 210) / max(0.1, widest))
        step = max(size * 1.13, size + 30)
        total = step * len(lines)
        at = beat.get("headline_at", "low")
        top = {"low": self.cap_y - 60 - total, "top": y0 + 10, "mid": (y0 + y1) / 2 - total / 2}.get(at, at if isinstance(at, (int, float)) else y0)
        if at == "low" and self.hero_box:
            # a full-frame subject: the strips sit across the chest, below the face and above the platform buttons
            hx, hy, hw, hh = self.hero_box
            z0 = hy + hh * beat.get("face", 0.48)
            z1 = (self.cap_y - 50) if beat.get("cap", True) else self.H - (300 if self.v else 70)
            z1 = max(z1, z0 + 120)
            if total > z1 - z0:
                step = (z1 - z0) / len(lines)
                size = min(step / 1.13, step - 30)
                total = step * len(lines)
            top = z0 + (z1 - z0 - total) * 0.35
        cyc = beat.get("headline_colors") or [c for c in ("mustard", "", "ink", "red") if c != self.cur_bg and not (c == "" and self.cur_bg in ("cream", "newsprint"))]
        cx = (x0 + x1) / 2
        ptr, prev = 0, t + 0.05
        for j, ln in enumerate(lines):
            kind = (cyc[j % len(cyc)] + (" fat" if fat else "")).strip()
            si = self.strip(ln, cx + (b.r(8, 34) if j % 2 else -b.r(8, 34)), top + j * step, size, 44 + j, kind=kind)
            ons = beat.get("headline_on") or []
            first = ons[j] if j < len(ons) else (ln.split()[0] if ln.split() else "")
            hit = self.find_word(first, ptr) if beat.get("headline_sync", True) else None
            if hit:
                ptr = hit[0] + 1
            te = (hit[1] + 0.12) if hit else prev + 0.4
            prev = te
            # the strip is slapped down on the word, it does not slide in
            fresh.append((si, dict(how="slap", rot=b.r(1.2, 3.6) * (-1 if j % 2 == 0 else 1)), te + 0.06))

    def letters(self, beat, t, dur, fresh):
        """One huge word, printed letter by letter, slightly off register like a two-colour press."""
        b = self.b
        word = str(beat["letters"]).upper()
        x0, y0, x1, y1 = self.box
        fn = "AbrilFatface-Regular.ttf"
        ratio = text_ratio(fn, word)
        size = min(beat.get("letters_size", 430), (self.W - 110) / max(0.1, ratio))
        col = rgb(beat["letters_color"]) if beat.get("letters_color") else (CREAM if self.dark else INK)
        # the second ink of the press, printed a few pixels off
        off = rgb(beat["letters_offset"]) if beat.get("letters_offset") else (
            rgb("teal") if beat.get("letters_color") == "red" else (RED if self.dark else rgb("mustard")))
        at = beat.get("letters_at", "top")
        y = {"top": y0 - 30, "mid": (y0 + y1) / 2 - size / 2, "low": self.cap_y - 70 - size}.get(at, at if isinstance(at, (int, float)) else y0)
        x = self.W / 2 - ratio * size / 2
        wt = self.word_time(beat.get("letters_on"))
        ta = (wt + 0.15) if wt else t + 0.4
        if beat.get("letters_kicker"):
            # a small condensed line riding on the giant word: the size contrast is the design
            ks = beat.get("kicker_size", max(54, size * 0.2))
            kshade = INK if self.dark else "rgba(239,232,218,.85)"
            ki = self.el(f'<div class="kick" style="font-size:{ks:.0f}px;color:{col};text-shadow:3px 4px 0 {kshade}">{beat["letters_kicker"]}</div>',
                         x + 6, y - ks * 0.2, text_ratio("Anton-Regular.ttf", beat["letters_kicker"].upper()) * ks + 40, 33)
            fresh.append((ki, dict(how="print", rot=b.r(-1.5, 1.5)), ta - 0.3))
            y += ks * 0.62
        d = max(5, size * 0.02)
        n = 0
        for ch in word:
            w = text_ratio(fn, ch) * size
            if ch != " ":
                i = self.el(f'<div class="big" style="font-size:{size:.0f}px;color:{col};text-shadow:{-d:.0f}px {d * 0.7:.0f}px 0 {off}, '
                            f'{d * 1.6:.0f}px {d * 2.2:.0f}px 0 rgba(20,14,8,.28)">{ch}</div>', x, y + b.r(-9, 9), w, 34 + n)
                fresh.append((i, dict(how="print", rot=b.r(-3.5, 3.5)), ta + n * 0.1))
                n += 1
            x += w

    def tags_on(self, beat, t, dur, fresh):
        """Small paper tags anywhere on the frame: {"text", "at": [fx, fy], "color", "on": spoken word}."""
        b = self.b
        for j, tg in enumerate(beat["tags"]):
            fat = tg.get("font", "fat") == "fat"
            kind = (tg.get("color", "red") + (" fat" if fat else "")).strip()
            si = self.strip(tg["text"], tg["at"][0] * self.W, tg["at"][1] * self.H, tg.get("size", 58), 48 + j, kind=kind)
            wt = self.word_time(tg.get("on"))
            fresh.append((si, dict(how="slap", rot=tg.get("rot", b.r(-6, 6))), (wt + 0.16) if wt else t + 0.7 + j * 0.35))

    def notes(self, beat, t, dur, fresh):
        """Marker handwriting with a drawn arrow: {"text", "at": [fx, fy], "to": [fx, fy], "on": spoken word}."""
        b = self.b
        for j, n in enumerate(beat["notes"]):
            ax, ay = n["at"][0] * self.W, n["at"][1] * self.H
            size = n.get("size", 66)
            col = rgb(n["color"]) if n.get("color") else (CREAM if self.dark else INK)
            txt = n["text"].replace("|", "<br>")
            # the note is written on, one character per pose, by a marker
            chars, cn = [], 0
            for ch in n["text"]:
                if ch == "|":
                    chars.append("<br>")
                else:
                    chars.append(f'<span class="c c{cn}">{ch}</span>')
                    cn += 1
            ni = self.el(f'<div style="position:absolute;left:0;top:0;transform:translate(-50%,-50%)">'
                         f'<div class="note" style="font-size:{size}px;color:{col}">{"".join(chars)}</div></div>', ax, ay, 0, 52 + j)
            wt = self.word_time(n.get("on"))
            te = (wt + 0.12) if wt else t + 0.6 + j * 0.5
            fresh.append((ni, dict(how="set", rot=n.get("rot", b.r(-7, 7))), te))
            per = min(1 / 24, 0.5 / max(1, cn))
            for c in range(cn):
                b.js.append(f'tl.set("#{ni} .c{c}", {{opacity: 1}}, {max(0.0, te - 0.18) + c * per:.3f});')
            b.ev(max(0.0, te - 0.18), "draw", g=0.6)
            if n.get("to"):
                tx, ty = n["to"][0] * self.W, n["to"][1] * self.H
                dx, dy = tx - ax, ty - ay
                L = math.hypot(dx, dy) or 1
                ux, uy = dx / L, dy / L
                rows = txt.count("<br>") + 1
                off = min(L * 0.4, max(size * 0.9 * rows, abs(ux) * len(n["text"]) * size * 0.2) + 24)
                sx, sy = ax + ux * off, ay + uy * off
                ex, ey = tx - ux * 18, ty - uy * 18
                bend = n.get("bend", 0.22) * (1 if j % 2 == 0 else -1)
                mx, my = (sx + ex) / 2 - uy * L * bend, (sy + ey) / 2 + ux * L * bend
                hx, hy = ex - mx, ey - my
                hl = math.hypot(hx, hy) or 1
                hx, hy = hx / hl, hy / hl
                a1 = (ex - (hx * 0.86 - hy * 0.5) * 44, ey - (hy * 0.86 + hx * 0.5) * 44)
                a2 = (ex - (hx * 0.86 + hy * 0.5) * 44, ey - (hy * 0.86 - hx * 0.5) * 44)
                ai = self.el(f'<svg viewBox="0 0 {self.W} {self.H}" width="{self.W}" height="{self.H}" style="overflow:visible">'
                             f'<path class="sh" d="M{sx:.0f},{sy:.0f} Q{mx:.0f},{my:.0f} {ex:.0f},{ey:.0f}" fill="none" stroke="{col}" '
                             f'stroke-width="9" stroke-linecap="round" pathLength="1" stroke-dasharray="1" stroke-dashoffset="1"/>'
                             f'<path class="hd" d="M{a1[0]:.0f},{a1[1]:.0f} L{ex:.0f},{ey:.0f} L{a2[0]:.0f},{a2[1]:.0f}" fill="none" stroke="{col}" '
                             f'stroke-width="9" stroke-linecap="round" stroke-linejoin="round" opacity="0"/></svg>', 0, 0, self.W, 51 + j)
                ta = te - 0.18 + cn * per + 0.08  # the arrow is drawn once the writing is done
                b.js.append(f'tl.fromTo("#{ai} .sh", {{strokeDashoffset: 1}}, {{strokeDashoffset: 0, duration: .42, ease: st("power1.inOut", .42)}}, {ta:.3f});')
                b.js.append(f'tl.set("#{ai} .hd", {{opacity: 1}}, {ta + 0.42:.3f});')
                fresh.append((ai, dict(how="set"), ta + 0.18))
                b.ev(ta, "draw", g=0.7)

    def _labels(self, beat, t, dur, fresh, top, bottom, cx):
        b = self.b
        x0, y0, x1, y1 = self.box
        if beat.get("label"):
            size = beat.get("label_size", 110 if len(beat["label"]) <= 14 else 84)
            ly = max(y0, top - size - 70)
            li = self.strip(beat["label"], cx + b.r(-20, 20), ly, size, 40, kind=beat.get("label_kind", ""))
            fresh.append((li, dict(how="slap", rot=b.r(-2.5, 2.5)), t + 0.42))
        if beat.get("tag"):
            ty = min(y1 - 70, bottom - 30)
            ti = self.strip(beat["tag"], cx + b.r(-40, 40), ty, 46, 41, kind="type")
            fresh.append((ti, dict(how="drop", rot=b.r(-3, 3)), t + 0.5))
        if beat.get("stamp"):
            si = self.stamp(beat["stamp"], cx + 170, min(y1 - 220, bottom - 200), beat.get("stamp_size", 96), 60)
            word_t = self.word_time(beat.get("stamp_on"))
            ta = word_t if word_t else t + min(dur * 0.6, 1.6)
            fresh.append((si, dict(how="stamp", rot=b.r(-13, -6)), ta))

    def find_word(self, w, start=0):
        """(index, start time) of a spoken word in this beat: exact match first, then a prefix, then a part."""
        if not w or self.k >= len(self.words):
            return None
        q = re.sub(r"[^a-z0-9]", "", str(w).lower())
        row = self.words[self.k]
        if not q:
            return None
        tests = (lambda a: a == q, lambda a: len(q) >= 3 and a.startswith(q), lambda a: len(q) >= 4 and q in a)
        for test in tests:
            for n in range(start, len(row)):
                if test(re.sub(r"[^a-z0-9]", "", row[n]["w"].lower())):
                    return n, row[n]["s"]
        return None

    def word_time(self, w, start=0):
        hit = self.find_word(w, start)
        return hit[1] if hit else None

    # ----- whole film -----
    def build(self):
        b = self.b
        beats = self.s["beats"]
        self.maps, self.pins, self.tags = [], [], []
        self.need_band, self.use_clouds, self.use_moon, self.bgs = set(), False, False, []
        self.blurs = []
        total = self.total
        scenes_html = []
        # camera whip-pans with motion blur by default (the old paper slide-ins are still "right", "up", "left", "down")
        trans_cycle = ["whip-left", "whip-up", "whip-right", "cut", "whip-down", "whip-left", "whip-up"]
        for k, (beat, tm) in enumerate(zip(beats, self.timing)):
            self.k = k
            t0 = tm["start"]
            nxt = self.timing[k + 1]["start"] if k + 1 < len(beats) else total
            trans = beat.get("transition", trans_cycle[k % len(trans_cycle)] if k else "none")
            s_start = (max(0.0, t0 - (0.06 if trans == "cut" else 0.3))) if k else 0.0
            s_end = min(total, nxt + 0.05) if k + 1 < len(beats) else total
            bg = beat.get("bg", ["mustard", "red", "teal", "newsprint", "kraft", "navy"][k % 6])
            tag = self.press_tag if bg.startswith("press") else ""
            bgf = f"assets/paper/bg_{bg}_{k % 3}{tag}.jpg"
            self.need_bg.add((bg, k % 3, tag))
            self.cur_bg = bg
            self.bgs.append(bg)
            self.scene_end = s_end
            body = self.scene(k, beat, t0, nxt - t0, s_end, trans)
            sid = f"s{k}"
            scenes_html.append(
                f'<div class="clip scene" id="{sid}" data-start="{s_start:.3f}" data-duration="{s_end - s_start:.3f}" '
                f'data-track-index="1" data-track-kind="graphics" data-layout-allow-overlap data-layout-allow-overflow style="z-index:{10 + k}">'
                f'<div class="wipe" id="{sid}w"><div class="cam" id="{sid}c"><img class="bg" src="{bgf}">{"".join(body)}</div></div></div>')
            if k and trans.startswith("whip"):
                # a camera whip-pan: the old scene is flung out, the new one flies in, both smeared along the move
                d = trans.split("-", 1)[1] if "-" in trans else "left"
                ax, sg = ("x", -1) if d == "left" else ("x", 1) if d == "right" else ("y", -1) if d == "up" else ("y", 1)
                span = self.W if ax == "x" else self.H
                wd = 0.3
                bx, by = (90, 0) if ax == "x" else (0, 90)
                prev = f"s{k - 1}w"
                self.blurs += [f"sb{k}", f"sb{k - 1}"]
                b.js.append(f'document.getElementById("{sid}w").style.filter = "url(#sb{k})";')
                b.js.append(f'tl.set("#{prev}", {{filter: "url(#sb{k - 1})"}}, {s_start:.3f});')
                b.js.append(f'tl.fromTo("#{sid}w", {{{ax}: {-sg * span}}}, {{{ax}: 0, duration: {wd}, ease: "power3.out"}}, {s_start:.3f});')
                b.js.append(f'tl.fromTo("#sb{k} feGaussianBlur", {{attr: {{stdDeviation: "{bx} {by}"}}}}, {{attr: {{stdDeviation: "0 0"}}, duration: {wd}, ease: "power2.out"}}, {s_start:.3f});')
                b.js.append(f'tl.to("#{prev}", {{{ax}: {sg * span * 0.55:.0f}, duration: {wd}, ease: "power3.in"}}, {s_start:.3f});')
                b.js.append(f'tl.fromTo("#sb{k - 1} feGaussianBlur", {{attr: {{stdDeviation: "0 0"}}}}, {{attr: {{stdDeviation: "{bx} {by}"}}, duration: {wd}, ease: "power2.in"}}, {s_start:.3f});')
                b.js.append(f'tl.set("#{sid}w", {{filter: "none"}}, {s_start + wd + 0.02:.3f});')
                b.ev(s_start + 0.06, "whip")
            # paper wipe in (stop-motion: 4 poses)
            elif k and trans != "cut":
                fr = {"right": "x: %d" % self.W, "left": "x: %d" % -self.W, "up": "y: %d" % self.H,
                      "down": "y: %d" % -self.H, "drop": "y: %d" % -self.H}[trans]
                b.js.append(f'tl.fromTo("#{sid}w", {{{fr}, rotation: {b.r(-3, 3):.1f}}}, {{x: 0, y: 0, rotation: 0, duration: .3, ease: st("power2.out", .3)}}, {s_start:.3f});')
                b.ev(s_start, "wipe")
            # slow camera push on twos
            b.js.append(f'tl.fromTo("#{sid}c", {{scale: 1}}, {{scale: {1.035 + b.r(0, .02):.3f}, x: {b.r(-14, 14):.0f}, duration: {s_end - s_start:.3f}, ease: st("sine.inOut", {s_end - s_start:.3f})}}, {s_start:.3f});')

        style = self.s.get("captions", "build")
        style = "build" if style is True else style
        caps = self.captions(style) if style and style != "none" else ""
        return scenes_html, caps

    def captions(self, style="build"):
        """Captions from the script's own words. "build": every word is its own paper chip and lands as it is spoken.
        "strip": one strip per phrase with the current word lit. A beat with "cap": false shows none (kinetic beats
        default to none, because the words are already on screen)."""
        b = self.b
        out = []
        chunks, owner = [], []
        beats = self.s["beats"]
        for k, row in enumerate(self.words):
            if not beats[k].get("cap", beats[k].get("kind") != "kinetic"):
                continue
            cur = []
            for w in row:
                cur.append(w)
                end_punct = w["w"][-1:] in ".,;:?!"
                if len(cur) >= 3 or end_punct or (len(cur) >= 2 and len("".join(x["w"] for x in cur)) > 11):
                    chunks.append(cur)
                    owner.append(k)
                    cur = []
            if cur:
                chunks.append(cur)
                owner.append(k)
        for j, ch in enumerate(chunks):
            s = ch[0]["s"] - 0.04
            e = chunks[j + 1][0]["s"] - 0.04 if j + 1 < len(chunks) and chunks[j + 1][0]["s"] - ch[-1]["e"] < 0.6 else ch[-1]["e"] + 0.25
            cid = f"c{j}"
            if style == "build":
                fn = "ArchivoBlack-Regular.ttf"
                texts = [x["w"].upper() for x in ch]
                room = self.W - 110 - len(texts) * 52
                size = min(62, room / max(0.1, sum(text_ratio(fn, w) for w in texts)))
                chips = "".join(f'<span class="cw" id="{cid}w{n}" style="font-size:{size:.0f}px;clip-path:{torn_clip(b.rng, tear=2.5)}">{w}</span>'
                                for n, w in enumerate(texts))
                out.append(f'<div class="clip cap build" id="{cid}" data-start="{s:.3f}" data-duration="{max(0.2, e - s):.3f}" data-track-index="5" '
                           f'data-track-kind="captions" style="z-index:{800 + j}">{chips}</div>')
                for n, x in enumerate(ch):
                    ws = max(s + 0.02, x["s"] - 0.03)
                    nxt_s = ch[n + 1]["s"] - 0.03 if n + 1 < len(ch) else None
                    warm = str(self.bgs[owner[j]]).split("-")[-1] in ("mustard", "kraft", "olive")
                    lit, lit_ink = (RED, CREAM) if warm else (rgb("mustard"), INK)
                    b.js.append(f'tl.set("#{cid}w{n}", {{opacity: 1, background: "{lit}", color: "{lit_ink}"}}, {ws:.3f});')
                    b.js.append(f'tl.fromTo("#{cid}w{n}", {{scale: 1.28, rotation: {b.r(-6, 6):.1f}}}, {{scale: 1, rotation: {b.r(-2.2, 2.2):.1f}, '
                                f'duration: .17, ease: st("power2.out", .17)}}, {ws:.3f});')
                    if nxt_s:
                        b.js.append(f'tl.set("#{cid}w{n}", {{background: "#1f1c19", color: "{CREAM}"}}, {max(ws + 0.1, nxt_s):.3f});')
                continue
            spans = "".join(f'<span class="w" id="{cid}w{n}">{x["w"].upper()}</span>' for n, x in enumerate(ch))
            clip = torn_clip(b.rng, tear=2)
            out.append(f'<div class="clip cap" id="{cid}" data-start="{s:.3f}" data-duration="{max(0.2, e - s):.3f}" data-track-index="5" '
                       f'data-track-kind="captions" style="z-index:{800 + j}"><div class="strip ink" id="{cid}s" style="clip-path:{clip};display:inline-block">{spans}</div></div>')
            b.js.append(f'tl.fromTo("#{cid}s", {{scale: 1.18, rotation: {b.r(-3, 3):.1f}}}, {{scale: 1, rotation: {b.r(-1.5, 1.5):.1f}, duration: .17, ease: st("power2.out", .17)}}, {s:.3f});')
            for n, x in enumerate(ch):
                b.js.append(f'tl.set("#{cid}w{n}", {{color: "{rgb("mustard")}"}}, {x["s"]:.3f});')
                b.js.append(f'tl.set("#{cid}w{n}", {{color: "{CREAM}"}}, {x["e"] + 0.02:.3f});')
        return "".join(out)


def write_project(story, timing, words, total, proj, images):
    f = Film(story, timing, words, proj, images)
    f.total = total
    f.need_bg = set()
    scenes, caps = f.build()
    W, H = f.W, f.H
    # backgrounds + shared paper
    pd = os.path.join(proj, "assets", "paper")
    os.makedirs(pd, exist_ok=True)
    said = [bt.get("say", "") for bt in story["beats"]]
    for bg, v, tag in f.need_bg:
        p = os.path.join(pd, f"bg_{bg}_{v}{tag}.jpg")
        if not os.path.exists(p):
            make_world(bg, W, H, seed=stable(bg) + v, title=story.get("title", ""), lines=said).save(p, quality=90)
    for name, tag in f.need_band:
        p = os.path.join(pd, f"band_{name}{tag}.jpg")
        if not os.path.exists(p):
            make_world(name, W + 160, int(H * 0.5), seed=stable(name) + 5, title=story.get("title", ""), lines=said).save(p, quality=90)
    if f.use_clouds:
        for v in range(4):
            p = os.path.join(pd, f"cloud{v}.png")
            if not os.path.exists(p):
                cloud(560 + v * 40, 250 + (v % 2) * 30, seed=20 + v).save(p)
    if f.use_moon and not os.path.exists(os.path.join(pd, "moon.png")):
        moon(300, 4).save(os.path.join(pd, "moon.png"))
    for c in ("cream", "red", "mustard", "teal", "navy", "newsprint", "kraft"):
        p = os.path.join(pd, f"{c}.jpg")
        if not os.path.exists(p):
            card(c, 900, 600, seed=5).save(p, quality=90)
    for v in range(4):
        p = os.path.join(pd, f"scrap{v}.png")
        if not os.path.exists(p):
            col = ["newsprint", "newsprint", "kraft", "cream"][v]
            scrap(520 if v < 2 else 380, 420 if v < 2 else 300, seed=40 + v, color=col).save(p)
    if not os.path.exists(os.path.join(pd, "tape.png")):
        tape(220, 64, 3).save(os.path.join(pd, "tape.png"))
    if not os.path.exists(os.path.join(pd, "grain.png")):
        rng = np.random.default_rng(2)
        g = (rng.random((300, 300)) * 255).astype(np.uint8)
        Image.fromarray(255 - (g > 200).astype(np.uint8) * 90 - (rng.random((300, 300)) * 40).astype(np.uint8)).convert("L").save(os.path.join(pd, "grain.png"))
    if not os.path.exists(os.path.join(pd, "grunge.png")):
        rng = np.random.default_rng(9)
        from paper import _noise
        n = _noise(420, 420, rng, scales=(1, 3, 12), weights=(0.5, 0.3, 0.2))
        a = np.where(n > 0.38, 255, 0).astype(np.uint8)
        Image.fromarray(a).save(os.path.join(pd, "grunge.png"))

    # light through a window and the folds of the paper, over every scene and under the captions
    light = story.get("light", "window")
    light_html = ""
    if light and light != "none":
        lp = os.path.join(pd, f"light_{light}.png")
        if not os.path.exists(lp):
            window_light(W + 600, H + 400, kind=light, seed=7).save(lp)
        light_html += (f'<div id="light" style="position:absolute;left:-300px;top:-200px;width:{W + 600}px;height:{H + 400}px;'
                       f'background:url(assets/paper/light_{light}.png) 0 0/100% 100%;mix-blend-mode:multiply;'
                       f'opacity:{story.get("light_strength", 0.85)};pointer-events:none;z-index:790"></div>')
    if story.get("folds", True):
        fp = os.path.join(pd, "folds.png")
        if not os.path.exists(fp):
            folds(W, H, seed=3).save(fp)
        light_html += ('<div id="folds" style="position:absolute;inset:0;background:url(assets/paper/folds.png) 0 0/100% 100%;'
                       'mix-blend-mode:soft-light;opacity:.75;pointer-events:none;z-index:791"></div>')

    # fonts + libs
    fd = os.path.join(proj, "assets", "fonts")
    os.makedirs(fd, exist_ok=True)
    for fn in os.listdir(os.path.join(HERE, "fonts")):
        shutil.copy(os.path.join(HERE, "fonts", fn), fd)
    jd = os.path.join(proj, "assets", "js")
    os.makedirs(jd, exist_ok=True)
    libs = ["gsap.min.js"] + (["d3-array.min.js", "d3-geo.min.js", "topojson-client.min.js"] if f.maps else [])
    for fn in libs:
        shutil.copy(os.path.join(HERE, "data", fn), jd)

    map_js = ""
    if f.maps:
        world = open(os.path.join(HERE, "data", "countries-110m.json"), encoding="utf-8").read()
        pins = json.dumps([{"pin": p, "map": m, "x": x, "y": y} for p, m, x, y in f.pins])
        tags = json.dumps([{"tag": p, "map": m, "x": x, "y": y} for p, m, x, y in f.tags])
        map_js = f"""
const WORLD = {world};
const COUNTRIES = topojson.feature(WORLD, WORLD.objects.countries).features;
const MAPS = {json.dumps(f.maps)};
const PINS = {pins}, TAGS = {tags};
for (const m of MAPS) {{
  const svg = document.getElementById(m.id);
  const hit = COUNTRIES.filter(c => (m.highlight || [m.country]).includes(c.properties.name));
  // mainland only (France's overseas parts would zoom the map out to the Atlantic)
  const main = hit.map(c => {{ if (c.geometry.type !== "MultiPolygon") return c;
    const parts = c.geometry.coordinates.map(cs => ({{type: "Polygon", coordinates: cs}}));
    parts.sort((a, b) => d3.geoArea(b) - d3.geoArea(a));
    return {{type: "Feature", geometry: parts[0]}}; }});
  let fitTo = main.length ? {{type: "FeatureCollection", features: main}} : null;
  if (m.bbox) fitTo = {{type: "Feature", geometry: {{type: "MultiPoint", coordinates: m.bbox}}}};
  const pad = m.pad || 150;
  const proj = d3.geoMercator().fitExtent([[pad, pad], [m.w - pad, m.h - pad]], fitTo || {{type: "Sphere"}});
  if (m.zoom) proj.scale(proj.scale() * m.zoom);
  const path = d3.geoPath(proj);
  const NS = "http://www.w3.org/2000/svg";
  for (const c of COUNTRIES) {{
    const p = document.createElementNS(NS, "path"); p.setAttribute("d", path(c) || "");
    p.setAttribute("fill", "url(#" + m.id + "dots)"); p.setAttribute("stroke", "#1a1714"); p.setAttribute("stroke-width", "2");
    svg.querySelector(".land").appendChild(p);
  }}
  for (const c of hit) {{
    const p = document.createElementNS(NS, "path"); p.setAttribute("d", path(c) || "");
    p.setAttribute("fill", "{RED}"); p.setAttribute("stroke", "#1a1714"); p.setAttribute("stroke-width", "3");
    svg.querySelector(".hit").appendChild(p);
  }}
  m._proj = proj;
}}
for (const p of PINS) {{ const m = MAPS.find(x => x.id === p.map); const [px, py] = m._proj(m.pin);
  const e = document.getElementById(p.pin); e.style.left = (p.x + px - 22) + "px"; e.style.top = (p.y + py - 22) + "px"; }}
for (const p of TAGS) {{ const m = MAPS.find(x => x.id === p.map); const [px, py] = m._proj(m.pin);
  const e = document.getElementById(p.tag); const right = px > m.w * 0.55;
  e.style.left = (p.x + px + (right ? -34 : 34)) + "px"; e.style.top = (p.y + py - 40) + "px";
  if (right) {{ const inner = e.querySelector(".boil > div"); inner.style.transform = "translateX(-100%)"; }} }}
"""
    scripts = "".join(f'<script src="assets/js/{fn}"></script>' for fn in libs)
    css = CSS % {"W": W, "H": H, "RED": RED, "CAPY": f.cap_y}
    head_js = JS_HEAD % {"W": W, "H": H}
    tail_js = f"""
tl.fromTo("#grain", {{"--gx": 0}}, {{"--gx": 1, duration: {total:.3f}, ease: jit(5, {total:.3f})}}, 0);
tl.fromTo("#grain", {{"--gy": 0}}, {{"--gy": 1, duration: {total:.3f}, ease: jit(9, {total:.3f})}}, 0);
if (document.getElementById("light")) tl.fromTo("#light", {{x: 0, y: 0}}, {{x: 140, y: 60, duration: {total:.3f}, ease: "sine.inOut"}}, 0);
// the ink is never the same twice: every piece of type is re-inked six times a second
tl.fromTo("feTurbulence.inkseed", {{attr: {{seed: 1}}}}, {{attr: {{seed: {1 + max(1, round(total * 6))}}}, duration: {total:.3f}, ease: "steps({max(1, round(total * 6))})"}}, 0);
window.__timelines = window.__timelines || {{}};
window.__timelines["main"] = tl;
"""
    # "ink": 0 = clean type, 1 = printed (default), 2 = rough
    ink_a, ink_b = story.get("ink", 1.0) * 2.4, story.get("ink", 1.0) * 4.5
    audio = '<audio id="mix" class="clip" data-start="0" data-duration="%.3f" data-track-index="9" src="assets/audio/mix.wav"></audio>' % total
    html = f"""<!doctype html>
<html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width={W}, height={H}">
{scripts}
<style>{css}</style></head>
<body><div id="root" data-composition-id="main" data-start="0" data-duration="{total:.3f}" data-width="{W}" data-height="{H}" data-fps="30">
{''.join(scenes)}
{caps}
{light_html}
<div id="grain"></div><div id="vig"></div>
<svg width="0" height="0" style="position:absolute" aria-hidden="true"><defs>
{"".join(f'<filter id="{fid}" x="-30%" y="-30%" width="160%" height="160%"><feGaussianBlur stdDeviation="0 0"/></filter>' for fid in dict.fromkeys(f.blurs))}
<filter id="ink" x="-4%" y="-10%" width="108%" height="120%" color-interpolation-filters="sRGB">
<feTurbulence class="inkseed" type="fractalNoise" baseFrequency="0.4" numOctaves="2" seed="1" result="n"/>
<feDisplacementMap in="SourceGraphic" in2="n" scale="{ink_a:.1f}" xChannelSelector="R" yChannelSelector="G" result="d"/>
<feTurbulence class="inkseed" type="fractalNoise" baseFrequency="0.85" numOctaves="1" seed="1" result="s"/>
<feColorMatrix in="s" type="matrix" values="0 0 0 0 0  0 0 0 0 0  0 0 0 0 0  0 0 0 -9 7.1" result="m"/>
<feComposite in="d" in2="m" operator="in"/></filter>
<filter id="inkb" x="-4%" y="-6%" width="108%" height="112%" color-interpolation-filters="sRGB">
<feTurbulence class="inkseed" type="fractalNoise" baseFrequency="0.22" numOctaves="2" seed="1" result="n"/>
<feDisplacementMap in="SourceGraphic" in2="n" scale="{ink_b:.1f}" xChannelSelector="R" yChannelSelector="G" result="d"/>
<feTurbulence class="inkseed" type="fractalNoise" baseFrequency="0.55" numOctaves="2" seed="1" result="s"/>
<feColorMatrix in="s" type="matrix" values="0 0 0 0 0  0 0 0 0 0  0 0 0 0 0  0 0 0 -9 7.0" result="m"/>
<feComposite in="d" in2="m" operator="in"/></filter>
</defs></svg>
{audio}
</div>
<script>
{map_js}
{head_js}
{chr(10).join(f.b.js)}
{tail_js}
</script></body></html>"""
    open(os.path.join(proj, "index.html"), "w", encoding="utf-8").write(html)
    json.dump(f.b.events, open(os.path.join(proj, "sfx_events.json"), "w"), indent=0)
    return f.b.events

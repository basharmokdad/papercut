"""Worlds: full-frame printed paper to build a scene on, and the loose pieces that live in it.

Everything is generated from a seed, so the engine still ships with no image files to license:
a newspaper page set from the film's own words, a printed sky with paper clouds, a night sky with a
cut-out moon, rings of torn card, graph paper.
"""
import os
import textwrap

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from paper import CARDS, _noise, card, with_shadow

FONTS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fonts")
SKY = (62, 132, 208)
NIGHT = (22, 36, 74)
# backgrounds that need light ink on top of them
DARK = {"red", "teal", "navy", "ink", "olive", "press-dark", "night", "sky", "rings-red", "rings-navy", "rings-teal"}


def font(name, size):
    return ImageFont.truetype(os.path.join(FONTS, name), int(size))


def text_ratio(name, text):
    """Width of `text` in em for a font file: lets the builder fit a headline without guessing."""
    return font(name, 200).getlength(text) / 200.0


def screen(tone, cell=8):
    """A halftone dot screen for a darkness map (float 0..1). Returns float 0..1, 1 = ink."""
    h, w = tone.shape
    sup = 2
    W, H = w * sup, h * sup
    im = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(im)
    c = cell * sup
    for y in range(0, H + c, c):
        ox = (c // 2) if (y // c) % 2 else 0
        for x in range(-c, W + c, c):
            v = tone[min(h - 1, max(0, y // sup)), min(w - 1, max(0, (x + ox) // sup))]
            r = c * 0.62 * float(np.sqrt(max(0.0, v)))
            if r > 0.7:
                d.ellipse([x + ox - r, y - r, x + ox + r, y + r], fill=255)
    return np.asarray(im.resize((w, h), Image.LANCZOS), np.float32) / 255


def sky(w, h, seed=0, color=SKY):
    """Printed blue sky: card, lighter towards the horizon, a faint dot screen."""
    rng = np.random.default_rng(seed)
    base = np.asarray(card(color, w, h, seed), np.float32)
    yy = np.linspace(0, 1, h, dtype=np.float32)[:, None]
    lift = 0.30 * yy ** 1.6
    base = base + (255 - base) * lift[..., None]
    tone = (0.10 + 0.10 * _noise(h, w, rng, scales=(90, 200), weights=(0.5, 0.5))).astype(np.float32)
    dots = screen(tone, cell=7)
    base *= (1 - 0.22 * dots[..., None])
    return Image.fromarray(np.clip(base, 0, 255).astype(np.uint8))


def night(w, h, seed=0):
    """Printed night sky: navy card with paper-punch stars."""
    rng = np.random.default_rng(seed)
    im = card(NIGHT, w, h, seed)
    d = ImageDraw.Draw(im, "RGBA")
    for _ in range(int(w * h / 14000)):
        x, y = rng.random() * w, rng.random() * h
        r = 1.2 + rng.random() ** 3 * 4.5
        d.ellipse([x - r, y - r, x + r, y + r], fill=(240, 233, 219, int(120 + rng.random() * 135)))
    return im


def cloud(w=520, h=260, seed=0):
    """A paper cloud: torn white card, dotted shading underneath, soft cast shadow. RGBA."""
    rng = np.random.default_rng(seed)
    m = Image.new("L", (w, h), 0)
    d = ImageDraw.Draw(m)
    base_y = h * 0.80
    n = 5 + int(rng.integers(0, 3))
    peak = 0.25 + rng.random() * 0.5          # where the tallest puff sits, so no two clouds match
    for i in range(n):
        f = (i + 0.5) / n
        cx = w * (0.13 + 0.74 * f) + rng.normal(0, w * 0.02)
        r = h * (0.13 + 0.25 * np.exp(-((f - peak) / 0.28) ** 2) + rng.random() * 0.09)
        d.ellipse([cx - r * 1.05, base_y - r * 1.9, cx + r * 1.05, base_y + r * 0.1], fill=255)
    d.rounded_rectangle([w * 0.05, base_y - h * 0.17, w * 0.95, base_y + h * 0.06], radius=int(h * 0.11), fill=255)
    # rough torn edge: blur, add fibre noise, threshold
    soft = np.asarray(m.filter(ImageFilter.GaussianBlur(5)), np.float32) / 255
    soft += (_noise(h, w, rng, scales=(2, 6), weights=(0.6, 0.4)) - 0.5) * 0.30
    mask = (soft > 0.5).astype(np.uint8) * 255
    yy = np.linspace(0, 1, h, dtype=np.float32)[:, None] * np.ones((1, w), np.float32)
    tone = np.clip((yy - 0.50) * 1.9, 0, 1) ** 1.4 * 0.55 + 0.05 * _noise(h, w, rng, scales=(30, 80), weights=(0.5, 0.5)) * (yy > 0.4)
    dots = screen(tone.astype(np.float32), cell=6)
    body = np.asarray(card((246, 243, 236), w, h, seed + 1), np.float32)
    ink = np.array((96, 124, 164), np.float32)
    body = body * (1 - 0.78 * dots[..., None]) + ink[None, None, :] * (0.78 * dots[..., None])
    out = Image.fromarray(np.clip(body, 0, 255).astype(np.uint8)).convert("RGBA")
    out.putalpha(Image.fromarray(mask))
    return with_shadow(out, pad=20, off=(5, 9), blur=8, alpha=0.30)


def moon(size=260, seed=0):
    """A cut-out paper moon with dotted craters. RGBA."""
    rng = np.random.default_rng(seed)
    m = Image.new("L", (size, size), 0)
    ImageDraw.Draw(m).ellipse([6, 6, size - 6, size - 6], fill=255)
    tone = np.clip(_noise(size, size, rng, scales=(18, 46), weights=(0.55, 0.45)) - 0.42, 0, 1) * 1.5
    dots = screen(tone.astype(np.float32), cell=6)
    body = np.asarray(card((244, 238, 220), size, size, seed), np.float32)
    body *= (1 - 0.55 * dots[..., None])
    out = Image.fromarray(np.clip(body, 0, 255).astype(np.uint8)).convert("RGBA")
    out.putalpha(m)
    return with_shadow(out, pad=24, off=(4, 8), blur=10, alpha=0.4)


def rings(w, h, a="red", b="cream", seed=0, center=(0.5, 0.40), band=118):
    """Layers of torn card around a centre. Each ring casts a shadow on the next one down."""
    rng = np.random.default_rng(seed)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    cx, cy = center[0] * w, center[1] * h
    dist = np.hypot((xx - cx) * 1.06, (yy - cy) * 0.94)
    ang = np.arctan2(yy - cy, xx - cx)
    wob = sum(np.sin(ang * k + rng.random() * 6.28) * (26 / k) for k in (2, 3, 5, 7))
    dist = dist + wob + (_noise(h, w, rng, scales=(3, 9, 40), weights=(0.3, 0.3, 0.4)) - 0.5) * 26
    dist = np.maximum(dist, 2.0)  # no stray fleck at the very centre
    idx = np.floor(dist / band).astype(int)
    frac = (dist / band) - idx
    ca = np.asarray(card(a, w, h, seed + 1), np.float32)
    cb = np.asarray(card(b, w, h, seed + 2), np.float32)
    img = np.where((idx % 2 == 0)[..., None], ca, cb)
    shade = 1 - 0.34 * np.exp(-frac * 9.0)
    img = img * shade[..., None]
    edge = np.clip(1 - np.abs(frac - 0.985) / 0.02, 0, 1)  # the white fibre of a torn edge
    img = img + (np.array((246, 240, 228), np.float32) - img) * (0.75 * edge[..., None])
    return Image.fromarray(np.clip(img, 0, 255).astype(np.uint8))


def grid(w, h, seed=0, cell=54):
    """Graph paper."""
    im = card("cream", w, h, seed).convert("RGBA")
    d = ImageDraw.Draw(im, "RGBA")
    for i, x in enumerate(range(0, w, cell)):
        d.line([(x, 0), (x, h)], fill=(70, 110, 150, 90 if i % 5 == 0 else 42), width=3 if i % 5 == 0 else 1)
    for i, y in enumerate(range(0, h, cell)):
        d.line([(0, y), (w, y)], fill=(70, 110, 150, 90 if i % 5 == 0 else 42), width=3 if i % 5 == 0 else 1)
    return im.convert("RGB")


def press(w, h, title="", lines=(), dark=False, seed=0):
    """A newspaper page set from the film's own title and script: real words, never invented headlines.

    It is a background, so it is low contrast, slightly rotated and bleeds off every edge."""
    rng = np.random.default_rng(seed)
    W, H = int(w * 1.16), int(h * 1.12)
    paper = (34, 32, 30) if dark else CARDS["newsprint"]
    ink = (92, 88, 82) if dark else (58, 52, 46)
    im = card(paper, W, H, seed).convert("RGBA")
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    a_head, a_body = (235, 150) if dark else (190, 120)
    lines = [x.strip() for x in lines if x and x.strip()]
    text = " ".join(lines) or title or "Paper, scissors, motion."
    title = (title or "Late edition").upper()
    m = int(W * 0.05)

    def headline(y, s, size):
        f = font("AbrilFatface-Regular.ttf", size)
        for ln in textwrap.wrap(s, width=max(8, int((W - 2 * m) / (size * 0.60)))):
            d.text((m, y), ln, font=f, fill=ink + (a_head,))
            y += int(size * 1.02)
        return y + int(size * 0.2)

    def columns(y, y_end, k, cols=4):
        f = font("SpecialElite-Regular.ttf", W / 78)
        lh = int(f.size * 1.34)
        gap = int(W * 0.022)
        cw = (W - 2 * m - gap * (cols - 1)) / cols
        chars = max(10, int(cw / (f.size * 0.60)))
        words = text.split()
        for c in range(cols):
            x = m + c * (cw + gap)
            yy_ = y
            start = int(rng.integers(0, max(1, len(words))))
            run = " ".join((words[start:] + words * 60)[:900])
            if (c + k) % 3 == 1:  # one column in three opens with a printed photo block
                bh = int(cw * 0.72)
                tone = (0.25 + 0.5 * _noise(bh, int(cw), rng, scales=(12, 40), weights=(0.5, 0.5))).astype(np.float32)
                dots = screen(tone, cell=6)
                blk = Image.new("RGBA", (int(cw), bh), ink + (0,))
                blk.putalpha(Image.fromarray((dots * a_body).astype(np.uint8)))
                layer.alpha_composite(blk, (int(x), int(yy_)))
                yy_ += bh + lh
            for ln in textwrap.wrap(run, width=chars):
                if yy_ > y_end - lh:
                    break
                d.text((x, yy_), ln, font=f, fill=ink + (a_body,))
                yy_ += lh
            if c:
                d.line([(x - gap / 2, y), (x - gap / 2, y_end - lh)], fill=ink + (70,), width=2)
        return y_end

    y = int(H * 0.035)
    kick = font("Anton-Regular.ttf", W / 40)
    right = "PAPER  /  SCISSORS  /  MOTION"
    d.text((m, y), "LATE EDITION", font=kick, fill=ink + (a_head,))
    d.text((W - m - kick.getlength(right), y), right, font=kick, fill=ink + (a_head,))
    y += int(kick.size * 1.5)
    d.line([(m, y), (W - m, y)], fill=ink + (a_head,), width=5)
    y = headline(y + 14, title, W / 9.5)
    d.line([(m, y), (W - m, y)], fill=ink + (a_head,), width=3)
    y = columns(y + 20, int(H * 0.50), 0)
    d.line([(m, y), (W - m, y)], fill=ink + (a_head,), width=5)
    second = (lines[0] if lines else title).upper().rstrip(".")
    y = headline(y + 14, second, W / 14)
    d.line([(m, y), (W - m, y)], fill=ink + (a_head,), width=3)
    columns(y + 20, H - int(H * 0.02), 1)
    im = Image.alpha_composite(im, layer).convert("RGB")
    im = im.rotate(float(rng.uniform(-3.2, 3.2)), resample=Image.BICUBIC, expand=False)
    l, t = (W - w) // 2, (H - h) // 2
    return im.crop((l, t, l + w, t + h))


def window_light(w, h, kind="window", seed=0):
    """Sunlight through a window falling across the desk: soft diagonal shafts of light, the rest in shade.

    A greyscale image used with multiply: white = untouched, grey = shade. "blinds" gives many thin slats."""
    rng = np.random.default_rng(seed)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    ang = np.deg2rad(-34 + rng.uniform(-4, 4))
    u = xx * np.cos(ang) + yy * np.sin(ang)          # distance across the shafts
    lit = np.zeros((h, w), np.float32)
    if kind == "blinds":
        period = 120
        ph = (u / period) % 1
        lit = np.clip(1 - np.abs(ph - 0.5) / 0.32, 0, 1)
    else:
        # two panes of a window: two wide shafts with a thin glazing bar between them
        # centred on the frame, so the brightest shaft crosses the middle of the picture
        uc = (w / 2) * np.cos(ang) + (h / 2) * np.sin(ang)
        span = min(w, h) * 0.9
        c0 = uc - span * rng.uniform(0.02, 0.1)
        for c, wd in ((c0, span * 0.2), (c0 + span * 0.36, span * 0.12)):
            lit = np.maximum(lit, np.clip(1 - np.abs(u - c) / wd, 0, 1) ** 0.5)
    # a soft edge (light from a real window is never razor sharp) and a slight falloff down the frame
    im = Image.fromarray((lit * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(28))
    lit = np.asarray(im, np.float32) / 255
    fall = 1 - 0.25 * (yy / h)
    shade, light = 0.6, 1.0
    v = shade + (light - shade) * np.clip(lit * fall + 0.06 * _noise(h, w, rng, scales=(60, 160), weights=(0.5, 0.5)), 0, 1)
    return Image.fromarray(np.clip(v * 255, 0, 255).astype(np.uint8), "L")


def folds(w, h, seed=0):
    """A sheet that was folded and flattened again: soft crease lines for a soft-light overlay (128 = no change)."""
    rng = np.random.default_rng(seed)
    a = np.full((h, w), 128.0, np.float32)
    im = Image.fromarray(a.astype(np.uint8))
    d = ImageDraw.Draw(im)
    # one vertical fold and two horizontal ones, a little off true, like a letter folded in thirds
    x = w * rng.uniform(0.45, 0.55)
    dx = rng.uniform(-20, 20)
    d.line([(x, 0), (x + dx, h)], fill=150, width=3)
    d.line([(x + 4, 0), (x + 4 + dx, h)], fill=108, width=5)
    for f in (rng.uniform(0.3, 0.36), rng.uniform(0.64, 0.7)):
        y = h * f
        dy = rng.uniform(-25, 25)
        d.line([(0, y), (w, y + dy)], fill=150, width=3)
        d.line([(0, y + 4), (w, y + 4 + dy)], fill=108, width=5)
    im = im.filter(ImageFilter.GaussianBlur(2.2))
    arr = np.asarray(im, np.float32) + (_noise(h, w, rng, scales=(3, 12, 50), weights=(0.4, 0.3, 0.3)) - 0.5) * 22
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "L")


def world(name, w, h, seed=0, title="", lines=()):
    """Any background by name: a card colour, or one of the printed worlds."""
    if name == "sky":
        return sky(w, h, seed)
    if name == "night":
        return night(w, h, seed)
    if name == "grid":
        return grid(w, h, seed)
    if name in ("press", "press-dark"):
        return press(w, h, title, lines, dark=name.endswith("dark"), seed=seed)
    if name.startswith("rings"):
        a = name.split("-", 1)[1] if "-" in name else "red"
        return rings(w, h, a, "cream", seed)
    return card(name, w, h, seed)


if __name__ == "__main__":
    import sys
    import time
    out = sys.argv[1] if len(sys.argv) > 1 else "."
    os.makedirs(out, exist_ok=True)
    W, H = 1080, 1920
    t = time.time()
    lines = ["September ninth, 1947. Harvard University.",
             "Mid-afternoon, one of the first computers starts making errors.",
             "Seventy-nine years later, we are still debugging."]
    tiles = []
    for n in ["press-dark", "press", "sky", "night", "rings-red", "rings-teal", "grid"]:
        im = world(n, W, H, 3, "The First Computer Bug", lines)
        tiles.append(im.resize((360, 640)))
        print(n, round(time.time() - t, 1))
    sh = Image.new("RGB", (360 * len(tiles), 640))
    for i, x in enumerate(tiles):
        sh.paste(x, (i * 360, 0))
    sh.save(os.path.join(out, "worlds.jpg"), quality=85)
    sk = sky(900, 500, 1).convert("RGBA")
    for i in range(3):
        sk.alpha_composite(cloud(420 + i * 80, 210 + i * 30, seed=i), (40 + i * 260, 40 + i * 110))
    nt = night(900, 500, 1).convert("RGBA")
    nt.alpha_composite(moon(220, 1), (80, 60))
    both = Image.new("RGB", (1800, 500))
    both.paste(sk.convert("RGB"), (0, 0))
    both.paste(nt.convert("RGB"), (900, 0))
    both.save(os.path.join(out, "pieces.jpg"), quality=88)

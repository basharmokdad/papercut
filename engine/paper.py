"""Procedural paper: every texture is generated from a seed, so the engine ships with no image files to license.

Backgrounds are flat coloured card with fibres, stains and print grain. Scraps are blank newsprint with torn edges
and faint halftone, never readable text (invented headlines are what make AI collage look fake).
"""
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

# Card colours. One hot signal colour, earthy neutrals, ink. Keys are what story.json uses for "bg".
CARDS = {
    "red": (196, 48, 38),
    "mustard": (214, 165, 52),
    "teal": (38, 104, 104),
    "navy": (30, 42, 66),
    "newsprint": (226, 216, 194),
    "kraft": (176, 136, 92),
    "ink": (28, 26, 24),
    "cream": (238, 230, 212),
    "pink": (222, 150, 140),
    "olive": (120, 120, 72),
}
INK = (26, 23, 20)
PAPER = (240, 233, 219)


def _noise(h, w, rng, scales=(1, 4, 16, 64), weights=(0.35, 0.3, 0.2, 0.15)):
    """Multi-octave value noise in [0,1], built by upsampling random grids (fast, no extra deps)."""
    out = np.zeros((h, w), np.float32)
    for s, wt in zip(scales, weights):
        gh, gw = max(2, h // s), max(2, w // s)
        g = rng.random((gh, gw)).astype(np.float32)
        im = Image.fromarray((g * 255).astype(np.uint8)).resize((w, h), Image.BICUBIC)
        out += wt * (np.asarray(im, np.float32) / 255)
    return out / sum(weights)


def card(color, w, h, seed=0):
    """A full-frame sheet of coloured card: fibres, soft stains, edge darkening, print grain."""
    rng = np.random.default_rng(seed)
    base = np.array(CARDS.get(color, color), np.float32)
    n = _noise(h, w, rng)
    fib = _noise(h, w, rng, scales=(1, 2), weights=(0.6, 0.4))
    stain = _noise(h, w, rng, scales=(128, 256), weights=(0.5, 0.5))
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    vig = ((xx / w - 0.5) ** 2 + (yy / h - 0.5) ** 2) ** 0.5
    shade = 1 + 0.10 * (n - 0.5) + 0.05 * (fib - 0.5) - 0.10 * np.clip(stain - 0.55, 0, 1) - 0.22 * vig ** 2
    img = np.clip(base[None, None, :] * shade[..., None], 0, 255)
    # sparse fibres: short light and dark hairs
    im = Image.fromarray(img.astype(np.uint8))
    d = ImageDraw.Draw(im, "RGBA")
    for _ in range(int(w * h / 9000)):
        x, y = rng.random() * w, rng.random() * h
        a, ln = rng.random() * np.pi, 4 + rng.random() * 14
        c = (255, 255, 255, 28) if rng.random() < 0.5 else (0, 0, 0, 22)
        d.line([(x, y), (x + np.cos(a) * ln, y + np.sin(a) * ln)], fill=c, width=1)
    return im


def torn_mask(w, h, seed=0, tear=10, edges="tblr"):
    """An RGBA-ready L mask for a rectangle whose chosen edges are torn (jagged, fibrous)."""
    rng = np.random.default_rng(seed)
    pts = []

    def edge(p0, p1, torn):
        n = max(2, int(np.hypot(p1[0] - p0[0], p1[1] - p0[1]) / 4))
        walk = 0.0
        for i in range(n):
            t = i / n
            x, y = p0[0] + (p1[0] - p0[0]) * t, p0[1] + (p1[1] - p0[1]) * t
            if torn:
                # slow wander (the tear line) + fine fibre fuzz, pushed inwards only
                walk = 0.85 * walk + rng.normal(0, 0.55)
                k = np.clip(0.5 + walk * 0.25, 0, 1) * tear + rng.random() * tear * 0.25
                dx, dy = p1[1] - p0[1], -(p1[0] - p0[0])
                L = np.hypot(dx, dy) or 1
                x, y = x + dx / L * k, y + dy / L * k
            pts.append((x, y))

    m = tear
    edge((m, m), (w - m, m), "t" in edges)
    edge((w - m, m), (w - m, h - m), "r" in edges)
    edge((w - m, h - m), (m, h - m), "b" in edges)
    edge((m, h - m), (m, m), "l" in edges)
    mask = Image.new("L", (w, h), 0)
    ImageDraw.Draw(mask).polygon(pts, fill=255)
    return mask


def halftone_field(w, h, seed=0, cell=9, strength=0.22):
    """Faint, unreadable halftone grain: the 'printed newsprint' look without any letters."""
    rng = np.random.default_rng(seed)
    tone = _noise(h, w, rng, scales=(64, 160), weights=(0.6, 0.4))
    sup = 2
    W, H = w * sup, h * sup
    im = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(im)
    c = cell * sup
    for y in range(0, H, c):
        for x in range(0, W, c):
            ox = (c // 2) if (y // c) % 2 else 0
            v = tone[min(h - 1, y // sup), min(w - 1, (x + ox) // sup)]
            r = c * 0.5 * (v * strength * 2)
            if r > 0.6:
                d.ellipse([x + ox - r, y - r, x + ox + r, y + r], fill=255)
    return np.asarray(im.resize((w, h), Image.LANCZOS), np.float32) / 255


def scrap(w, h, seed=0, color="newsprint", dots=True):
    """A torn piece of blank newsprint/card with soft shadow baked in (RGBA, padded for the shadow)."""
    pad = 24
    body = card(color, w, h, seed).convert("RGBA")
    if dots:
        hf = halftone_field(w, h, seed + 7)
        arr = np.asarray(body, np.float32)
        arr[..., :3] *= (1 - 0.35 * hf[..., None])
        body = Image.fromarray(arr.astype(np.uint8), "RGBA")
    mask = torn_mask(w, h, seed, tear=9)
    body.putalpha(mask)
    return with_shadow(body, pad)


def with_shadow(rgba, pad=24, off=(6, 10), blur=9, alpha=0.45):
    """Bake a soft cast shadow under an RGBA cut-out: paper lifted a few millimetres off the table."""
    w, h = rgba.size
    out = Image.new("RGBA", (w + pad * 2, h + pad * 2), (0, 0, 0, 0))
    a = rgba.split()[3]
    sh = Image.new("L", out.size, 0)
    sh.paste(a, (pad + off[0], pad + off[1]))
    sh = sh.filter(ImageFilter.GaussianBlur(blur)).point(lambda v: int(v * alpha))
    shadow = Image.new("RGBA", out.size, (20, 14, 8, 0))
    shadow.putalpha(sh)
    out = Image.alpha_composite(out, shadow)
    layer = Image.new("RGBA", out.size, (0, 0, 0, 0))
    layer.paste(rgba, (pad, pad))
    return Image.alpha_composite(out, layer)


def tape(w=220, h=64, seed=0):
    """Masking tape: translucent cream with torn short ends."""
    rng = np.random.default_rng(seed)
    t = card((222, 208, 170), w, h, seed).convert("RGBA")
    m = torn_mask(w, h, seed, tear=6, edges="lr")
    m = m.point(lambda v: int(v * (0.78 + 0.0 * rng.random())))
    t.putalpha(m)
    return t

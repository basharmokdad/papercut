"""Turn any photo into a hand-cut halftone paper piece.

  photo -> (optional) background removal -> contrast -> halftone dots -> scissor-cut paper border
        -> offset accent silhouette (misregistered print) -> baked soft shadow  -> RGBA PNG

Background removal is rembg (MIT) with the u2net / isnet models (Apache-2.0), on the CPU.
"""
import math

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageOps

from paper import INK, PAPER, CARDS, card, with_shadow

_SESSION = None


def _mask_rembg(img):
    global _SESSION
    from rembg import new_session, remove
    if _SESSION is None:
        _SESSION = new_session("isnet-general-use")
    m = remove(img, session=_SESSION, only_mask=True)
    m = np.asarray(m.convert("L"))
    m = (m > 110).astype(np.uint8)
    # keep the big parts only, close small gaps, fill pinholes
    n, lab, stats, _ = cv2.connectedComponentsWithStats(m, 8)
    if n > 1:
        big = stats[1:, cv2.CC_STAT_AREA].max()
        keep = [i for i in range(1, n) if stats[i, cv2.CC_STAT_AREA] > 0.08 * big]
        m = np.isin(lab, keep).astype(np.uint8)
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9))
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, k)
    cnts, _ = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    filled = np.zeros_like(m)
    cv2.drawContours(filled, cnts, -1, 1, -1)
    return filled * 255


def halftone(gray, mask, cell=8, angle=45, sup=3):
    """Ink dots on paper. gray: float32 0..1 (1 = white). Returns an L image, 0 = ink."""
    h, w = gray.shape
    W, H = w * sup, h * sup
    out = Image.new("L", (W, H), 255)
    d = ImageDraw.Draw(out)
    a = math.radians(angle)
    ca, sa = math.cos(a), math.sin(a)
    c = cell * sup
    diag = int(math.hypot(W, H)) + c
    cx, cy = W / 2, H / 2
    for v in range(-diag // 2, diag // 2, c):
        for u in range(-diag // 2, diag // 2, c):
            x = cx + u * ca - v * sa
            y = cy + u * sa + v * ca
            if 0 <= x < W and 0 <= y < H:
                px, py = int(x / sup), int(y / sup)
                if mask[py, px] < 128:
                    continue
                dark = 1 - gray[py, px]
                r = c * 0.71 * math.sqrt(max(0.0, dark))
                if r > 0.5:
                    d.ellipse([x - r, y - r, x + r, y + r], fill=0)
    return out.resize((w, h), Image.LANCZOS)


def _scissor_poly(mask, grow, seed, eps=5.0):
    """Grow the silhouette into a paper border and cut it with straight scissor strokes."""
    rng = np.random.default_rng(seed)
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (grow * 2 + 1, grow * 2 + 1))
    big = cv2.dilate((mask > 127).astype(np.uint8), k)
    cnts, _ = cv2.findContours(big, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    out = np.zeros_like(big)
    for c in cnts:
        if cv2.contourArea(c) < 400:
            continue
        p = cv2.approxPolyDP(c, eps, True).reshape(-1, 2).astype(np.float32)
        p += rng.normal(0, 1.2, p.shape)  # a hand never cuts perfectly
        cv2.fillPoly(out, [p.astype(np.int32)], 1)
    return out * 255


def cut_piece(src, size=900, cut=True, accent="red", border=14, seed=1, contrast=1.1, cell=None,
              offset=(16, 12), paper=PAPER, dots=True):
    """Return an RGBA PIL image of the finished paper piece (shadow included)."""
    img = Image.open(src).convert("RGB")
    img = ImageOps.exif_transpose(img)
    s = size / max(img.size)
    img = img.resize((max(1, int(img.width * s)), max(1, int(img.height * s))), Image.LANCZOS)
    w, h = img.size

    if cut:
        m = _mask_rembg(img)
    else:
        m = np.full((h, w), 255, np.uint8)

    # tone: autocontrast inside the subject, a little local contrast, then a gentle S-curve
    g = ImageOps.grayscale(img)
    g = ImageOps.autocontrast(g, cutoff=2, mask=Image.fromarray(m))
    g = g.filter(ImageFilter.UnsharpMask(radius=6, percent=60, threshold=2))
    ga = np.asarray(g, np.float32) / 255
    ga = np.clip(0.5 + (ga - 0.5) * contrast, 0, 1)
    ga = ga ** 0.72                      # lift the mids so faces keep detail
    ga = 0.10 + ga * 0.90                # deepest shadow = 90% ink, never a solid black blob

    cell = cell or max(6, int(round(size / 115)))
    if dots:
        ht = np.asarray(halftone(ga, m, cell=cell), np.float32) / 255  # 1 paper, 0 ink
    else:
        # clean print for documents and handwriting: keep the detail, add a fine print grain
        rng = np.random.default_rng(seed)
        ht = np.clip(ga + rng.normal(0, 0.035, ga.shape), 0, 1).astype(np.float32)

    # canvas with room for border + accent offset
    pad = border + max(abs(offset[0]), abs(offset[1])) + 8
    W, H = w + pad * 2, h + pad * 2
    M = np.zeros((H, W), np.uint8)
    M[pad:pad + h, pad:pad + w] = m

    if cut:
        bmask = _scissor_poly(M, border, seed)
    else:
        rng = np.random.default_rng(seed)
        j = lambda: rng.normal(0, 2.5)
        q = [(pad - border + j(), pad - border + j()), (pad + w + border + j(), pad - border + j()),
             (pad + w + border + j(), pad + h + border + j()), (pad - border + j(), pad + h + border + j())]
        im = Image.new("L", (W, H), 0)
        ImageDraw.Draw(im).polygon(q, fill=255)
        bmask = np.asarray(im)

    paper_tex = np.asarray(card(paper, W, H, seed + 3), np.float32)
    rgb = paper_tex.copy()
    ink = np.array(INK, np.float32)
    inner = np.zeros((H, W), np.float32)
    inner[pad:pad + h, pad:pad + w] = (m > 127) * (1 - ht)
    rgb = rgb * (1 - inner[..., None]) + ink[None, None, :] * inner[..., None]

    layers = []
    if accent:
        acol = np.array(CARDS.get(accent, accent), np.float32)
        am = np.roll(np.roll(bmask, offset[1], 0), offset[0], 1)
        acc = Image.new("RGBA", (W, H), tuple(int(v) for v in acol) + (0,))
        acc.putalpha(Image.fromarray(am))
        layers.append(acc)
    piece = Image.fromarray(np.clip(rgb, 0, 255).astype(np.uint8)).convert("RGBA")
    piece.putalpha(Image.fromarray(bmask))
    layers.append(piece)
    comp = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    for L in layers:
        comp = Image.alpha_composite(comp, L)
    bbox = comp.getbbox()
    comp = comp.crop(bbox)
    return with_shadow(comp, pad=26)


if __name__ == "__main__":
    import sys
    cut_piece(sys.argv[1], cut="--rect" not in sys.argv).save(sys.argv[2])

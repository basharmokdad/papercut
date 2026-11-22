"""Find real archive photos you are allowed to use: Wikimedia Commons, public domain and CC0 only by default.

  search "Harvard Mark II"            -> numbered candidates + a contact sheet PNG to look at
  get "File:Harvard_Mark_II.jpg" out  -> downloads it and appends the credit line to CREDITS.txt

CC BY / CC BY-SA images are allowed with --allow-by; their author + licence go into the credits and must be shown.
"""
import json
import os
import re
import sys
import time

import requests
from PIL import Image, ImageDraw, ImageFont

API = "https://commons.wikimedia.org/w/api.php"
UA = {"User-Agent": "PapercutVideoEngine/1.0 (free paper-collage video engine)"}
FREE = re.compile(r"public domain|^pd|cc0|no restrictions", re.I)
BY = re.compile(r"^cc[ -]by", re.I)


def _get(params, tries=4):
    for i in range(tries):
        r = requests.get(API, params=params, headers=UA, timeout=30)
        if r.status_code == 429:
            time.sleep(2 + i * 3)
            continue
        r.raise_for_status()
        return r.json()
    r.raise_for_status()


def _clean(html):
    return re.sub(r"<[^>]+>", "", html or "").strip()


def search(query, limit=24, allow_by=False):
    data = _get({
        "action": "query", "format": "json", "generator": "search", "gsrnamespace": 6,
        "gsrsearch": f"{query} filetype:bitmap", "gsrlimit": limit,
        "prop": "imageinfo", "iiprop": "url|size|mime|extmetadata", "iiurlwidth": 1600,
    })
    out = []
    for p in sorted(data.get("query", {}).get("pages", {}).values(), key=lambda p: p.get("index", 0)):
        ii = (p.get("imageinfo") or [{}])[0]
        md = ii.get("extmetadata", {})
        lic = _clean(md.get("LicenseShortName", {}).get("value"))
        ok = bool(FREE.search(lic)) or (allow_by and bool(BY.search(lic)))
        if not ok or ii.get("width", 0) < 500:
            continue
        out.append({
            "title": p["title"], "license": lic, "w": ii.get("width"), "h": ii.get("height"),
            "thumb": ii.get("thumburl") or ii.get("url"), "page": ii.get("descriptionurl"),
            "artist": _clean(md.get("Artist", {}).get("value"))[:80],
        })
    return out


def _curl(url, out, tries=4):
    """Download with curl: Wikimedia's edge rate-limits python's HTTP fingerprint on upload.wikimedia.org."""
    import subprocess
    code = "000"
    for i in range(tries):
        code = subprocess.run(["curl", "-s", "-L", "-o", out, "-w", "%{http_code}", "-A", UA["User-Agent"], url],
                              capture_output=True, text=True).stdout.strip()
        if code == "200":
            return True
        time.sleep(4 * (i + 1) if code == "429" else 1.5)
    return False


def contact_sheet(cands, path, cols=4, tw=300):
    """Every candidate on one sheet, numbered, so the pick is made by looking. A thumbnail that will not download
    still gets its numbered cell (marked), so the numbers always match the printed list."""
    if not cands:
        print("no free-to-use results: try other words, or --allow-by for CC BY")
        return
    import tempfile
    font = ImageFont.load_default()
    rows = (len(cands) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * tw, rows * (tw + 40)), (30, 30, 30))
    d = ImageDraw.Draw(sheet)
    tmp = os.path.join(tempfile.gettempdir(), "papercut_thumb.bin")
    for i, c in enumerate(cands):
        x, y = (i % cols) * tw, (i // cols) * (tw + 40)
        try:
            if not _curl(c["thumb"].split("?")[0].replace("/1600px-", "/500px-"), tmp, tries=3):
                raise OSError("thumbnail refused")
            im = Image.open(tmp).convert("RGB")
            im.thumbnail((tw - 8, tw - 8))
            sheet.paste(im, (x + 4, y + 4))
        except Exception:
            d.rectangle([x + 4, y + 4, x + tw - 4, y + tw - 4], outline=(120, 60, 60))
            d.text((x + 16, y + tw // 2), "preview failed, open the page:", fill=(200, 120, 120), font=font)
        d.text((x + 6, y + tw + 2), f"{i + 1}. {c['title'][5:40]}", fill=(255, 255, 255), font=font)
        d.text((x + 6, y + tw + 18), f"{c['license'][:30]}  {c['w']}x{c['h']}", fill=(180, 180, 180), font=font)
        time.sleep(0.25)
    sheet.save(path)


def get(title, out, credits="CREDITS.txt", allow_by=False, width=1920):
    data = _get({"action": "query", "format": "json", "titles": title, "prop": "imageinfo",
                 "iiprop": "url|extmetadata", "iiurlwidth": int(width)})  # 1280 / 1920 / 2560 / 3840 are standard steps
    page = next(iter(data["query"]["pages"].values()))
    ii = page["imageinfo"][0]
    md = ii.get("extmetadata", {})
    lic = _clean(md.get("LicenseShortName", {}).get("value"))
    if not (FREE.search(lic) or (allow_by and BY.search(lic))):
        raise SystemExit(f"refused: {title} is '{lic}', not public domain/CC0 (use --allow-by for CC BY)")
    url = (ii.get("thumburl") or ii["url"]).split("?")[0]  # tracking params get rate-limited
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    if not _curl(url, out, tries=5):
        raise SystemExit(f"download failed: {url}")
    time.sleep(1.0)
    import html
    artist = html.unescape(_clean(md.get("Artist", {}).get("value")))[:120]
    line = f"{os.path.basename(out)}: {title} | {artist or 'unknown'} | {lic} | {ii.get('descriptionurl')}\n"
    existing = open(credits, encoding="utf-8").read() if os.path.exists(credits) else ""
    if line not in existing:
        open(credits, "a", encoding="utf-8").write(line)
    return out


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    cmd = sys.argv[1]
    allow = "--allow-by" in sys.argv
    args = [a for a in sys.argv[2:] if not a.startswith("--")]
    if cmd == "search":
        c = search(args[0], allow_by=allow)
        for i, x in enumerate(c, 1):
            print(f"{i:2d}. {x['title']}  [{x['license']}]  {x['w']}x{x['h']}")
        if len(args) > 1:
            contact_sheet(c, args[1])
            json.dump(c, open(args[1] + ".json", "w", encoding="utf-8"), indent=1)
            print("sheet:", args[1])
    elif cmd == "get":
        print(get(args[0], args[1], allow_by=allow))

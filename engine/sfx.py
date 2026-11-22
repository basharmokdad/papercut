"""Paper foley and a documentary bed, synthesised from noise and sine waves: no sample packs, nothing to license.

events: [{"t": 1.23, "k": "slide"|"drop"|"stamp"|"tape"|"wipe"|"type"|"draw"|"pin"}]
"""
import numpy as np
import soundfile as sf
from scipy.signal import butter, sosfilt

SR = 48000


def _bp(x, lo, hi, order=2):
    sos = butter(order, [lo, hi], btype="band", fs=SR, output="sos")
    return sosfilt(sos, x)


def _lp(x, f, order=2):
    return sosfilt(butter(order, f, btype="low", fs=SR, output="sos"), x)


def _env(n, a, d, curve=3.0):
    t = np.arange(n) / SR
    e = np.minimum(1, t / max(a, 1e-4)) * np.exp(-np.maximum(0, t - a) / max(d, 1e-4) * curve / 3)
    return e


def paper_slide(rng, dur=0.28):
    n = int(dur * SR)
    x = rng.standard_normal(n)
    # paper friction: band noise with a grainy amplitude flutter
    flutter = 0.6 + 0.4 * np.abs(_lp(rng.standard_normal(n), 60))
    x = _bp(x, 1800, 7000) * flutter
    e = np.sin(np.linspace(0, np.pi, n)) ** 1.5
    return x * e * 0.35


def tap(rng, dur=0.12, body=180):
    n = int(dur * SR)
    t = np.arange(n) / SR
    click = _bp(rng.standard_normal(n), 2000, 8000) * _env(n, 0.001, 0.012)
    thump = np.sin(2 * np.pi * body * t) * _env(n, 0.002, 0.05)
    return click * 0.5 + thump * 0.45


def stamp(rng):
    n = int(0.3 * SR)
    t = np.arange(n) / SR
    thud = np.sin(2 * np.pi * (95 - 30 * t) * t) * _env(n, 0.002, 0.12)
    slap = _bp(rng.standard_normal(n), 400, 3000) * _env(n, 0.001, 0.03)
    return thud * 0.9 + slap * 0.6


def tape_rip(rng, dur=0.35):
    n = int(dur * SR)
    x = _bp(rng.standard_normal(n), 2500, 9000)
    crackle = (rng.random(n) < 0.02) * rng.standard_normal(n) * 3
    e = _env(n, 0.03, dur * 0.6)
    return (x + _bp(crackle, 1500, 9000)) * e * 0.3


def wipe(rng, dur=0.42):
    n = int(dur * SR)
    x = rng.standard_normal(n)
    lo = _bp(x, 300, 2500)
    hi = _bp(x, 2500, 9000)
    e = np.sin(np.linspace(0, np.pi, n)) ** 0.8
    return (lo * 0.5 + hi * 0.35) * e * 0.5


def typewriter(rng, n_keys=12, rate=14):
    out = np.zeros(int((n_keys / rate + 0.2) * SR))
    for i in range(n_keys):
        k = tap(rng, 0.06, body=900 + rng.random() * 300) * (0.5 + 0.3 * rng.random())
        s = int((i / rate + rng.normal(0, 0.008)) * SR)
        s = max(0, s)
        out[s:s + len(k)] += k[: len(out) - s]
    return out * 0.7


def marker(rng, dur=0.5):
    n = int(dur * SR)
    x = _bp(rng.standard_normal(n), 3000, 10000)
    e = (0.5 + 0.5 * np.sin(np.linspace(0, 6 * np.pi, n))) * np.sin(np.linspace(0, np.pi, n))
    return x * e * 0.18


# ---------------------------------------------------------------------------------------------------------------
# v2: real recordings. Paper, card and book handling from Kenney's CC0 packs (public domain), whooshes and low hits
# rendered with Earshot (MIT). Every hit is a fresh pick, a touch off in pitch and level, so nothing repeats.
# ---------------------------------------------------------------------------------------------------------------
import os as _os

SOUNDS = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "sounds")
BANK = {
    "slide": ["k_card-slide-1", "k_card-slide-3", "k_card-slide-5", "k_card-slide-7", "k_card-shove-1", "k_card-shove-3"],
    "drop": ["k_card-place-1", "k_card-place-2", "k_card-place-3", "k_card-place-4"],
    "heavy": ["k_bookPlace1", "k_bookPlace2", "k_impactSoft_medium_002"],
    "whoosh": ["es_whoosh_flick", "es_whoosh_paper", "es_whoosh_soft"],
    "whip": ["es_whip_big", "es_whip_swell"],
    "flip": ["k_bookFlip1", "k_bookFlip2", "k_bookFlip3"],
    "pop": ["k_click_002", "k_click_004", "k_tick_002"],
    "stamp": ["k_impactWood_heavy_001", "k_impactWood_heavy_003", "k_impactPlank_medium_000"],
    "sub": ["es_sub"],
    "punch": ["es_punch"],
    "pin": ["k_drop_002", "k_tick_002"],
    "draw": ["k_scratch_002"],
    "type": ["es_type_run"],
    "riser": ["es_riser"],
}
_CACHE = {}


def _load(name):
    if name not in _CACHE:
        p = _os.path.join(SOUNDS, name + ".wav")
        if not _os.path.exists(p):
            _CACHE[name] = None
        else:
            x, sr = sf.read(p, dtype="float32")
            if x.ndim > 1:
                x = x.mean(1)
            if sr != SR:
                from scipy.signal import resample_poly
                x = resample_poly(x, SR, sr).astype(np.float32)
            pk = np.max(np.abs(x)) or 1.0
            _CACHE[name] = x / pk * 0.9
    return _CACHE[name]


def _take(kind, rng, ev):
    names = [n for n in BANK.get(kind, []) if _load(n) is not None]
    if not names:
        return None
    x = _load(names[int(rng.integers(0, len(names)))]).copy()
    if kind == "type":  # trim a typing run to the length of the line being typed
        n = int(min(len(x), max(0.25, ev.get("n", 12) / 15.0) * SR))
        x = x[:n] * np.minimum(1, (n - np.arange(n)) / (0.04 * SR))
    # a hand never does the same thing twice: +/- 4% speed (pitch) and +/- 2 dB
    sp = 1 + rng.uniform(-0.04, 0.04)
    idx = np.arange(0, len(x) - 1, sp)
    x = np.interp(idx, np.arange(len(x)), x).astype(np.float32)
    return x * 10 ** (rng.uniform(-2, 2) / 20)


# how loud each kind sits in the mix (before the story's sfx_gain)
LEVEL = {"slide": 0.55, "drop": 0.6, "heavy": 0.7, "whoosh": 0.45, "whip": 0.55, "flip": 0.4, "pop": 0.35,
         "stamp": 0.9, "sub": 0.9, "punch": 0.6, "pin": 0.4, "draw": 0.3, "type": 0.35, "riser": 0.45, "tape": 0.5}


def make_events_v2(events, total, seed=7):
    """Recorded foley. Falls back to the synthesised v1 sound for any kind the bank does not hold (tape)."""
    rng = np.random.default_rng(seed)
    mix = np.zeros(int((total + 2) * SR))
    v1 = {"tape": lambda: tape_rip(rng)}
    last = {}
    for ev in sorted(events, key=lambda e: e["t"]):
        k = ev["k"]
        k = {"wipe": "whip"}.get(k, k)
        # never stack the same sound twice inside 60 ms: it reads as a flam, not two hits
        if ev["t"] - last.get(k, -9) < 0.06:
            continue
        last[k] = ev["t"]
        x = _take(k, rng, ev)
        if x is None:
            x = v1.get(k, lambda: tap(rng))() if k in v1 or k not in BANK else None
            if x is None:
                continue
        lead = 0.0
        if k in ("whoosh", "whip"):
            lead = 0.12  # a whoosh peaks as the piece arrives, so it starts a little early
        x = x * LEVEL.get(k, 0.5) * ev.get("g", 1.0)
        s = int(max(0, ev["t"] - lead) * SR)
        e = min(len(mix), s + len(x))
        mix[s:e] += x[: e - s]
    return mix


def music_track(path, total, cuts=(), start=0.0):
    """A real music track under the film: loops if short, fades out at the end, drops out briefly at each cut."""
    from scipy.signal import resample_poly
    x, sr = sf.read(path, dtype="float32")
    if x.ndim > 1:
        x = x.mean(1)
    if sr != SR:
        x = resample_poly(x, SR, sr).astype(np.float32)
    x = x[int(start * SR):]
    n = int((total + 2) * SR)
    while len(x) < n:
        x = np.concatenate([x, x])
    x = x[:n].copy()
    t = np.arange(n) / SR
    env = np.ones(n, np.float32)
    env *= np.minimum(1, t / 0.4)                                  # soft start
    env *= np.clip((total + 0.4 - t) / 1.2, 0, 1)                  # fade out under the last line
    for c in cuts:                                                  # a stop-down: out 0.35 s before, back on the hit
        a, b = c - 0.38, c
        env *= np.where((t > a) & (t < b), np.clip(1 - (t - a) / 0.06, 0.04, 1), 1)
        env *= np.where((t >= b) & (t < b + 0.25), np.clip((t - b) / 0.25, 0.04, 1), 1)
    x *= env
    pk = np.max(np.abs(x)) or 1
    return x / pk * 0.8


def duck(music, voice, depth_db=-9.0, att=0.03, rel=0.35):
    """Pull the music down while the voice speaks (a simple sidechain)."""
    n = min(len(music), len(voice))
    v = np.abs(voice[:n])
    w = int(0.02 * SR)
    env = np.convolve(v, np.ones(w) / w, mode="same")
    on = (env > 0.02).astype(np.float32)
    g = np.empty(n, np.float32)
    lo = 10 ** (depth_db / 20)
    cur = 1.0
    a, r = np.exp(-1 / (att * SR)), np.exp(-1 / (rel * SR))
    for i in range(0, n, 64):  # control rate is plenty for a duck
        tgt = lo if on[i] else 1.0
        k = a if tgt < cur else r
        cur = tgt + (cur - tgt) * (k ** 64)
        g[i:i + 64] = cur
    out = music.copy()
    out[:n] *= g
    return out


def make_events(events, total, seed=7):
    rng = np.random.default_rng(seed)
    mix = np.zeros(int((total + 1) * SR))
    for ev in events:
        k = ev["k"]
        x = {"slide": lambda: paper_slide(rng), "drop": lambda: tap(rng), "pin": lambda: tap(rng, 0.08, 1200),
             "stamp": lambda: stamp(rng), "tape": lambda: tape_rip(rng), "wipe": lambda: wipe(rng),
             "type": lambda: typewriter(rng, ev.get("n", 12)), "draw": lambda: marker(rng)}.get(k, lambda: tap(rng))()
        x = x * ev.get("g", 1.0)
        s = int(max(0, ev["t"]) * SR)
        e = min(len(mix), s + len(x))
        mix[s:e] += x[: e - s]
    return mix


def bed(total, seed=3, bpm=72):
    """Low documentary tension: a slow minor pad, a soft heartbeat pulse and a clock tick."""
    rng = np.random.default_rng(seed)
    n = int((total + 1) * SR)
    t = np.arange(n) / SR
    # chord roots (A minor -> F -> C -> E), one chord per 4 beats
    roots = [110.0, 87.31, 130.81, 82.41]
    bar = 4 * 60 / bpm
    out = np.zeros(n)
    for i, r in enumerate(roots * int(total / (bar * 4) + 2)):
        a = int(i * bar * SR)
        if a >= n:
            break
        z = min(n, a + int(bar * SR * 1.15))
        tt = t[a:z] - t[a]
        env = np.minimum(1, tt / 0.8) * np.minimum(1, (tt[-1] - tt) / 0.6 + 0.0)
        tones = sum(np.sin(2 * np.pi * f * tt + p) for f, p in
                    [(r, 0), (r * 1.003, 1), (r * 1.5, 2), (r * 2.38, 0.5), (r * 0.5, 0.2)])
        out[a:z] += tones * env * 0.08
    out = _lp(out, 1400)
    beat = 60 / bpm
    for k in range(int(total / beat) + 1):
        s = int(k * beat * SR)
        hb = tap(rng, 0.25, body=55) * 0.5
        e = min(n, s + len(hb))
        out[s:e] += hb[: e - s] * 0.6
        tk = _bp(rng.standard_normal(int(0.02 * SR)), 3000, 8000) * _env(int(0.02 * SR), 0.0005, 0.004)
        s2 = int((k * beat + beat / 2) * SR)
        e2 = min(n, s2 + len(tk))
        out[s2:e2] += tk[: e2 - s2] * 0.12
    fade = np.minimum(1, t / 1.5) * np.minimum(1, (t[-1] - t) / 1.5)
    return out * fade


def write(path, x):
    peak = np.max(np.abs(x)) or 1
    sf.write(path, (x / peak * 0.8).astype(np.float32), SR)

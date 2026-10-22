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

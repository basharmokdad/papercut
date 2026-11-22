"""Narration with Kokoro (Apache-2.0, runs on the CPU, free for commercial use) + word timings for captions.

One wav per beat, so every beat's length is exact. Captions use the script's own words, timed by faster-whisper
(MIT): the script text is mapped onto whisper's word clock by character position, so spelling always matches.
"""
import json
import os
import re

import numpy as np
import soundfile as sf


def _models():
    for d in (os.environ.get("PAPERCUT_KOKORO"), os.path.join(os.path.expanduser("~"), ".papercut", "kokoro"), r"C:\kokoro\models"):
        if d and os.path.exists(os.path.join(d, "kokoro-v1.0.onnx")):
            return d
    raise SystemExit("Kokoro models not found: run setup (it downloads them to ~/.papercut/kokoro)")


GAP = 0.18  # silence between beats (s)


def synth(beats, out_dir, voice="af_heart", speed=1.0, lang="en-us"):
    from kokoro_onnx import Kokoro
    km = _models()
    k = Kokoro(os.path.join(km, "kokoro-v1.0.onnx"), os.path.join(km, "voices-v1.0.bin"))
    os.makedirs(out_dir, exist_ok=True)
    clips, sr = [], 24000
    for i, b in enumerate(beats):
        x, sr = k.create(b["say"], voice=voice, speed=speed, lang=lang)
        x = np.asarray(x, np.float32)
        # trim Kokoro's own leading/trailing silence so beats sit tight, then add a fixed gap
        nz = np.where(np.abs(x) > 0.004)[0]
        if len(nz):
            x = x[max(0, nz[0] - int(0.02 * sr)): nz[-1] + int(0.06 * sr)]
        clips.append(x)
    t, timing, parts = 0.25, [], [np.zeros(int(0.25 * sr), np.float32)]
    for x in clips:
        d = len(x) / sr
        timing.append({"start": round(t, 3), "dur": round(d, 3)})
        parts += [x, np.zeros(int(GAP * sr), np.float32)]
        t += d + GAP
    parts.append(np.zeros(int(0.6 * sr), np.float32))
    full = np.concatenate(parts)
    path = os.path.join(out_dir, "vo.wav")
    sf.write(path, full, sr, subtype="PCM_16")
    return path, timing, len(full) / sr


def from_take(take, beats, out_dir, model="small", lang="en"):
    """Use any narration recording instead of Kokoro: your own voice, ElevenLabs, VoxCPM, anything.

    One take of the whole script, read in order. Whisper finds every word; the script is laid onto its clock by
    character position, so each beat starts on its own first word. Returns the same (path, timing, total) as synth."""
    from faster_whisper import WhisperModel
    from scipy.signal import resample_poly
    x, sr = sf.read(take, dtype="float32")
    if x.ndim > 1:
        x = x.mean(1)
    lead = 0.25
    full = np.concatenate([np.zeros(int(lead * sr), np.float32), x, np.zeros(int(0.6 * sr), np.float32)])
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, "vo.wav")
    sf.write(path, full, sr, subtype="PCM_16")
    ww = hear(path, lang=lang, model=model)
    if not ww:
        raise SystemExit("voice_file: whisper heard no words in " + take)
    toks = [t for b in beats for t in b["say"].split()]
    times = align(toks, ww)
    timing, cur = [], 0
    for b in beats:
        n = len(b["say"].split())
        s, e = times[cur][0], times[cur + n - 1][1]
        timing.append({"start": round(s, 3), "dur": round(max(0.3, e - s), 3)})
        cur += n
    return path, timing, len(full) / sr


_HEARD = {}


def _norm(s):
    return re.sub(r"[^a-z0-9]", "", s.lower())


def hear(path, lang="en", model="small"):
    """Whisper's words for a recording as [{"w", "s", "e"}], cached, with the first word pinned to the real first sound
    (whisper likes to start the first word at 0.0 even when the file opens with silence)."""
    key = (os.path.abspath(path), os.path.getmtime(path), lang, model)
    if key in _HEARD:
        return _HEARD[key]
    from faster_whisper import WhisperModel
    from scipy.signal import resample_poly
    x, sr = sf.read(path, dtype="float32")
    if x.ndim > 1:
        x = x.mean(1)
    m = WhisperModel(model, device="cpu", compute_type="int8")
    segs, _ = m.transcribe(resample_poly(x, 16000, sr).astype(np.float32), word_timestamps=True, language=lang)  # an array: avoids PyAV clashes
    ww = [{"w": w.word, "s": float(w.start), "e": float(w.end)} for s in segs for w in (s.words or [])]
    if ww:
        loud = np.where(np.abs(x) > 0.03 * (np.max(np.abs(x)) or 1))[0]
        onset = loud[0] / sr if len(loud) else 0.0
        if ww[0]["s"] < onset - 0.05:
            ww[0]["s"] = float(min(onset, ww[0]["e"] - 0.08))
    _HEARD[key] = ww
    return ww


def align(tokens, ww):
    """Lay the script's words onto whisper's clock: one (start, end) per script word.

    Words both sides agree on pin exact times. A stretch that differs (a number the script spells out and whisper
    writes as digits, a name it mishears) shares the time whisper gave that stretch, split by word length. So it does
    not matter how numbers are written in the script, and one misheard word never shifts the words after it."""
    import difflib
    a = [_norm(t) or "_" for t in tokens]
    b = [_norm(w["w"]) or "_" for w in ww]
    out = [None] * len(a)
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(a=a, b=b, autojunk=False).get_opcodes():
        if tag == "equal":
            for k in range(i2 - i1):
                out[i1 + k] = (ww[j1 + k]["s"], ww[j1 + k]["e"])
        elif i2 > i1:
            if j2 > j1:
                t0, t1 = ww[j1]["s"], ww[j2 - 1]["e"]
            else:  # whisper heard nothing for these words: they get the gap between its neighbours
                t0 = ww[j1 - 1]["e"] if j1 > 0 else (ww[0]["s"] if ww else 0.0)
                t1 = ww[j1]["s"] if j1 < len(ww) else t0 + 0.25 * (i2 - i1)
            wts = [max(1, len(a[i])) for i in range(i1, i2)]
            tot, c = float(sum(wts)), 0.0
            for n, i in enumerate(range(i1, i2)):
                s = t0 + (t1 - t0) * c / tot
                c += wts[n]
                out[i] = (s, t0 + (t1 - t0) * c / tot)
    last = 0.0
    for i, (s, e) in enumerate(out):  # never run backwards, never shorter than a blink
        s = max(s, last)
        e = max(e, s + 0.08)
        out[i] = (s, e)
        last = s
    return out


def words(vo_path, beats, timing, model="small", lang="en"):
    """Script tokens with start/end times, grouped per beat."""
    ww = hear(vo_path, lang=lang, model=model)
    toks = [t for b in beats for t in b["say"].split()]
    out, cur = [], 0
    if ww:
        times = align(toks, ww)
        for b in beats:
            n = len(b["say"].split())
            out.append([{"w": t, "s": round(times[cur + k][0], 3), "e": round(times[cur + k][1], 3)}
                        for k, t in enumerate(b["say"].split())])
            cur += n
        return out
    for b, tm in zip(beats, timing):  # whisper heard nothing at all: spread each beat's words evenly
        ws = b["say"].split()
        step = tm["dur"] / max(1, len(ws))
        out.append([{"w": t, "s": round(tm["start"] + k * step, 3), "e": round(tm["start"] + (k + 1) * step, 3)}
                    for k, t in enumerate(ws)])
    return out


if __name__ == "__main__":
    import sys
    story = json.load(open(sys.argv[1], encoding="utf-8"))
    p, tm, total = synth(story["beats"], "assets/audio", story.get("voice", "af_heart"))
    print(p, round(total, 2), tm)

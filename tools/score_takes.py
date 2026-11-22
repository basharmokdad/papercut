"""Pick a narration take without ears: score every take of a script, for people and agents that cannot listen.

  python score_takes.py story.json voice/take_03.wav voice/take_07.wav ...

Run it with papercut's own Python (it needs faster-whisper). For each take it prints:
  words    share of the script's words whisper heard, in order (numbers are compared as numbers, so "twelve" = "12")
  missing  the script words it did not hear (a real dropped or changed word shows up here)
  pauses   the shortest gap between two beats: a take that runs one sentence into the next reads rushed
  tail     how quiet the last 150 ms are: a take that is cut off mid-sound is not clean
Take the one with every word, the longest shortest-pause and a quiet tail.
"""
import json
import os
import re
import sys

import numpy as np
import soundfile as sf

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "engine"))
import voice  # noqa: E402

NUM = set("zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen "
          "seventeen eighteen nineteen twenty thirty forty fifty sixty seventy eighty ninety hundred thousand million "
          "billion first second third fourth fifth sixth seventh eighth ninth tenth eleventh twelfth thirteenth "
          "fourteenth fifteenth sixteenth seventeenth eighteenth nineteenth twentieth thirtieth and".split())


def is_num(tok):
    t = re.sub(r"[^a-z0-9]", "", tok.lower())
    return bool(re.search(r"\d", t)) or t in NUM or any(p in NUM for p in re.split(r"[-\s]", tok.lower()) if p)


story = json.load(open(sys.argv[1], encoding="utf-8"))
beats = story["beats"]
toks = [t for b in beats for t in b["say"].split()]
print(f"{'take':28} {'words':>6} {'pauses':>7} {'tail':>8}  missing")
for take in sys.argv[2:]:
    ww = voice.hear(take, lang=story.get("lang", "en-us")[:2])
    heard = {voice._norm(w["w"]) for w in ww}
    plain = [t for t in toks if not is_num(t)]
    miss = [t for t in plain if voice._norm(t) not in heard]
    times = voice.align(toks, ww)
    gaps, cur = [], 0
    for b in beats[:-1]:
        cur += len(b["say"].split())
        gaps.append(times[cur][0] - times[cur - 1][1])
    x, sr = sf.read(take, dtype="float32")
    x = x.mean(1) if x.ndim > 1 else x
    tail = 20 * np.log10(max(1e-6, float(np.sqrt(np.mean(x[-int(0.15 * sr):] ** 2)))))
    share = 1 - len(miss) / max(1, len(plain))
    print(f"{os.path.basename(take):28} {share:6.1%} {min(gaps) if gaps else 0:6.2f}s {tail:6.1f}dB  {' '.join(miss[:8])}")

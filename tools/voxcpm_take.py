"""Make a natural narration take for a papercut film with VoxCPM2 (Apache-2.0, free, runs on your own GPU).

  python voxcpm_take.py story.json out_folder ["(voice description)"] [seeds...]

Install VoxCPM in its own environment first (pip install voxcpm; see github.com/OpenBMB/VoxCPM). It writes one take of
the whole script per seed. Listen, pick one, and set "voice_file": "<that take>" in story.json. papercut times every
beat and caption to the take with Whisper, so the take only has to read the script in order.
"""
import json
import os
import sys
import time

import soundfile as sf
import torch
from voxcpm import VoxCPM

story = json.load(open(sys.argv[1], encoding="utf-8"))
out = sys.argv[2]
voice = sys.argv[3] if len(sys.argv) > 3 else \
    "(A calm documentary narrator, a man in his forties with a warm, low, clear voice, measured unhurried pace)"
seeds = [int(s) for s in sys.argv[4:]] or [3, 7, 11]
os.makedirs(out, exist_ok=True)
text = " ".join(b["say"] for b in story["beats"])
model = VoxCPM.from_pretrained("openbmb/VoxCPM2", load_denoiser=False)
sr = model.tts_model.sample_rate
for seed in seeds:
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
    t1 = time.time()
    wav = model.generate(text=voice + text, cfg_value=2.0, inference_timesteps=10)
    p = os.path.join(out, f"take_{seed:02d}.wav")
    sf.write(p, wav, sr)
    print(p, f"{len(wav) / sr:.1f}s audio in {time.time() - t1:.0f}s")

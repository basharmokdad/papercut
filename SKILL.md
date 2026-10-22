---
name: papercut
description: Make a finished paper-collage documentary short (the Vox-style halftone cut-out look) from one topic, for free, on your own computer. Claude verifies the facts, writes the script, finds public-domain archive photos, and the engine cuts them out, voices the narration, animates every piece in stop-motion, adds paper sound effects and captions, and renders the MP4. Use for "make a collage video about X", "Vox-style explainer", "paper cut-out documentary", "halftone collage short", or any history, tech or true-story short where no footage exists.
---

# papercut

One topic in, one finished 30-60 s documentary out. No video model, no image model, no credits:

| Part | Tool | Licence |
|---|---|---|
| Script, facts, picture choices | Claude | your plan |
| Archive photos | Wikimedia Commons, public domain / CC0 only | free to use |
| Cut-outs | rembg (isnet) + our halftone + scissor edge | MIT / Apache-2.0 |
| Voice | Kokoro-82M, on the CPU | Apache-2.0 |
| Word timing for captions | faster-whisper | MIT |
| Paper, foley, music bed | generated in code from a seed | ours, MIT |
| Animation + render | HyperFrames (HTML to video) | Apache-2.0 |
| Maps | Natural Earth via world-atlas + d3-geo | public domain / ISC |
| Fonts | Anton, Archivo Black, Special Elite, Permanent Marker | OFL / Apache-2.0 |

Paths (relative to this skill's own folder, the one this SKILL.md is in):
- engine: `<skill>/engine/papercut.py`
- python: `<skill>/.venv/Scripts/python.exe` on Windows, `<skill>/.venv/bin/python` on macOS / Linux (made by setup)

Make one folder per film and run every command from inside it, e.g. `"<python>" "<skill>/engine/papercut.py" make story.json`.

## The workflow (run it in this order, stop where it says)

### 1. Facts first

Search the topic. Every date, name and number in the script needs two independent sources. If sources disagree, write around it ("August 1911", not "August 21"). Never invent a quote: use the documented wording, or none.

### 2. Script (beats)

- 10-14 beats, 30-45 s. One sentence (or half of one) per beat, one visual idea per beat.
- Cold open on a date and a place: "September ninth, 1947. Harvard University."
- Calm documentary voice, short declaratives. Spell numbers the way they should be spoken ("Seventy-nine years later").
- End on a short line that lands: "After it, it was." / "We are still debugging."

### 3. Pictures

```
<python> <skill>/engine/papercut.py search "Grace Hopper" sheet.png
```

Open `sheet.png` and pick by looking, not by title. Rules learned the hard way:

- People: `"cut": true` (background removed). The face must be well lit and at least ~400 px tall in the source. Dark or busy photos cut badly: crop tight around the person (`"crop": [l, t, r, b]` as fractions) or use `"cut": false`.
- Machines, rooms, scenes, space photos: `"cut": false` (a printed photo with tape).
- Documents and handwriting: `"cut": false, "dots": false` (clean print, halftone would destroy the writing).
- Never show a photo of the wrong object with the right caption (a Mark I is not a Mark II). If no true photo exists, use a `document`, `number` or `timeline` beat instead.

### 4. story.json

```json
{
  "title": "The First Computer Bug", "slug": "first-computer-bug",
  "format": "9:16", "voice": "af_heart", "music": "bed", "seed": 11,
  "images": {
    "hopper": {"commons": "File:Commodore Grace M. Hopper, USN (covered) head and shoulders crop.jpg", "cut": true, "accent": "red"},
    "page":   {"file": "sources/log.jpg", "cut": false, "dots": false, "accent": "red", "size": 1200}
  },
  "beats": [
    {"say": "September ninth, 1947. Harvard University.", "kind": "document", "bg": "mustard",
     "head": "OPERATIONS LOG", "lines": ["DATE: 9 SEPT 1947", "MACHINE: MARK II"], "label": "09.09.1947"}
  ]
}
```

Image keys: `commons` (exact `File:` title) or `file` (local path), `cut`, `dots`, `crop`, `accent` (red, mustard, teal, null), `size`, `contrast`.

Beat kinds (every beat also takes `bg`, `scraps`, `burst`, `transition`):

| kind | fields | use for |
|---|---|---|
| `hero` | `hero`, `label`, `tag`, `stamp`, `stamp_on`, `circle` | a person or object, big |
| `photo` | `photo`, `label`, `tag`, `stamp`, `stamp_on` | a scene, a document photo |
| `duo` | `left`, `right`, `string`, `label` | two people, a connection |
| `number` | `number`, `sub`, `stamp`, `hero` | a date, an amount, a count (ransom letters) |
| `document` | `head`, `lines`, `redact`, `mark`, `stamp`, `hero`, `label` | typed text, lists, names |
| `timeline` | `dates`, `active`, `hero`, `label` | before / after, a span of years |
| `quote` | `quote`, `by`, `hero` | a real, sourced quote |
| `map` | `map: {country | highlight[], pin: [lon, lat], place, sea}`, `label`, `stamp` | where it happened |

`bg`: mustard, red, teal, navy, newsprint, kraft, cream, pink, olive, ink. Alternate warm and cool; never the same twice in a row.
`stamp_on`: a word from `say`; the stamp lands when that word is spoken.
Labels: 1-3 words, uppercase. `label_size` shrinks long ones; `|` breaks a line.

### 5. Build, look, fix, render

```
<python> <skill>/engine/papercut.py make story.json            # images, voice, animation, sound
```

1. Open `pieces.jpg`: every cut-out on one sheet. A blob or a missing face means re-crop, raise `contrast`, or switch to `cut: false`.
2. `<python> <skill>/engine/papercut.py snap story.json 2.1,5.4,...` with a time near the end of each beat (beat times are in `project/assets/audio/timing.json`). Check every frame: nothing off the edge, nothing important under the captions, every stamp readable.
3. Fix story.json and run `make` again (cut-outs and voice are cached, only what changed is rebuilt).
4. `<python> <skill>/engine/papercut.py make story.json --render` writes `<slug>.mp4` (1080x1920, 30 fps, -14 LUFS).

Credits for every photo are written to `CREDITS.txt`. Put them in the video description.

## What the engine does for you

- Halftone cut-outs with a scissor-cut paper border, a misregistered colour offset and a real cast shadow.
- Stop-motion on twos: every move is quantised to 12 poses a second, every piece "boils" a pixel or two, the camera pushes in slowly in steps.
- Paper wipes between scenes (slide, drop, cut), torn label strips, rubber stamps, marker circles, red string, typewriter documents with redaction bars.
- Foley for every entrance (paper slide, tap, stamp thud, tape, typewriter) and a quiet tension bed, mixed under the voice to -14 LUFS.
- Captions from the script's own words, timed by whisper, current word highlighted.

## Voices

Kokoro voices that work for documentary: `af_heart` (default, best quality), `af_bella`, `bf_emma`, `am_michael`, `bm_george`. English only. For another language, record your own voice as `vo.wav` per beat or swap in a TTS that speaks it.

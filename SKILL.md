---
name: papercut
description: Make a finished paper-collage documentary short (the Vox-style halftone cut-out look) from one topic, for free, on your own computer. Claude verifies the facts, writes the script, finds public-domain archive photos, and the engine cuts them out, builds a layered paper world, voices the narration, animates every piece in stop-motion, builds the headlines and captions word by word, adds paper sound effects and renders the MP4. Use for "make a collage video about X", "Vox-style explainer", "paper cut-out documentary", "halftone collage short", or any history, tech or true-story short where no footage exists.
---

# papercut

One topic in, one finished 30-60 s documentary out. No video model, no image model, no credits:

| Part | Tool | Licence |
|---|---|---|
| Script, facts, picture choices | Claude | your plan |
| Archive photos | Wikimedia Commons, public domain / CC0 only | free to use |
| Cut-outs | rembg (isnet) + our halftone + scissor edge | MIT / Apache-2.0 |
| Paper worlds (newspaper, sky, night, rings, graph paper) | generated in code from a seed | ours, MIT |
| Voice | Kokoro-82M on the CPU, or any recording you bring (`voice_file`) | Apache-2.0 / yours |
| Word timing for captions | faster-whisper | MIT |
| Paper, card, book and impact foley | real recordings, Kenney's sound packs | CC0 (public domain) |
| Whooshes, low hits, typing | rendered with Earshot | MIT |
| Music | three Kevin MacLeod tracks ship with the engine, or your own file | CC BY 4.0 (credit written to CREDITS.txt) |
| Animation + render | HyperFrames (HTML to video) | Apache-2.0 |
| Maps | Natural Earth via world-atlas + d3-geo | public domain / ISC |
| Fonts | Abril Fatface, DM Serif Display Italic, Anton, Archivo Black, Special Elite, Permanent Marker | OFL / Apache-2.0 |

Paths (relative to this skill's own folder, the one this SKILL.md is in):
- engine: `<skill>/engine/papercut.py`
- python: `<skill>/.venv/Scripts/python.exe` on Windows, `<skill>/.venv/bin/python` on macOS / Linux (made by setup)

Make one folder per film and run every command from inside it, e.g. `"<python>" "<skill>/engine/papercut.py" make story.json`.

## What makes it look like the real thing

Hold every scene to these five rules. They are the difference between a slideshow and a collage film.

1. **Fill the frame.** The subject is huge and runs off the bottom edge (`"size": "full"`). A small picture in the middle of a flat colour is a slideshow.
2. **Three layers, always.** A printed world at the back (`bg`), a torn strip or loose pieces in the middle (`band`, clouds, moon), the subject on top. Never one photo on one flat card when a layered world fits.
3. **The words are part of the picture.** Every beat gets at least one piece of text that builds while the voice speaks: a `headline` that stacks one strip per phrase, a `kinetic` sentence that lands word by word, giant `letters`, a hand-written `notes` arrow, a small paper `tags` label. Use the speaker's own words, shortened.
4. **One new thing every half second.** Strip, subject, headline line one, line two, note. Nothing arrives together and nothing sits still (the engine pushes in and drifts every piece after it lands).
5. **Change the world every beat.** Dark newspaper, then red rings, then sky. Never the same `bg` twice in a row, never the same scene kind three times in a row.

### Motion and light rules (the engine applies these for you)

- **Photos are clean prints.** Fine grain, soft contrast, ink that is never pure black. Coarse halftone dots turn busy or dark photos into mush, so dots are opt-in (`"dots": true`) and fine by default.
- **Fast things blur.** Every piece that flies in is smeared along its path while it moves and is sharp the frame it lands. Scene changes are camera whip-pans: the old scene is flung out and the new one flies in, both blurred.
- **Light falls through a window.** Soft diagonal shafts of light cross every scene and drift slowly, and the sheet carries faint fold lines. `"light": "blinds"` for slats, `"none"` to turn it off; `"folds": false`.
- **Sound follows the picture.** A whoosh as anything flies, a real paper slide and landing under it, a click on every word that pops on, a marker squeak on highlights and string, a thud on stamps. The music ducks under the voice.
- **Drops.** Put `"drop": true` on the one or two beats that turn the story. The music cuts out for a breath before the line and comes back on a low hit.

### Type rules (the engine applies the first two for you)

- **Type is printed, not rendered.** Every letter gets rough ink edges and a few missed specks, and is re-inked six times a second, so no text ever looks like a clean screen font. `"ink": 0` in the story turns it off, `2` makes it rougher.
- **Type is never flown in.** A word is simply there on the syllable, a hair off register, and is knocked into place over the next two poses. Strips are slapped down the same way. Only pictures slide and rise.
- **Two voices in one sentence.** Plain words are set in a heavy condensed sans, capitals. The one or two words that carry the meaning go in `em` and are set in an italic serif, lower case, in the accent colour ("MOON LANDING IS *off.*"). Never emphasise more than two words in a beat.
- **Size contrast is the design.** A small line riding on a giant word (`letters_kicker` on `letters`: "APRIL THIRTEENTH" over "1970") beats two lines of the same size.
- **One phrase at a time for the big moments.** `"swap": true` on a `kinetic` beat shows one line, then replaces it with the next in the same spot ("APOLLO THIRTEEN" / "NEVER TOUCHED" / "*the moon*"). Use it for the turn of the story and the last line.
- **Notes are written, strips are slapped.** A `notes` line writes on letter by letter, then its arrow is drawn.

## The workflow (run it in this order, stop where it says)

### 1. Facts first

Search the topic. Every date, name and number in the script needs two independent sources. If sources disagree, write around it ("August 1911", not "August 21"). Never invent a quote: use the documented wording, or none.

### 2. Script (beats)

- 10-14 beats, 30-45 s. One sentence (or half of one) per beat, one visual idea per beat.
- Word budget: about 105-115 words lands at 40-44 s with a natural take (VoxCPM or a person). The built-in Kokoro voice reads the same script about 15% slower, so do not judge the length on a Kokoro draft.
- Cold open on a date and a place: "September ninth, 1947. Harvard University."
- Calm documentary voice, short declaratives. Spell numbers the way they should be spoken ("Seventy-nine years later"); the timing copes with either spelling.
- End on a short line that lands: "After it, it was." / "We are still debugging."
- While writing each line, decide which 2-4 words of it go on screen. That is the beat's `headline`, `lines` or `letters`.

### 3. Pictures

```
<python> <skill>/engine/papercut.py search "Grace Hopper" sheet.png
```

Open `sheet.png` and pick by looking, not by title. Rules learned the hard way:

- People: `"cut": true` (background removed). The face must be well lit and at least ~400 px tall in the source. Dark or busy photos cut badly: crop tight around the person (`"crop": [l, t, r, b]` as fractions) or use `"cut": false`.
- A person used full frame needs `"size": 1400` so the face keeps its detail when it is big.
- Machines, rooms, scenes, space photos: `"cut": false` (a printed photo with tape).
- Every photo prints clean by default. `"color": true` keeps a colour photo's own colours (slightly faded, like an old print); `"dots": true` turns it into a halftone print (use it on a clear, well-lit face, never on a crowd or a dark room).
- Never show a photo of the wrong object with the right caption (a Mark I is not a Mark II). If no true photo exists, use a `scene`, `kinetic`, `document`, `number` or `timeline` beat instead.

### 4. story.json

```json
{
  "title": "Apollo 13", "slug": "apollo-13", "format": "9:16", "voice": "af_heart", "music": "investigations", "seed": 21,
  "images": {
    "swigert": {"commons": "File:Jack Swigert.jpg", "cut": true, "accent": "red", "size": 1400},
    "sm":      {"commons": "File:Apollo 13 SM.jpg", "cut": false, "accent": "red", "size": 1100}
  },
  "beats": [
    {"say": "April thirteenth, 1970. Two hundred thousand miles from Earth.", "kind": "scene", "bg": "night",
     "moon": [0.5, 0.47, 560], "letters": "1970", "letters_on": "1970",
     "tags": [{"text": "13 APRIL", "at": [0.3, 0.335], "color": "red", "on": "April"}],
     "headline": ["200,000 MILES", "FROM EARTH"], "headline_on": ["Two", "from"]},
    {"say": "Jack Swigert radios: Okay, Houston, we've had a problem here.", "kind": "hero", "size": "full",
     "bg": "press-dark", "band": "night", "hero": "swigert", "label": "JACK SWIGERT",
     "headline": ["HOUSTON,", "WE'VE HAD", "A PROBLEM"], "cap": false}
  ]
}
```

Image keys: `commons` (exact `File:` title) or `file` (local path), `px` (download width: 1920 default, 2560 or 3840 for a photo you crop hard or print full frame), `cut`, `color`, `dots`, `crop`, `accent` (red, mustard, teal, null), `size`, `cell` (dot size when `dots` is on), `contrast`.

Story keys for sound and look: `voice` (a Kokoro voice) or `voice_file` (one recorded take of the whole script, read in order; any voice works, and it is timed by Whisper), `music` (`investigations` default, `sneaky-snitch`, `dark-fog`, `none`, `bed` for the old synthesised pad, or a path to your own track), `music_gain`, `duck_db`, `sfx_gain`, `foley` (`v1` for the old synthesised set), `light`, `light_strength`, `folds`, `motion_blur`, `ink`.

**Scene kinds** (the middle of the frame):

| kind | fields | use for |
|---|---|---|
| `hero` | `hero`, `size: "full"`, `label`, `tag`, `stamp`, `stamp_on`, `circle` | a person or object. `full` = fills the frame, rises from the bottom |
| `kinetic` | `lines`, `em`, `swap`, `hero`, `size` | the sentence is the picture: each word is printed as it is spoken, last line biggest. `swap: true` = one line at a time in the same spot |
| `scene` | none of its own | an empty stage for `letters`, `headline`, `band`, `moon`, `tags`, `notes` |
| `photo` | `photo`, `label`, `tag`, `stamp`, `stamp_on` | a scene, a document photo |
| `board` | `center`, `around` (up to 4 image keys, or `{"img", "tag"}`), `circle`, `circle_on`, `label` | an evidence board: photos fly in, get pinned, red string is drawn from each to the middle |
| `duo` | `left`, `right`, `string`, `label` | two people, a connection |
| `number` | `number`, `sub`, `stamp`, `hero` | a date, an amount, a count (ransom letters) |
| `document` | `head`, `lines`, `redact`, `mark`, `stamp`, `hero`, `label` | typed text, lists, names |
| `timeline` | `dates`, `active`, `hero`, `label` | before / after, a span of years |
| `quote` | `quote`, `by`, `hero` | a real, sourced quote |
| `map` | `map: {country | highlight[], pin: [lon, lat], place, sea}`, `label`, `stamp` | where it happened |

**Layers every kind can take** (this is where the look comes from):

| field | what it adds |
|---|---|
| `bg` | the world at the back. Printed: `press` (newspaper set from your own title and script), `press-dark`, `sky` (with drifting paper clouds), `night` (stars and a cut-out moon), `rings-red`, `rings-teal`, `rings-mustard`, `rings-navy` (rings of torn card), `grid` (graph paper). Flat card: mustard, red, teal, navy, newsprint, kraft, cream, pink, olive, ink |
| `band` | a torn strip across the frame behind the subject: `sky`, `night`, any `bg` name, or an image key (the photo fills the strip). `band_y`, `band_h` as fractions (default 0.29, 0.31) |
| `headline` | list of lines. Each line is its own torn strip and lands on the word it starts with. If a line starts with a number or a word that is not spoken, name the spoken word per line in `headline_on` (`"200,000 MILES"` lands on `"Two"`). `headline_at`: low (default), top, mid. `headline_colors`: e.g. `["mustard", "", "ink", "red"]` ("" is cream). `headline_font`: fat (default) or anton. Behind a full-frame subject the strips are sized to sit across the chest, never over the face (`face`: where the face ends, default 0.48 of the cut-out) |
| `letters` | one giant word or year, printed letter by letter with a second ink a few pixels off register. `letters_on` (spoken word that starts it), `letters_at` top / mid / low, `letters_color`, `letters_offset` (the second ink), `letters_kicker` (a small condensed line riding on top of it) |
| `tags` | small paper labels: `[{"text", "at": [x, y], "color", "on": spoken word}]` |
| `notes` | marker handwriting with a drawn arrow: `[{"text", "at": [x, y], "to": [x, y], "on", "color", "size"}]` |
| `moon` | `true` or `[x, y, size]`. `clouds`: a number |
| `cap` | `false` hides the bottom captions for this beat. Do it when the headline already shows the spoken words |
| `hl` | on a `kinetic` beat: words that get a highlighter swipe just after they are printed (yellow; a cream strip on yellow or brown card) |
| `drop` | `true`: the music stops for a breath before this beat and comes back on a low hit. One or two per film |
| `transition` | how this scene arrives: `whip-left`, `whip-right`, `whip-up`, `whip-down` (default cycle), `cut`, or the old paper slide-ins `right`, `left`, `up`, `down`, `drop` |

`at` and `to` are fractions of the frame: `[0.5, 0.5]` is the centre; a note's `at` is the centre of its text. On a `photo` beat keep notes between y 0.66 and 0.74 (below the photo, above the captions); on other kinds put them wherever there is clear paper, and check the still.

**Placement keys** (use them when a still shows a clash; every one is optional):

| key | on | what it does |
|---|---|---|
| `hero_y`, `hero_x` | hero, kinetic, board | centre of the subject in pixels / a sideways nudge |
| `hero_h`, `hero_top` | hero | height of the box in pixels / where a full-frame subject's top sits (fraction of the frame, default 0.33) |
| `headline_at`, `letters_at` | any | `low`, `top`, `mid`, or a number: the y in pixels of the first strip / the word |
| `headline_size`, `letters_size`, `label_size`, `stamp_size`, `kicker_size` | any | type size in pixels (they are shrunk to fit the width anyway) |
| `text_y`, `size` | kinetic | top of the text block / base type size |
| `band_y`, `band_h`, `band_rot` | band | position, height (fractions) and tilt of the strip |
| `clouds`, `moon` | any | number of clouds (0 to remove them) / `true` or `[x, y, size]` |
| `doc_y`, `number_y`, `line_y`, `map_y` | document, number, timeline, map | where that piece sits |
| `bend`, `rot`, `size`, `color` | each note | curve of the arrow, tilt, type size, ink |

**Traps other people hit:**

- **A wide photo as a full-frame hero.** `"size": "full"` is for a tall subject (a person, a rocket). A landscape photo gets its sides cropped and sits low; use `photo`, or a `band` with the image key, or set `hero_y` / `hero_x` and a numeric `headline_at`.
- **Headline on a tight portrait.** If the face fills the cut-out, the default strips have no chest to sit on and shrink. Use `"headline_at": "top"`, or raise `face` (0.48 = the face ends just under halfway down).
- **Short strips.** Keep each headline line to about 14 characters; long lines become small type.
- **Boards.** Pins go in at the top of each photo and the string runs from there to the middle. Use uncut prints (`cut: false`) with some headroom, not cut-out heads: a pin in a forehead looks wrong.
- **Machines on a plain background.** Still `cut: false`. The cut-out keeps slabs of the backdrop.
- **Kinetic beats show no bottom captions** (the words are already the picture). Add `"cap": true` if the lines are a shortened version of the sentence and the full words matter.
- **A `document` with a `hero`** drops a small photo over the top-right of the sheet: keep the typed lines short there.
- **The `press` worlds print your title and script** as a newspaper behind the scene, so they change when the script changes. That is real text on screen: check it reads as texture, not as a spoiler.
- **Kickers and giant letters over `sky`.** Clouds are cream; cream type on them is weak. Use `"clouds": 0` on that beat or a `letters_color`.
`stamp_on`, `letters_on` and `on` take a word from `say`; the piece lands when that word is spoken.
Labels: 1-3 words, uppercase. `label_size` shrinks long ones; `|` breaks a line.
A `kinetic` beat's `lines` may be a shorter version of the sentence ("MOON LANDING / IS OFF. / GET THREE / MEN HOME"); words that are in `say` land on time. `em` lists the words (exactly as written in `lines`, any case) that are set in the italic serif.

Captions: `"captions": "build"` (default: every word is its own paper chip and lands as it is spoken), `"strip"` (one strip per phrase, the current word lit) or `"none"`.

### 5. Build, look, fix, render

```
<python> <skill>/engine/papercut.py make story.json            # images, voice, animation, sound
<python> <skill>/engine/papercut.py sheet story.json           # one still at the end of every beat, in snaps/
```

1. Open `pieces.jpg`: every cut-out on one sheet. A blob or a missing face means re-crop, raise `contrast`, or switch to `cut: false`.
2. Open every `snaps/frame-*.png` (or `snaps/contact-sheet-*.jpg`). Check each beat against the five rules, and: no face under a strip, no note under the captions or across a label, every stamp readable, nothing important in the bottom 300 px of a 9:16 frame.
3. For one moment in a beat: `<python> <skill>/engine/papercut.py snap story.json 2.1,5.4` (stills go to `snaps-at/`; beat times are in `project/assets/audio/timing.json`).
4. Fix story.json and run `make` again (cut-outs and voice are cached, only what changed is rebuilt).
5. `<python> <skill>/engine/papercut.py make story.json --render` writes `<slug>.mp4` (1080x1920, 30 fps, -14 LUFS) and prints the loudness it measured. It also runs HyperFrames' lint and prints only real errors.
6. Pull a dozen frames out of the finished MP4 and look once more; check the frame at 0.3 s already shows a picture.

Credits for every photo are written to `CREDITS.txt`. Put them in the video description.

## What the engine does for you

- Halftone cut-outs with a scissor-cut paper border, a misregistered colour offset and a real cast shadow.
- Paper worlds printed from a seed: a newspaper page that carries your own title and script, sky, night, rings of torn card, graph paper. No stock textures, no invented headlines.
- Torn strips with a white fibre edge, paper clouds that drift, a cut-out moon.
- Text that builds with the voice: stacked headline strips, word-by-word sentences, giant cut-out letters, marker notes with drawn arrows, captions as paper chips.
- Stop-motion on twos: every move is quantised to 12 poses a second, every piece "boils" a pixel or two, subjects rise from below and keep pushing in.
- Paper wipes between scenes, rubber stamps, marker circles, red string, typewriter documents with redaction bars.
- Foley for every entrance (paper slide, tap, stamp thud, tape, typewriter, marker) and a quiet tension bed, mixed under the voice to -14 LUFS.

## Voices

The built-in voice is Kokoro (`af_heart` default, also `af_bella`, `bf_emma`, `am_michael`, `bm_george`): fast, free, on the CPU, but it sounds synthetic. For a film people will watch, bring a real take:

- **Your own voice:** record the whole script once, in order, and set `"voice_file": "my-take.wav"`.
- **A free natural voice:** `tools/voxcpm_take.py story.json voice/` makes three takes with VoxCPM2 (Apache-2.0, runs on your own GPU, the voice is described in plain words). Pick one by ear, or if you cannot listen run `<python> <skill>/tools/score_takes.py story.json voice/take_*.wav`: take the one that has every word, the longest pause between beats and a quiet ending. Set it as `voice_file`.
- **Any voice tool you already pay for** works the same way: export one take, set `voice_file`.

papercut times every beat, caption and headline to the take with Whisper, so any language Whisper understands works.

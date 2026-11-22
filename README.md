# papercut

**Vox-style paper-collage documentaries, made by Claude, for free, on your own computer.**

One topic in, one finished vertical short out: halftone cut-outs that fill the frame, layered paper worlds, headlines and captions that build word by word with the voice, rubber stamps, maps, typewriter documents, stop-motion on twos and paper sound effects. No video model, no image model, no credits.

![Frames from the Apollo 13 example](docs/frames-v2.jpg)

<p>
<img src="docs/demo-headline.gif" width="240" alt="An astronaut cut-out rises into frame and headline strips land on each spoken phrase">
<img src="docs/demo-words.gif" width="240" alt="A sentence printed word by word in two typefaces, with a highlighter swipe">
<img src="docs/demo-board.gif" width="240" alt="Photos fly onto an evidence board, get pinned and joined with red string">
</p>

## How it works

AI video tools invent the picture, and every clip costs credits. papercut builds the picture instead, from real archive photos and code:

1. **Claude** checks the facts, writes a 10-14 beat script and picks the photos.
2. **Wikimedia Commons** supplies the photos. Only public domain and CC0 by default; every photo is credited automatically.
3. **rembg** removes the background, then the engine prints it as halftone dots on paper, cuts a scissor border, adds a misregistered colour offset and a real shadow.
4. The engine prints the **paper world** behind it from a seed: a newspaper page set from your own title and script, a sky with drifting paper clouds, a night sky with a cut-out moon, rings of torn card, graph paper. Torn strips cross the frame behind the subject.
5. **Kokoro** (an open voice model, runs on the CPU) reads the script. **faster-whisper** times every word, so headline strips, giant letters, hand-written notes and caption chips each land on the word being spoken.
6. **HyperFrames** animates it as HTML: subjects rise from the bottom of the frame, every piece slides, drops or stamps in at 12 poses a second, boils a pixel like a real animation table, and keeps pushing in after it lands.
7. **Real sound.** Paper slides, card landings, book thuds and clicks are real recordings (Kenney, CC0); whooshes and low hits come from Earshot (MIT). Every flying piece gets a whoosh, every word that pops on gets a click, and a music track by Kevin MacLeod (CC BY 4.0) ducks under the voice and drops out before the lines that turn the story. Mixed to -14 LUFS.
8. **Motion like a camera.** Pieces are motion-blurred while they fly, scenes change with blurred whip-pans, and soft window light drifts across the paper.

Everything that ships in the video is either generated from a seed or free to use. Nothing is rented.

## Install

You need Python 3.10+, Node 18+, FFmpeg and git.

```bash
git clone https://github.com/basharmokdad/papercut
cd papercut
./setup.sh          # macOS / Linux
# or on Windows:
powershell -ExecutionPolicy Bypass -File setup.ps1
```

Setup makes a Python venv in `.venv`, installs the libraries, downloads the Kokoro voice model (~330 MB) to `~/.papercut/kokoro`, and fetches the map data and animation library into `engine/data`.

To use it as a Claude Code skill, link or copy the folder into your skills folder:

```bash
ln -s "$(pwd)" ~/.claude/skills/papercut
```

Then ask Claude: *"Make a papercut video about the first computer bug."*

## Use it by hand

```bash
mkdir my-film && cd my-film
../.venv/bin/python ../engine/papercut.py search "Grace Hopper" sheet.png   # find photos, look at sheet.png
# write story.json (see examples/ and SKILL.md)
../.venv/bin/python ../engine/papercut.py make story.json                   # build
../.venv/bin/python ../engine/papercut.py sheet story.json                  # one still per beat, in snaps/
../.venv/bin/python ../engine/papercut.py snap story.json 3.2,7.5           # or stills at exact seconds
../.venv/bin/python ../engine/papercut.py make story.json --render          # render the MP4
```

Each film is one `story.json`: the images and a list of beats. A beat is one line of narration plus one scene: `hero`, `kinetic`, `scene`, `photo`, `duo`, `number`, `document`, `timeline`, `quote` or `map`. Any scene can add a world (`bg`), a torn strip (`band`), a `headline`, giant `letters`, `tags` and hand-written `notes`. The full reference and the five rules that make it look right are in [SKILL.md](SKILL.md).

## Examples

| Film | Scenes it shows off |
|---|---|
| [The first computer bug](examples/01-first-bug/story.json) | the real 1947 logbook, ransom-letter numbers, timeline |
| [Apollo 13](examples/02-apollo-13/story.json) | the full new look: full-frame cut-outs, newspaper and night-sky worlds, building headlines, word-by-word sentences, notes with arrows |
| [The Mona Lisa theft](examples/03-mona-lisa/story.json) | paper maps with pins, police report with a redaction bar |
| [ENIAC's six programmers](examples/04-eniac/story.json) | typed name list, stamps, hall-of-fame number |

A 40-second film renders in a few minutes on a normal PC.

## Limits

- The built-in voice (Kokoro) is quick but sounds synthetic. For a film people will watch, record the script once or make a free natural take with `tools/voxcpm_take.py` (VoxCPM2, needs a GPU) and set `"voice_file"`. Any language Whisper understands works that way.
- It is only as good as the photos: dark or busy photos cut badly. `pieces.jpg` shows every cut-out before you render.
- It makes 9:16 shorts first; 16:9 works but its layouts are less tuned.

## Credits

Built by [Web Lab](https://instagram.com/weblabai). Open-source parts and their licences are listed in [CREDITS.md](CREDITS.md). Code: MIT.

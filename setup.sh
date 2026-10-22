#!/usr/bin/env bash
# papercut setup for macOS / Linux: venv + libraries + Kokoro voice model + map data and animation library.
set -euo pipefail
root="$(cd "$(dirname "$0")" && pwd)"

for tool in python3 node npx ffmpeg curl; do
  command -v "$tool" >/dev/null || { echo "$tool is not installed"; exit 1; }
done

[ -d "$root/.venv" ] || python3 -m venv "$root/.venv"
"$root/.venv/bin/python" -m pip install -q -U pip
"$root/.venv/bin/python" -m pip install -q -r "$root/requirements.txt"

models="$HOME/.papercut/kokoro"
mkdir -p "$models"
rel="https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0"
for f in kokoro-v1.0.onnx voices-v1.0.bin; do
  [ -f "$models/$f" ] || { echo "downloading $f"; curl -sL -o "$models/$f" "$rel/$f"; }
done

data="$root/engine/data"
mkdir -p "$data"
get() { [ -f "$data/$1" ] || curl -sL -o "$data/$1" "$2"; }
get gsap.min.js https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js
get d3-array.min.js https://cdn.jsdelivr.net/npm/d3-array@3.2.4/dist/d3-array.min.js
get d3-geo.min.js https://cdn.jsdelivr.net/npm/d3-geo@3.1.1/dist/d3-geo.min.js
get topojson-client.min.js https://cdn.jsdelivr.net/npm/topojson-client@3.1.0/dist/topojson-client.min.js
get countries-110m.json https://cdn.jsdelivr.net/npm/world-atlas@2.0.2/countries-110m.json

npx --yes hyperframes --version >/dev/null
echo "papercut is ready. Try: .venv/bin/python engine/papercut.py make examples/01-first-bug/story.json --render"

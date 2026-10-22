# papercut setup for Windows: venv + libraries + Kokoro voice model + map data and animation library.
$ErrorActionPreference = "Stop"
$root = $PSScriptRoot

foreach ($tool in "python", "node", "npx", "ffmpeg") {
    if (-not (Get-Command $tool -ErrorAction SilentlyContinue)) { throw "$tool is not installed or not on PATH" }
}

if (-not (Test-Path "$root\.venv")) { python -m venv "$root\.venv" }
& "$root\.venv\Scripts\python.exe" -m pip install -q -U pip
& "$root\.venv\Scripts\python.exe" -m pip install -q -r "$root\requirements.txt"

$models = Join-Path $HOME ".papercut\kokoro"
New-Item -ItemType Directory -Force $models | Out-Null
$rel = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0"
foreach ($f in "kokoro-v1.0.onnx", "voices-v1.0.bin") {
    if (-not (Test-Path "$models\$f")) { Write-Host "downloading $f"; curl.exe -sL -o "$models\$f" "$rel/$f" }
}

$data = "$root\engine\data"
New-Item -ItemType Directory -Force $data | Out-Null
$libs = @{
    "gsap.min.js" = "https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"
    "d3-array.min.js" = "https://cdn.jsdelivr.net/npm/d3-array@3.2.4/dist/d3-array.min.js"
    "d3-geo.min.js" = "https://cdn.jsdelivr.net/npm/d3-geo@3.1.1/dist/d3-geo.min.js"
    "topojson-client.min.js" = "https://cdn.jsdelivr.net/npm/topojson-client@3.1.0/dist/topojson-client.min.js"
    "countries-110m.json" = "https://cdn.jsdelivr.net/npm/world-atlas@2.0.2/countries-110m.json"
}
foreach ($k in $libs.Keys) { if (-not (Test-Path "$data\$k")) { curl.exe -sL -o "$data\$k" $libs[$k] } }

npx --yes hyperframes --version | Out-Null
Write-Host "papercut is ready. Try: .venv\Scripts\python.exe engine\papercut.py make examples\01-first-bug\story.json --render"

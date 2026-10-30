#!/usr/bin/env bash
# Render slide HTML files to 1080x1350 PNGs with headless Chrome.
# Usage: ./render.sh out_dir file1.html [file2.html ...]
set -euo pipefail
CHROME="/c/Program Files/Google/Chrome/Application/chrome.exe"
out="$1"; shift
mkdir -p "$out"
for f in "$@"; do
  abs=$(cd "$(dirname "$f")" && pwd -W)/$(basename "$f")
  dir=$(basename "$(dirname "$f")")
  name="${dir}_$(basename "${f%.html}").png"
  "$CHROME" --headless=new --disable-gpu --hide-scrollbars --force-device-scale-factor=1 \
    --window-size=1080,1350 --virtual-time-budget=4000 --allow-file-access-from-files \
    --screenshot="$(cd "$out" && pwd -W)/$name" "file:///$abs" >/dev/null 2>&1
  echo "$out/$name"
done

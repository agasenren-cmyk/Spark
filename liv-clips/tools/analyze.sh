#!/usr/bin/env bash
# Steps 1-5 of CLAUDE.md section 2 for one source file. Writes the raw data to out/:
#   <name>_probe.txt      duration, resolution, fps, audio sample rate
#   <name>_sheet_N.jpg    contact sheets, 1 frame per second, 32 s per sheet (Read these)
#   <name>_scenes.txt     scene-change times already cut into the file
#   <name>_drop.json      drop time and beat grid
# The shot list and dead zones are yours to write into out/<name>_analysis.md.
set -euo pipefail
cd "$(dirname "$0")/.."

src=${1:?usage: tools/analyze.sh raw/FILE.mov}
name=$(basename "${src%.*}")
mkdir -p out

ffprobe -v error -select_streams v:0 -show_entries stream=width,height,r_frame_rate:format=duration \
  -of default=nw=1 "$src" > "out/${name}_probe.txt"
ffprobe -v error -select_streams a:0 -show_entries stream=sample_rate,channels \
  -of default=nw=1 "$src" >> "out/${name}_probe.txt" || true
cat "out/${name}_probe.txt"

w=$(grep '^width=' "out/${name}_probe.txt" | cut -d= -f2)
h=$(grep '^height=' "out/${name}_probe.txt" | cut -d= -f2)
dur=$(grep '^duration=' "out/${name}_probe.txt" | cut -d= -f2)
if [ "$w" -gt "$h" ]; then scale=480:270; else scale=270:480; fi

sheets=$(( ( ${dur%.*} + 32 ) / 32 ))
for ((n = 0; n < sheets; n++)); do
  ffmpeg -v error -y -ss $((n * 32)) -i "$src" -t 32 -vf "fps=1,scale=$scale,tile=8x4" \
    -frames:v 1 "out/${name}_sheet_$((n + 1)).jpg"
done
echo "contact sheets: $sheets (sheet N covers 32*(N-1) to 32*N s, left to right, 8 per row)"

ffmpeg -i "$src" -vf "scale=$scale,select='gt(scene,0.2)',showinfo" -an -f null - 2>&1 \
  | grep -o "pts_time:[0-9.]*" | cut -d: -f2 > "out/${name}_scenes.txt" || true
echo "scene changes: $(wc -l < "out/${name}_scenes.txt")"

python3 tools/drop.py "$src" | tee "out/${name}_drop.json"

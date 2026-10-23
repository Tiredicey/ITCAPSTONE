#!/bin/sh
set -e
cd "$(dirname "$0")"
mkdir -p build
[ -f build/score_master.wav ] || { python3 score.py; python3 master.py; }
python3 render.py --out build/video_only.mp4
ffmpeg -y -hide_banner -loglevel error -i build/video_only.mp4 -i build/score_master.wav -map 0:v -map 1:a -c:v copy -c:a aac -b:a 256k -ar 48000 -shortest -movflags +faststart build/bote_sa_bote_master.mp4
ffmpeg -y -hide_banner -loglevel error -i build/bote_sa_bote_master.mp4 -vf "crop=ih*9/16:ih,scale=1080:1920:flags=lanczos" -c:v libx264 -crf 18 -pix_fmt yuv420p -c:a copy -movflags +faststart build/bote_sa_bote_9x16.mp4
echo BUILD_OK

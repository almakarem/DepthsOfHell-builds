#!/bin/bash
# Renders the website background loops from the game's own assets.
#   PY=/path/to/venv/python (pip bpy 5.x, numpy, opencv-python-headless)
#   BEHEMOTH_BLEND=/path/behemoth_showcase.blend  renders B1 with the re-rigged Behemoth (props skinned to his hands)
#   WORK=/scratch/dir  OUT=/where/the/videos/go
# Headless EEVEE needs EGL (apt: libegl1 libegl-mesa0 libgl1-mesa-dri); it runs on llvmpipe.
# Each scene renders below 1080p (8 samples) and post.py upscales, adds bloom, smoke, embers,
# rain and lightning, and grades; every animated value is periodic, so the loops are seamless.
set -e
HERE=$(cd "$(dirname "$0")" && pwd)
PY=${PY:-python3}; WORK=${WORK:-/tmp/site_videos}; OUT=${OUT:-$WORK/final}
export DOH_REPO=${DOH_REPO:-$(cd "$HERE/../.." && pwd)} EGL_PLATFORM=surfaceless TEX=$WORK/tex
mkdir -p $WORK/tex $OUT
[ -f $WORK/tex/seal.png ] || $PY $HERE/make_seal.py $WORK/tex/seal.png
cd "$DOH_REPO"
render() { # script dir res extra-env...
  local s=$1 d=$2 r=$3; shift 3
  mkdir -p $WORK/$d; env "$@" OUT=$WORK/$d/ RES=$r MODE=anim $PY $HERE/$s > $WORK/$d.log 2>&1
}
finish() { # dir preset size name
  $PY $HERE/post.py $2 $WORK/$1 $WORK/$1/post --size $3
  ffmpeg -loglevel error -y -framerate 24 -i $WORK/$1/post/p_%04d.png -c:v libx264 -preset slow -crf 22 -pix_fmt yuv420p -movflags +faststart -an $OUT/$4.mp4
  ffmpeg -loglevel error -y -framerate 24 -i $WORK/$1/post/p_%04d.png -c:v libvpx-vp9 -crf 34 -b:v 0 -row-mt 1 -cpu-used 2 -pix_fmt yuv420p -an $OUT/$4.webm
  $PY -c "from PIL import Image; Image.open('$WORK/$1/post/p_0000.png').convert('RGB').save('$OUT/$4.jpg', quality=85)"
}
render c1_kitchen.py c1 1440x810 VOL=0.004;  finish c1 c1 1920x1080 C1-first-circle
render c2_court.py   c2 1440x810;            finish c2 c2 1920x1080 C2-second-circle
render c3_chapel.py  c3 1440x810;            finish c3 c3 1920x1080 C3-third-circle
render b_boss.py b1 864x1080 BOSS=behemoth ${BEHEMOTH_BLEND:+BEHEMOTH_BLEND=$BEHEMOTH_BLEND CDIST=6.5 LOOKZ=1.75};  finish b1 boss 1080x1350 B1-behemoth
render b_boss.py b2 864x1080 BOSS=verrier;   finish b2 boss_storm 1080x1350 B2-verrier
render b_boss.py b3 864x1080 BOSS=luvart;    finish b3 boss_rain 1080x1350 B3-luvart

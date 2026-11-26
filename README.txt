DEPTHS OF HELL - WEBSITE BACKGROUND VIDEO KIT
=============================================

Makes the six looping background videos for the website:
  C1-first-circle, C2-second-circle, C3-third-circle   1920x1080, 8 s
  B1-behemoth, B2-verrier, B3-luvart                   1080x1350, 6 s
Each gives an .mp4 (H.264), a .webm (VP9) and a .jpg poster (the first frame),
all 24 fps, no audio, seamless loops, each file under 8 MB. A contact_sheet.jpg
shows four frames of each.


ONE-TIME SETUP (Windows)
  1. Install Python 3.10 or newer from python.org (tick "Add python.exe to PATH").
  2. Open a terminal in this folder and run:
         python -m pip install -r requirements.txt
     (ffmpeg comes with the imageio-ffmpeg package; a system ffmpeg on PATH is used if present.)
  Blender: already installed through Steam (5.3). The scenes were saved with Blender 5.3.0
  and need Blender 5.0 or newer.


THE ONE COMMAND
         python render_all.py

  The videos and contact_sheet.jpg land in the output\ folder. Frames are kept in work\
  (about 2 GB for all six; delete it afterwards if you like).


OPTIONS
  python render_all.py --only=B1                one video (or --only=C1,C3)
  python render_all.py --blender "E:\Blender\blender.exe"   if Blender is somewhere else
  python render_all.py --ffmpeg "C:\ffmpeg\bin\ffmpeg.exe"   a specific ffmpeg
  python render_all.py --frames 0-1             quick test: render two frames only
  python render_all.py --skip-render            redo post and encode from frames in work\
  python render_all.py --help                   everything else

  Blender is looked for in: --blender, then the BLENDER environment variable, then
  D:\SteamLibrary\steamapps\common\Blender\blender.exe, the default Steam folders,
  C:\Program Files\Blender Foundation\Blender *\blender.exe, then PATH.


HOW IT WORKS
  1. Blender renders each scene from scenes\ with EEVEE on the graphics card:
         blender -b scenes\<name>.blend -P kit\blender_setup.py -a -- --out work\<name>\frames
     EEVEE needs no GPU setup. If you switch to Cycles (--engine cycles), blender_setup.py
     picks the GPU with HIP first (AMD Radeon), then OPTIX/CUDA, then falls back to the CPU.
     The look was tuned in EEVEE, so Cycles will look different.
  2. kit\post.py adds the painterly filter, bloom, smoke, embers, rain, lightning and the
     grade. It reads <name>.fx.json (where the smoke and embers sit on screen, frame by frame)
     and <name>.meta.json (preset and lightning timing). Every effect repeats exactly over the
     loop, so the loops stay seamless.
  3. ffmpeg encodes mp4 (crf 22) and webm (crf 34), raising the crf if a file would go over 8 MB.

  Every animated thing in the scenes repeats over the loop length, and the camera is almost
  still (a slight push-in that eases back), so the last frame runs into the first.
  Uploading the videos to the website is a separate step.


SOURCE
  kit\source\ holds the Python scripts that built the scenes (run with Blender's Python from the
  game repo; see run_all.sh there). They are for reference when improving the boss lairs; the
  kit itself only needs the .blend files. The same scripts are in the game repo under
  tools/site_videos/ (branch site-videos).

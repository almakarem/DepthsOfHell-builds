"""Depths of Hell - website background videos: render, post-process and encode.

    python render_all.py                     all six videos
    python render_all.py --only=B1           one video (or --only=C1,C3,B2)

For each scene in scenes/ it
  1. renders the loop with Blender:  blender -b <scene>.blend -P kit/blender_setup.py -a -- ...
  2. runs the 2D pass (kit/post.py): painterly filter, bloom, smoke, embers, rain, lightning, grade
  3. encodes <name>.mp4 (H.264), <name>.webm (VP9) and the first-frame poster <name>.jpg
and finally builds contact_sheet.jpg (4 frames of every video found in the output folder).

Works on Windows, macOS and Linux; needs Python 3.9+ with the packages in requirements.txt.
Run `python render_all.py --help` for the options.
"""
import argparse, glob, json, os, re, shutil, subprocess, sys, time
from concurrent.futures import ProcessPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
SCENES = os.path.join(HERE, "scenes")
KIT = os.path.join(HERE, "kit")
VIDEOS = ["C1-first-circle", "C2-second-circle", "C3-third-circle", "B1-behemoth", "B2-verrier", "B3-luvart"]
MAX_BYTES = 8 * 1024 * 1024          # each encoded file stays under ~8 MB (crf is raised until it fits)


# --- finding the tools -------------------------------------------------------------------------

def find_blender(given):
    cands = []
    if given:
        cands.append(given)
    if os.environ.get("BLENDER"):
        cands.append(os.environ["BLENDER"])
    cands += [r"D:\SteamLibrary\steamapps\common\Blender\blender.exe",
              r"C:\Program Files (x86)\Steam\steamapps\common\Blender\blender.exe",
              r"C:\Program Files\Steam\steamapps\common\Blender\blender.exe"]

    def version_key(p):
        m = re.search(r"Blender (\d+)\.(\d+)", p)
        return (int(m.group(1)), int(m.group(2))) if m else (0, 0)
    cands += sorted(glob.glob(r"C:\Program Files\Blender Foundation\Blender *\blender.exe"), key=version_key, reverse=True)
    cands += ["/Applications/Blender.app/Contents/MacOS/Blender"]
    w = shutil.which("blender")
    if w:
        cands.append(w)
    for c in cands:
        if c and os.path.isfile(c):
            return c
    sys.exit("Blender not found. Pass it with --blender \"C:\\path\\to\\blender.exe\"")


def find_ffmpeg(given):
    if given:
        if os.path.isfile(given) or shutil.which(given):
            return given
        sys.exit("ffmpeg not found at %s" % given)
    w = shutil.which("ffmpeg")
    if w:
        return w
    try:  # pip install imageio-ffmpeg ships its own ffmpeg (with x264 and VP9)
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        sys.exit("ffmpeg not found. Put it on PATH, pass --ffmpeg C:\\path\\to\\ffmpeg.exe, or pip install imageio-ffmpeg")


# --- steps ---------------------------------------------------------------------------------------

def run(cmd, log=None):
    print("  $", " ".join('"%s"' % c if " " in c else c for c in cmd), flush=True)
    if log:
        with open(log, "w", encoding="utf-8", errors="replace") as fh:
            p = subprocess.run(cmd, stdout=fh, stderr=subprocess.STDOUT)
    else:
        p = subprocess.run(cmd)
    if p.returncode != 0:
        raise RuntimeError("command failed (exit %d)%s" % (p.returncode, ", see " + log if log else ""))


def render(name, blender, work, a):
    frames = os.path.join(work, name, "frames")
    os.makedirs(frames, exist_ok=True)
    if a.show:  # Blender opens its window and shows each frame; blender_setup.py starts the render and quits after
        cmd = [blender, os.path.join(SCENES, name + ".blend"), "-P", os.path.join(KIT, "blender_setup.py"),
               "--", "--out", frames, "--engine", a.engine, "--show"]
    else:
        cmd = [blender, "-b", os.path.join(SCENES, name + ".blend"), "-P", os.path.join(KIT, "blender_setup.py"), "-a",
               "--", "--out", frames, "--engine", a.engine]
    if a.frames:
        cmd += ["--frames", a.frames]
    if a.samples:
        cmd += ["--samples", str(a.samples)]
    if a.percent != 100:
        cmd += ["--percent", str(a.percent)]
    log = os.path.join(work, name, "blender.log")
    t = time.time()
    run(cmd, log)
    for line in open(log, encoding="utf-8", errors="replace"):
        if line.startswith("[setup]"):
            print("  " + line.strip())
    print("  rendered in %.0f s" % (time.time() - t))


def _post_chunk(args):
    preset, src, dst, size, frames = args
    cmd = [sys.executable, os.path.join(KIT, "post.py"), preset, src, dst, "--size", size,
           "--only", ",".join(str(f) for f in frames)]
    p = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
    if p.returncode != 0:
        raise RuntimeError("post.py failed:\n" + p.stderr[-2000:])
    return len(frames)


def post(name, work, a):
    src = os.path.join(work, name, "frames")
    dst = os.path.join(work, name, "post")
    os.makedirs(dst, exist_ok=True)
    # post.py reads the scene's projected effect markers and its preset (and lightning) from the frame folder
    shutil.copy(os.path.join(SCENES, name + ".fx.json"), os.path.join(src, "fx.json"))
    meta = json.load(open(os.path.join(SCENES, name + ".meta.json")))
    json.dump(meta, open(os.path.join(src, "meta.json"), "w"))
    fx = json.load(open(os.path.join(src, "fx.json")))
    size = "%dx%d" % (fx["w"], fx["h"])
    frames = sorted(int(re.search(r"f_(\d+)\.png$", f).group(1)) for f in glob.glob(os.path.join(src, "f_*.png")))
    if not frames:
        raise RuntimeError("no rendered frames in " + src)
    workers = max(1, min(a.jobs, len(frames)))
    chunks = [frames[i::workers] for i in range(workers)]
    t = time.time()
    with ProcessPoolExecutor(workers) as ex:
        done = sum(ex.map(_post_chunk, [(meta["preset"], src, dst, size, c) for c in chunks]))
    print("  post-processed %d frames (%s, preset %s) in %.0f s" % (done, size, meta["preset"], time.time() - t))
    return dst, frames


def encode(name, post_dir, frames, ffmpeg, out):
    first = frames[0]
    pattern = os.path.join(post_dir, "p_%04d.png")
    base = [ffmpeg, "-loglevel", "error", "-y", "-framerate", "24", "-start_number", str(first), "-i", pattern]
    sizes = {}
    for ext, crf, codec in (("mp4", 22, ["-c:v", "libx264", "-preset", "slow", "-pix_fmt", "yuv420p", "-movflags", "+faststart"]),
                            ("webm", 34, ["-c:v", "libvpx-vp9", "-b:v", "0", "-row-mt", "1", "-cpu-used", "2", "-pix_fmt", "yuv420p"])):
        path = os.path.join(out, name + "." + ext)
        while True:
            run(base + codec + ["-crf", str(crf), "-an", path])
            sizes[ext] = (os.path.getsize(path), crf)
            if sizes[ext][0] <= MAX_BYTES or crf >= 45:
                break
            crf += 2
    from PIL import Image
    Image.open(os.path.join(post_dir, "p_%04d.png" % first)).convert("RGB").save(os.path.join(out, name + ".jpg"), quality=85)
    print("  %s.mp4 %.2f MB (crf %d), .webm %.2f MB (crf %d), .jpg poster" % (
        name, sizes["mp4"][0] / 1e6, sizes["mp4"][1], sizes["webm"][0] / 1e6, sizes["webm"][1]))


def contact_sheet(work, out):
    from PIL import Image, ImageDraw
    rows, H = [], 300
    for name in VIDEOS:
        post_dir = os.path.join(work, name, "post")
        files = sorted(glob.glob(os.path.join(post_dir, "p_*.png")))
        if not files:
            continue
        picks = [files[min(len(files) - 1, round(i * len(files) / 4))] for i in range(4)]
        ims = []
        for p in picks:
            im = Image.open(p).convert("RGB")
            ims.append(im.resize((round(im.width * H / im.height), H)))
        row = Image.new("RGB", (260 + sum(i.width + 8 for i in ims), H + 16), (12, 10, 10))
        ImageDraw.Draw(row).text((10, H // 2), name, fill=(230, 200, 160))
        x = 260
        for im in ims:
            row.paste(im, (x, 8))
            x += im.width + 8
        rows.append(row)
    if not rows:
        return
    sheet = Image.new("RGB", (max(r.width for r in rows), sum(r.height for r in rows)), (12, 10, 10))
    y = 0
    for r in rows:
        sheet.paste(r, (0, y))
        y += r.height
    path = os.path.join(out, "contact_sheet.jpg")
    sheet.save(path, quality=88)
    print("contact sheet:", path)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--only", default="", help="videos to make, e.g. B1 or C1,C3 (default: all six)")
    ap.add_argument("--blender", default="", help="path to blender.exe (default: Steam or Program Files install)")
    ap.add_argument("--ffmpeg", default="", help="path to ffmpeg.exe (default: on PATH, else imageio-ffmpeg)")
    ap.add_argument("--out", default=os.path.join(HERE, "output"), help="where the videos go (default: output/)")
    ap.add_argument("--work", default=os.path.join(HERE, "work"), help="where frames go (default: work/)")
    ap.add_argument("--frames", default="", help="render only these frames, e.g. 0-1 (a quick test)")
    ap.add_argument("--samples", type=int, default=0, help="override render samples (scenes are saved with 32)")
    ap.add_argument("--percent", type=int, default=100, help="render size in percent (quick tests)")
    ap.add_argument("--engine", default="scene", choices=["scene", "eevee", "cycles"],
                    help="the scenes are made for EEVEE; cycles uses the GPU via HIP (AMD), else OPTIX/CUDA")
    ap.add_argument("--jobs", type=int, default=max(1, (os.cpu_count() or 2) - 1), help="parallel post-processing workers")
    ap.add_argument("--skip-render", action="store_true", help="reuse frames already in work/")
    ap.add_argument("--show", action="store_true", help="open Blender's window and watch each frame render (closes itself after each scene)")
    a = ap.parse_args()

    names = VIDEOS
    if a.only:
        want = [w.strip().upper() for w in a.only.split(",") if w.strip()]
        names = [n for n in VIDEOS if any(n.upper() == w or n.upper().startswith(w + "-") for w in want)]
        if not names:
            sys.exit("--only=%s matches none of %s" % (a.only, ", ".join(VIDEOS)))
    blender = None if a.skip_render else find_blender(a.blender)
    ffmpeg = find_ffmpeg(a.ffmpeg)
    os.makedirs(a.out, exist_ok=True)
    print("Blender:", blender or "(skipped)")
    print("ffmpeg: ", ffmpeg)
    t0 = time.time()
    for name in names:
        print("\n== %s" % name, flush=True)
        if not a.skip_render:
            fdir = os.path.join(a.work, name, "frames")
            for old in glob.glob(os.path.join(fdir, "f_*.png")):
                os.remove(old)
            render(name, blender, a.work, a)
        pdir = os.path.join(a.work, name, "post")
        for old in glob.glob(os.path.join(pdir, "p_*.png")):
            os.remove(old)
        post_dir, frames = post(name, a.work, a)
        encode(name, post_dir, frames, ffmpeg, a.out)
    contact_sheet(a.work, a.out)
    print("\nDone in %.1f min. Videos are in %s" % ((time.time() - t0) / 60, a.out))


if __name__ == "__main__":
    main()

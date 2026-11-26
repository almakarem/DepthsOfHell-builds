"""Runs inside Blender before it renders a scene (render_all.py starts it as
    blender -b <scene>.blend -P blender_setup.py -a -- --out <dir> [options]

Sets where the frames go and, if asked, the frame range, samples and size. The scenes are made for
EEVEE, which renders on the graphics card through its normal driver with no setup. If the scene is
switched to Cycles (--engine cycles) the GPU is set up here: HIP first (AMD Radeon), then OPTIX, CUDA,
oneAPI and Metal, then the CPU.
"""
import bpy, sys, os, argparse

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
ap = argparse.ArgumentParser(prog="blender_setup.py")
ap.add_argument("--out", required=True, help="folder for the frames (f_0000.png ...)")
ap.add_argument("--frames", default="", help="first-last frame, e.g. 0-1 (default: the whole loop)")
ap.add_argument("--samples", type=int, default=0, help="render samples (default: as saved in the scene)")
ap.add_argument("--percent", type=int, default=100, help="render size in percent (for quick tests)")
ap.add_argument("--engine", default="scene", choices=["scene", "eevee", "cycles"])
ap.add_argument("--device", default="gpu", choices=["gpu", "cpu"], help="Cycles only")
ap.add_argument("--show", action="store_true", help="Blender runs with its window: render the animation in a render window, then quit")
a = ap.parse_args(argv)

sc = bpy.context.scene
r = sc.render
os.makedirs(a.out, exist_ok=True)
r.filepath = os.path.join(os.path.abspath(a.out), "f_")
r.use_file_extension = True
r.image_settings.file_format = "PNG"
r.image_settings.color_mode = "RGB"
r.image_settings.color_depth = "8"
r.resolution_percentage = a.percent
r.use_overwrite = True
r.use_placeholder = False
if a.frames:
    f0, f1 = (int(x) for x in a.frames.split("-"))
    sc.frame_start, sc.frame_end = f0, f1

if a.engine == "eevee":
    r.engine = "BLENDER_EEVEE" if "BLENDER_EEVEE" in [e.identifier for e in r.bl_rna.properties["engine"].enum_items] else "BLENDER_EEVEE_NEXT"
elif a.engine == "cycles":
    r.engine = "CYCLES"


def setup_cycles_device(want_gpu):
    """Picks the first GPU backend that has a device: HIP, OPTIX, CUDA, ONEAPI, METAL."""
    sc.cycles.device = "CPU"
    if not want_gpu:
        return "CPU"
    try:
        prefs = bpy.context.preferences.addons["cycles"].preferences
    except KeyError:
        return "CPU (Cycles add-on not found)"
    for backend in ("HIP", "OPTIX", "CUDA", "ONEAPI", "METAL"):
        try:
            prefs.compute_device_type = backend
        except TypeError:
            continue  # this backend is not built into this Blender
        try:
            prefs.refresh_devices()
        except AttributeError:
            prefs.get_devices()
        gpus = [d for d in prefs.devices if d.type == backend]
        if not gpus:
            continue
        for d in prefs.devices:
            d.use = d.type == backend
        sc.cycles.device = "GPU"
        return "%s: %s" % (backend, ", ".join(d.name for d in gpus))
    prefs.compute_device_type = "NONE"
    return "CPU (no GPU backend found)"


if r.engine == "CYCLES":
    dev = setup_cycles_device(a.device == "gpu")
    if a.samples:
        sc.cycles.samples = a.samples
else:
    dev = "graphics card via the display driver (EEVEE)"
    if a.samples:
        sc.eevee.taa_render_samples = a.samples

print("[setup] %s  engine=%s  device=%s  frames=%d-%d  size=%dx%d@%d%%  -> %s" % (
    os.path.basename(bpy.data.filepath), r.engine, dev, sc.frame_start, sc.frame_end,
    r.resolution_x, r.resolution_y, r.resolution_percentage, r.filepath), flush=True)


# --show: Blender was started with its window (no -b, no -a). Start the animation render in a render
# window once the UI is up, and quit Blender when it finishes (or is cancelled) so render_all.py carries on.
if a.show and not bpy.app.background:
    prefs = bpy.context.preferences
    prefs.use_preferences_save = False          # nothing below is saved into the user's preferences
    prefs.view.render_display_type = "WINDOW"   # show the frames in their own render window

    def _quit():
        bpy.ops.wm.quit_blender()
        return None

    def _done(scene, *args):
        print("[setup] render finished, closing Blender", flush=True)
        bpy.app.timers.register(_quit, first_interval=1.0)

    bpy.app.handlers.render_complete.append(_done)
    bpy.app.handlers.render_cancel.append(_done)

    def _start():
        wm = bpy.context.window_manager
        if not wm.windows:
            return 0.5
        win = wm.windows[0]
        with bpy.context.temp_override(window=win, screen=win.screen):
            bpy.ops.render.render("INVOKE_DEFAULT", animation=True)
        return None

    bpy.app.timers.register(_start, first_interval=2.0)

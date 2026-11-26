"""C3: the drowned chapel of Louviers - black water with rain rings, many candles, censers swinging
on chains, rain through the broken roof, pale teal light with warm candle points."""
import sys, os, math, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy
import lib, bits
from lib import TAU

W, H = [int(v) for v in os.environ.get("RES", "1280x720").split("x")]
N = int(os.environ.get("FRAMES", "192"))
SAMPLES = int(os.environ.get("SAMPLES", "8"))
OUT = os.environ.get("OUT", "/tmp/c3/")

lib.reset()
sc = lib.setup_render(W, H, N, SAMPLES, exposure=float(os.environ.get("EXPOSURE", "0.0")))
lib.world((0.006, 0.012, 0.014), 1.0, vol_density=float(os.environ.get("VOL", "0.007")), vol_color=(0.75, 0.9, 0.9),
          anisotropy=0.5)
if os.environ.get("RT", "1") == "1":
    ee = sc.eevee
    ee.use_raytracing = True
    try:
        ee.ray_tracing_method = "SCREEN"
        ee.ray_tracing_options.resolution_scale = "2"
        ee.ray_tracing_options.screen_trace_quality = 0.5
        ee.ray_tracing_options.use_denoise = True
    except Exception as ex:
        print("rt opt", ex)
if os.environ.get("VSHADOW", "1") == "1":
    sc.eevee.use_volumetric_shadows = True
sc.eevee.volumetric_tile_size = os.environ.get("VTILE", "4")
rnd = random.Random(21)
P = "assets/props/"
WL = 0.22  # the water's surface

# --- the stone floor under the water, and the water ---------------------------------------------
bpy.ops.mesh.primitive_plane_add(size=1, location=(0, 0, 0))
fl = bpy.context.active_object
fl.scale = (30, 40, 1)
fl.data.materials.append(lib.ground_surface_mat("vault_wet", gain=0.4))
bpy.ops.mesh.primitive_plane_add(size=1, location=(0, 4, WL))
water = bpy.context.active_object
water.scale = (26, 34, 1)
wm = bpy.data.materials.new("water")
wm.use_nodes = True
nt = wm.node_tree
for n in list(nt.nodes):
    nt.nodes.remove(n)
Nn, Ln = nt.nodes, nt.links.new
out = Nn.new("ShaderNodeOutputMaterial")
geo = Nn.new("ShaderNodeNewGeometry")
r1 = lib.ripple_bump(nt, geo.outputs["Position"], N, scale=1.1, cycles=3, width=0.04, seed=0.0)
r2 = lib.ripple_bump(nt, geo.outputs["Position"], N, scale=1.7, cycles=4, width=0.035, seed=3.3)
swell = lib.loop_noise(nt, geo.outputs["Position"], N, 0.7)
swell.inputs["Scale"].default_value = 0.35
swell.inputs["Detail"].default_value = 2
add = Nn.new("ShaderNodeMath"); add.operation = "ADD"
Ln(r1, add.inputs[0]); Ln(r2, add.inputs[1])
add2 = Nn.new("ShaderNodeMath"); add2.operation = "MULTIPLY_ADD"
Ln(swell.outputs["Fac"], add2.inputs[0]); add2.inputs[1].default_value = 1.2
Ln(add.outputs[0], add2.inputs[2])
bump = Nn.new("ShaderNodeBump")
bump.inputs["Strength"].default_value = 0.35
bump.inputs["Distance"].default_value = 0.02
Ln(add2.outputs[0], bump.inputs["Height"])
b = Nn.new("ShaderNodeBsdfPrincipled")
b.inputs["Base Color"].default_value = (0.004, 0.009, 0.010, 1)
b.inputs["Roughness"].default_value = 0.03
b.inputs["Specular IOR Level"].default_value = 1.0
b.inputs["IOR"].default_value = 2.4
Ln(bump.outputs[0], b.inputs["Normal"])
Ln(b.outputs[0], out.inputs[0])
water.data.materials.append(wm)
bpy.ops.mesh.primitive_plane_add(size=400, location=(0, 0, -0.1))
bpy.context.active_object.data.materials.append(lib.flat_mat("void", (0.002, 0.003, 0.003), 1.0))

# --- walls: wet crumbling stone, two courses high; the rose window over the altar -----------------
wet = lib.wall_surface_mat("crumbling_wet", gain=0.75)
flat = dict(wall=wet, shade=lib.wall_surface_mat("crumbling_wet", shade=0.45, gain=0.75), stone=lib.wall_surface_mat("stone", gain=0.8),
            iron=lib.flat_mat("w_iron", (0.13, 0.13, 0.14), 0.55, 0.7), wood=lib.flat_mat("w_wood", (0.3, 0.18, 0.1), 0.85),
            clay=lib.flat_mat("w_clay", (0.5, 0.27, 0.17), 0.8), cloth=lib.flat_mat("w_cloth", (0.4, 0.33, 0.24), 0.95),
            dark=lib.flat_mat("w_dark", (0.03, 0.02, 0.02), 1.0), gold=lib.flat_mat("w_gold", (0.6, 0.42, 0.15), 0.35, 1.0))
wall = {k: lib.source(P + "walls/%s.glb" % k, flat) for k in ["wall_a", "wall_b", "wall_niche", "wall_broken", "wall_buttress"]}
XW, YB = -12.0, 18.0
for row in range(2):
    z = row * 4.4
    for i in range(6):  # back wall
        x = -10 + 4 * i
        if row == 1 and abs(x) < 4:
            continue  # the rose window's place
        k = ["wall_a", "wall_b"][(i + row) % 2] if not (row == 1 and i == 5) else "wall_broken"
        lib.place(wall[k], (x, YB + 0.57, z), 0.0)
    for i in range(7):  # west wall
        y = YB - 2 - 4 * i
        k = ["wall_a", "wall_niche", "wall_b", "wall_buttress"][(i + row) % 4] if row == 0 else ["wall_a", "wall_b"][i % 2]
        if row == 1 and i in (2, 5):
            k = "wall_broken"
        lib.place(wall[k], (XW - 0.57, y, z), math.pi / 2)
GLASS = dict(glass_amber=((1.0, 0.6, 0.2), 1.0), glass_azure=((0.25, 0.5, 1.0), 1.0), glass_rose=((1.0, 0.3, 0.35), 1.0))
ch = lambda name: lib.source(P + "chapel/%s.gltf" % name, emit=GLASS)
lib.place(ch("rose_window"), (0, YB + 0.2, 0.9), 0.0, 1.0)
Lr = lib.light("AREA", (0, YB - 0.8, 8.5), (0.75, 0.8, 1.0), 1500, name="rose", shadow=False, size=7, spec=0.0)
Lr.rotation_euler = (math.radians(-70), 0, 0)
Lr.rotation_euler = (math.radians(-90 - 20), 0, 0)

# --- pillars, pews, fonts, booths, the altar --------------------------------------------------------
for (x, y) in [(-7.5, -6.0), (-7.5, 3.0), (-7.5, 12.0), (7.5, 12.0)]:
    lib.place(ch("pillar"), (x, y, 0), 0.0)
for y in [-7.0, -4.2, 6.0, 8.8]:
    for side in (-1, 1):
        if side > 0 and y < 0:
            continue
        lib.place(ch("pew"), (3.8 * side, y, 0), math.pi + rnd.uniform(-0.04, 0.04))
lib.place(ch("pew_short"), (3.6, -3.5, 0), math.pi + 0.25)  # knocked askew by the flood
lib.place(ch("baptismal_font"), (0.0, 1.5, 0), 0.0)
for side in (-1, 1):
    lib.place(ch("holy_water_font"), (5.6 * side, -1.5, 0), 0.0)
lib.place(ch("confession_booth"), (XW + 1.3, -1.0, 0), -math.pi / 2)
lib.place(ch("confession_booth"), (XW + 1.3, 7.5, 0), -math.pi / 2)
lib.place(ch("altar"), (0.0, YB - 2.6, 0), 0.0)
lib.place(ch("bell_rope"), (XW + 0.9, -8.5, 0), math.pi / 2)

# --- candles: on the altar, round the pillars and the font, on stands -------------------------------
lights_budget = []
bits.candles((-1.6, YB - 2.5), 7, 0.5, N, seed=1, base_z=1.32, light=120, hmax=0.45)
bits.candles((1.6, YB - 2.5), 7, 0.5, N, seed=2, base_z=1.32, light=120, hmax=0.45)
for i, (x, y) in enumerate([(-6.2, -6.0), (-6.2, 3.0), (-6.4, 11.6), (6.3, 11.4), (1.8, 0.2), (-1.9, 2.9),
                            (-10.0, 4.0), (4.0, 14.5), (-4.5, 15.2), (9.0, 3.5)]):
    bits.candles((x, y), rnd.randint(8, 14), 0.7, N, seed=10 + i, base_z=WL, light=110, hmax=0.6)
stand = lib.source(P + "new/candle_stand.gltf")
tips = lib.wax_tips(stand)
for i, (x, y) in enumerate([(-2.8, 12.2), (2.8, 12.2), (-3.4, -2.0), (5.0, 6.8)]):
    lib.place(stand, (x, y, 0), 0.0)
    for t in tips:
        lib.flame((x + t.x, y + t.y, t.z + 0.01), 0.08, N, seed=700 + i,
                  mat=lib.flame_mat("candle_flame"))
    Ls = lib.light("POINT", (x, y - 0.2, 2.1), (1.0, 0.62, 0.3), 60, radius=0.1, name="stand", shadow=False, spec=0.0)
    lib.flicker(Ls, N, 60, 0.15, seed=710 + i)
# the chandelier over the nave, its candles lit
chand = ch("chandelier")
ct = lib.wax_tips(chand)
cz = 3.6
for (x, y) in [(0.0, 8.5)]:
    lib.place(chand, (x, y, cz), 0.0)
    for j, t in enumerate(ct):
        if t.z < 0.6:
            lib.flame((x + t.x, y + t.y, cz + t.z + 0.01), 0.08, N, seed=800 + j, mat=lib.flame_mat("candle_flame"))
    Lc = lib.light("POINT", (x, y, cz + 0.4), (1.0, 0.62, 0.3), 220, radius=0.6, name="chand", shadow=False, spec=0.0)
    lib.flicker(Lc, N, 220, 0.1, seed=820)

# --- censers swinging on chains --------------------------------------------------------------------
censer = lib.source(P + "luvart/censer.glb")
iron = lib.flat_mat("chain_iron", (0.05, 0.05, 0.05), 0.4, 0.9)
for i, (x, y, drop) in enumerate([(-3.8, 3.5, 6.0), (3.4, 10.5, 6.6), (-9.0, 11.0, 5.4), (8.8, -1.0, 6.2)]):
    piv = bpy.data.objects.new("censer_pivot", None)
    sc.collection.objects.link(piv)
    piv.location = (x, y, 11.5)
    nl = int(drop / (0.16 * 0.78))
    bits.chain("cch%d" % i, nl, 0.16, iron, (0, 0, 0), parent=piv, thick=0.022)
    c = lib.place(censer, (0, 0, -drop - 0.45), rnd.random() * TAU, 0.9)
    c.parent = piv
    amp = math.radians(5.0 + 2 * i)
    lib.key_series(piv, "rotation_euler", [amp * math.sin(TAU * 2 * f / N + i) for f in range(N)], index=0)
    lib.key_series(piv, "rotation_euler", [amp * 0.6 * math.sin(TAU * 1 * f / N + i * 2) for f in range(N)], index=1)
    # a coal inside it, and its smoke
    Lg = lib.light("POINT", (0, 0, -drop - 0.3), (1.0, 0.5, 0.2), 25, radius=0.1, name="censer_coal", shadow=False, spec=0.0)
    Lg.parent = piv
    lib.fx_marker("smoke", (x, y, 11.5 - drop - 0.1), rate=0.45, width=0.5, height=4.0, color=(0.55, 0.6, 0.6))
# loose hanging chains
for i in range(7):
    x, y = rnd.uniform(-10, 9), rnd.uniform(-6, 16)
    piv = bpy.data.objects.new("chain_pivot", None)
    sc.collection.objects.link(piv)
    piv.location = (x, y, 11.5)
    drop = rnd.uniform(3.5, 7.0)
    bits.chain("hc%d" % i, int(drop / 0.125), 0.16, iron, (0, 0, 0), parent=piv, thick=0.02)
    amp = math.radians(rnd.uniform(2, 4))
    lib.key_series(piv, "rotation_euler", [amp * math.sin(TAU * f / N + i) for f in range(N)], index=0)

# --- the broken roof: a few beams left, and the light coming down through it -------------------------
beam = lib.flat_mat("roof_beam", (0.06, 0.045, 0.035), 0.8)
for (y, x0, x1, tilt) in [(16.0, -12.5, -5.5, 0.05), (11.0, -12.5, -8.0, -0.12)]:
    bits.box("roof_beam", (x1 - x0, 0.4, 0.5), beam, ((x0 + x1) / 2, y, 10.5), (0, tilt, 0), bevel=0.03)
moon = lib.light("SPOT", (2.5, 2.0, 22), (0.62, 0.92, 0.9), 26000, radius=2.5, name="moon_shaft", spot=math.radians(32), spec=0.6)
moon.rotation_euler = (math.radians(-6), math.radians(8), 0)
lib.light("SUN", (0, 0, 20), (0.5, 0.8, 0.8), 0.12, rot=(math.radians(35), 0, math.radians(200)), name="sky", shadow=False)
fill = lib.light("POINT", (6, -10, 10), (0.4, 0.62, 0.62), 1200, radius=4, name="fill", shadow=False, spec=0.0)

# --- camera: from the south-east, above, toward the altar --------------------------------------------
centre = (-0.5, 5.5, 0.0)
el = math.radians(float(os.environ.get("ELEV", "36")))
dist = float(os.environ.get("DIST", "38"))
path = lib.gentle_path(centre, el, dist, -26, (centre[0], centre[1] + 0.4, 3.6))
cam = lib.camera((0, -30, 30), centre, lens=float(os.environ.get("LENS", "35")))
lib.cyclic_camera(cam, N, path)

os.makedirs(OUT, exist_ok=True)
lib.export_fx(OUT + "fx.json")
lib.save(OUT + "c3.blend")
if os.environ.get("MODE") == "build":   # scene file only, rendered elsewhere
    raise SystemExit(0)
if os.environ.get("MODE", "still") == "still":
    for f in [int(x) for x in os.environ.get("STILLS", "0").split(",")]:
        sc.frame_set(f)
        sc.render.filepath = OUT + "still_%03d.png" % f
        bpy.ops.render.render(write_still=True)
else:
    sc.render.filepath = OUT + "f_"
    sc.frame_start = int(os.environ.get("F0", "0"))
    sc.frame_end = int(os.environ.get("F1", str(N - 1)))
    bpy.ops.render.render(animation=True)

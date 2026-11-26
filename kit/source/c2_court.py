"""C2: Verrier's Court of Edicts in a storm - broken pillars, the throne, the seal's gold runes,
cold lightning through tall broken windows, wind in the banners (rain is the post pass's)."""
import sys, os, math, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy
import lib, bits
from lib import TAU

W, H = [int(v) for v in os.environ.get("RES", "1280x720").split("x")]
N = int(os.environ.get("FRAMES", "192"))
SAMPLES = int(os.environ.get("SAMPLES", "8"))
OUT = os.environ.get("OUT", "/tmp/c2/")
HERE = os.path.dirname(os.path.abspath(__file__))
TEX = os.environ.get("TEX", os.path.join(HERE, "tex")) + "/"

lib.reset()
sc = lib.setup_render(W, H, N, SAMPLES, exposure=float(os.environ.get("EXPOSURE", "0.0")))
lib.world((0.004, 0.006, 0.012), 1.0, vol_density=float(os.environ.get("VOL", "0.006")), vol_color=(0.6, 0.7, 0.9))
rnd = random.Random(11)
P = "assets/props/"
FLASHES = [(36, 1.0), (41, 0.7), (112, 0.75), (117, 1.0), (165, 0.55)]
flash = lib.flash_values(N, FLASHES)

R = 19.0  # the hall's radius (inner face of the wall)

# --- floor: the court's shrine flags, wet, cracked in patches ---------------------------------
fmat = lib.ground_surface_mat("shrine", gain=0.62, patch="cracked", patch_amount=0.3, patch_scale=6.0, wet=0.35)
bpy.ops.mesh.primitive_circle_add(vertices=96, radius=R + 1.0, fill_type="NGON", location=(0, 0, 0))
fl = bpy.context.active_object
fl.data.materials.append(fmat)
bpy.ops.mesh.primitive_plane_add(size=300, location=(0, 0, -0.05))
bpy.context.active_object.data.materials.append(lib.flat_mat("void", (0.003, 0.003, 0.004), 1.0))

# --- the seal: brass inlay with the law's runes, glowing gold, a ripple running out -------------
seal_r = 6.8
bpy.ops.mesh.primitive_plane_add(size=seal_r * 2, location=(0, 0, 0.012))
seal = bpy.context.active_object
sm = bpy.data.materials.new("seal")
sm.use_nodes = True
nt = sm.node_tree
for n in list(nt.nodes):
    nt.nodes.remove(n)
Nn, Ln = nt.nodes, nt.links.new
out = Nn.new("ShaderNodeOutputMaterial")
tc = Nn.new("ShaderNodeTexCoord")
it = Nn.new("ShaderNodeTexImage")
it.image = lib.img(TEX + "seal.png", "Non-Color")
Ln(tc.outputs["UV"], it.inputs[0])
# distance from the middle, for the ripple
sub = Nn.new("ShaderNodeVectorMath"); sub.operation = "SUBTRACT"; sub.inputs[1].default_value = (0.5, 0.5, 0)
Ln(tc.outputs["UV"], sub.inputs[0])
ln = Nn.new("ShaderNodeVectorMath"); ln.operation = "LENGTH"
Ln(sub.outputs[0], ln.inputs[0])
rip = Nn.new("ShaderNodeMath"); rip.operation = "SUBTRACT"
Ln(ln.outputs["Value"], rip.inputs[0])
lib.key_series(rip.inputs[1], "default_value", [((f / N) * 2 % 1.0) * 0.62 for f in range(N)])
ab = Nn.new("ShaderNodeMath"); ab.operation = "ABSOLUTE"
Ln(rip.outputs[0], ab.inputs[0])
band = Nn.new("ShaderNodeMapRange")
band.inputs["From Min"].default_value = 0.0
band.inputs["From Max"].default_value = 0.05
band.inputs["To Min"].default_value = 2.2
band.inputs["To Max"].default_value = 1.0
Ln(ab.outputs[0], band.inputs["Value"])
pulse = Nn.new("ShaderNodeMath"); pulse.operation = "MULTIPLY"
Ln(band.outputs[0], pulse.inputs[0])
lib.key_series(pulse.inputs[1], "default_value", [1.5 + 0.5 * math.sin(TAU * 2 * f / N) for f in range(N)])
em_s = Nn.new("ShaderNodeMath"); em_s.operation = "MULTIPLY"
Ln(pulse.outputs[0], em_s.inputs[0])
Ln(it.outputs["Color"], em_s.inputs[1])
b = Nn.new("ShaderNodeBsdfPrincipled")
b.inputs["Base Color"].default_value = (0.55, 0.38, 0.12, 1)
b.inputs["Metallic"].default_value = 1.0
b.inputs["Roughness"].default_value = 0.35
b.inputs["Emission Color"].default_value = (1.0, 0.62, 0.18, 1)
Ln(em_s.outputs[0], b.inputs["Emission Strength"])
tr = Nn.new("ShaderNodeBsdfTransparent")
mx = Nn.new("ShaderNodeMixShader")
Ln(it.outputs["Color"], mx.inputs[0])
Ln(tr.outputs[0], mx.inputs[1])
Ln(b.outputs[0], mx.inputs[2])
Ln(mx.outputs[0], out.inputs[0])
try:
    sm.surface_render_method = "DITHERED"
except Exception:
    pass
seal.data.materials.append(sm)
seal.visible_shadow = False
for k in range(4):
    a = TAU * k / 4 + 0.4
    L = lib.light("POINT", (math.cos(a) * 3.5, math.sin(a) * 3.5, 0.6), (1.0, 0.65, 0.25), 140, radius=1.5,
                  name="seal_glow", shadow=False)
    lib.key_series(L.data, "energy", [140 * (1.5 + 0.5 * math.sin(TAU * 2 * f / N)) / 1.5 for f in range(N)])

# --- walls: the court's temple stone, in a ring, pillars at the joints, four storm windows ------
temple = lib.wall_surface_mat("temple", gain=0.95)
stone_m = lib.wall_surface_mat("stone")
flat = dict(wall=temple, shade=lib.wall_surface_mat("temple", shade=0.45), stone=stone_m,
            iron=lib.flat_mat("w_iron", (0.13, 0.13, 0.14), 0.55, 0.7), wood=lib.flat_mat("w_wood", (0.3, 0.18, 0.1), 0.85),
            clay=lib.flat_mat("w_clay", (0.5, 0.27, 0.17), 0.8), cloth=lib.flat_mat("w_cloth", (0.4, 0.33, 0.24), 0.95),
            dark=lib.flat_mat("w_dark", (0.03, 0.02, 0.02), 1.0), gold=lib.flat_mat("w_gold", (0.6, 0.42, 0.15), 0.35, 1.0))
wall = {k: lib.source(P + "walls/%s.glb" % k, flat) for k in
        ["wall_a", "wall_b", "wall_niche", "wall_buttress", "wall_broken", "pillar", "column", "pillar_low", "torch"]}
court_stone = lib.flat_mat("court_stone", (0.26, 0.24, 0.27), 0.85)
gold_trim = lib.flat_mat("gold_trim", (0.42, 0.32, 0.15), 0.45, 0.8)
WIN = [-36, -12, 12, 36]
step = 12
sky_mats = []
for k in range(-8, 9):
    a_deg = k * step
    a = math.radians(a_deg)
    pos = (R * math.sin(a), R * math.cos(a), 0)
    # the wall piece's local +y points away from the middle
    rot = -a
    off = 0.57
    if a_deg in WIN:
        # a tall broken window: stone jambs, sill, lintel, a cracked mullion and the storm in it
        root = bpy.data.objects.new("window", None)
        sc.collection.objects.link(root)
        root.location = ((R + 0.4) * math.sin(a), (R + 0.4) * math.cos(a), 0)
        root.rotation_euler = (0, 0, rot)
        for (x, y, z, sx, sy, sz, r_) in [(-1.6, 0, 3.3, 0.8, 1.0, 6.6, 0), (1.6, 0, 3.3, 0.8, 1.0, 6.6, 0),
                                          (0, 0, 6.85, 4.0, 1.1, 0.5, 0), (0, 0, 0.55, 4.0, 1.15, 1.1, 0),
                                          (0.25, -0.1, 4.0, 0.16, 0.16, 3.4, 0.45)]:
            bits.box("winpart", (sx, sy, sz), stone_m if sx > 0.5 else court_stone, (x, y, z), (0, r_, 0), parent=root, bevel=0.03)
        # pointed arch top
        for side in (-1, 1):
            bits.box("arch", (1.9, 1.0, 0.45), stone_m, (side * 0.75, 0, 7.4), (0, side * 0.55, 0), parent=root, bevel=0.03)
        sky = bits.box("sky", (2.4, 0.05, 6.4), None, (0, 0.35, 3.9), parent=root)
        skm = bpy.data.materials.new("storm_sky%d" % k)
        skm.use_nodes = True
        snt = skm.node_tree
        for n in list(snt.nodes):
            snt.nodes.remove(n)
        so = snt.nodes.new("ShaderNodeOutputMaterial")
        stc = snt.nodes.new("ShaderNodeTexCoord")
        nz = lib.loop_noise(snt, stc.outputs["Object"], N, 0.8)
        nz.inputs["Scale"].default_value = 0.6
        nz.inputs["Detail"].default_value = 5
        rmp = snt.nodes.new("ShaderNodeValToRGB")
        rmp.color_ramp.elements[0].color = (0.01, 0.015, 0.035, 1)
        rmp.color_ramp.elements[1].color = (0.12, 0.18, 0.32, 1)
        snt.links.new(nz.outputs["Fac"], rmp.inputs[0])
        se = snt.nodes.new("ShaderNodeEmission")
        snt.links.new(rmp.outputs[0], se.inputs[0])
        snt.links.new(se.outputs[0], so.inputs[0])
        lib.key_series(se.inputs[1], "default_value", [0.6 + 14.0 * v for v in flash])
        sky.data.materials.append(skm)
        sky.visible_shadow = False
        # the flash coming in through it
        Lw = lib.light("AREA", (0, 0, 0), (0.6, 0.72, 1.0), 0, name="win_light", shadow=True, size=2.4)
        Lw.parent = root
        Lw.location = (0, -0.4, 4.0)
        Lw.rotation_euler = (math.radians(-90 + 30), 0, 0)
        Lw.data.shape = "RECTANGLE"
        Lw.data.size = 2.4
        Lw.data.size_y = 6.0
        lib.key_series(Lw.data, "energy", [40 + 9000 * v for v in flash])
        lib.fx_marker("window", (root.location.x, root.location.y, 4.0))
    else:
        kind = ["wall_a", "wall_buttress", "wall_b", "wall_niche"][(k + 8) % 4]
        if k in (-7, 6):
            kind = "wall_broken"
        lib.place(wall[kind], (pos[0] + off * math.sin(a), pos[1] + off * math.cos(a), 0), rot)
    # pillars at the joints
    aj = math.radians(a_deg + step / 2)
    if k < 8:
        lib.place(wall["pillar"], ((R - 0.2) * math.sin(aj), (R - 0.2) * math.cos(aj), 0), -aj)

# torches on the pillars beside the windows, burning low
for i, a_deg in enumerate([-48, -24, 0, 24, 48]):
    a = math.radians(a_deg + 6)
    p = ((R - 1.15) * math.sin(a), (R - 1.15) * math.cos(a), 2.4)
    lib.place(wall["torch"], p, -a)
    f, L = lib.flame((p[0] - 0.35 * math.sin(a), p[1] - 0.35 * math.cos(a), p[2] + 0.55), 0.3, N, seed=300 + i,
                     light_energy=160, light_up=0.25)
    L.location.x -= 0.5 * math.sin(a)
    L.location.y -= 0.5 * math.cos(a)
    lib.fx_marker("embers", (p[0] - 0.35 * math.sin(a), p[1] - 0.35 * math.cos(a), p[2] + 0.7), count=5, spread=0.15, rise=2.0)

# --- the throne on its dais ---------------------------------------------------------------------
th = (0.0, 13.6)
for step_i in range(2):
    r0 = 5.2 - step_i * 1.6
    bits.cyl("dais", r0, 0.32, court_stone, (th[0], th[1] - 1.2, 0.16 + step_i * 0.32), seg=48, r2=r0 - 0.08)
    t = bits.torus("dais_trim", r0 - 0.06, 0.05, gold_trim, (th[0], th[1] - 1.2, 0.32 + step_i * 0.32), seg=64, rseg=6)
troot = bpy.data.objects.new("throne", None)
sc.collection.objects.link(troot)
troot.location = (th[0], th[1] - 0.6, 0.64)
dark_stone = lib.flat_mat("throne_stone", (0.12, 0.11, 0.13), 0.75)
for (x, y, z, sx, sy, sz) in [(0, 0, 0.45, 2.4, 1.8, 0.9), (0, 0.75, 2.4, 2.4, 0.4, 3.0),
                              (-1.25, 0.05, 1.15, 0.35, 1.7, 0.5), (1.25, 0.05, 1.15, 0.35, 1.7, 0.5),
                              (0, -0.05, 0.95, 2.0, 1.5, 0.12)]:
    bits.box("throne_part", (sx, sy, sz), dark_stone if sz != 0.12 else lib.flat_mat("throne_cloth", (0.18, 0.03, 0.05), 0.9),
             (x, y, z), parent=troot, bevel=0.04)
# the high back's pointed crown, one half knocked aside (cracked)
bits.box("crown", (1.5, 0.38, 1.6), dark_stone, (-0.55, 0.75, 4.25), (0, 0.45, 0), parent=troot, bevel=0.03)
bits.box("crown2", (1.4, 0.38, 1.3), dark_stone, (0.8, 0.9, 3.75), (0.15, -0.95, 0.12), parent=troot, bevel=0.03)
for x in (-1.25, 1.25):
    bits.box("trim", (0.42, 1.75, 0.08), gold_trim, (x, 0.05, 1.42), parent=troot)
bits.box("trim_back", (2.5, 0.08, 0.12), gold_trim, (0, 0.53, 3.2), parent=troot)
# braziers beside the throne
for i, side in enumerate((-1, 1)):
    at = (5.6 * side, th[1] - 1.6)
    lib.place(lib.source(P + "new/fire_bowl.gltf", emit=dict(coal_glow=((1.0, 0.3, 0.05), 2.2))), (*at, 0), 0.2)
    for k in range(3):
        a = TAU * k / 3 + i
        lib.flame((at[0] + math.cos(a) * 0.35, at[1] + math.sin(a) * 0.35, 1.85), 0.6, N, seed=400 + i * 5 + k)
    L = lib.light("POINT", (at[0], at[1] - 0.4, 2.9), (1.0, 0.48, 0.16), 650, radius=0.5, name="brazier")
    lib.flicker(L, N, 650, 0.3, seed=410 + i)
    lib.fx_marker("embers", (at[0], at[1], 2.2), count=22, spread=0.8, rise=6.0)
    lib.fx_marker("smoke", (at[0], at[1], 2.6), rate=0.6, width=1.0, height=6.0, color=(0.3, 0.3, 0.32))
src = lambda name, sub="new", **kw: lib.source(P + "%s/%s.gltf" % (sub, name), **kw)
for side in (-1, 1):
    lib.place(src("lectern"), (6.5 * side * 0.62, th[1] - 6.2, 0), 0.4 * -side + math.pi * 0)
    lib.place(src("candle_stand"), (3.2 * side, th[1] - 3.4, 0.64), 0.0)
    cl = lib.light("POINT", (3.2 * side, th[1] - 3.6, 2.6), (1.0, 0.65, 0.3), 70, radius=0.1, name="candle", shadow=False)
    lib.flicker(cl, N, 70, 0.2, seed=420 + side)

# --- broken pillars and rubble in the hall -----------------------------------------------------
cut_mat = court_stone
for i, (a_deg, r_, h) in enumerate([(-62, 12.5, 2.6), (-88, 13.0, None), (62, 12.5, 1.9), (90, 13.0, 3.1),
                                    (-118, 12.0, 1.3), (118, 12.0, None)]):
    a = math.radians(a_deg)
    at = (r_ * math.sin(a), r_ * math.cos(a), 0)
    root, objs = lib.real_copy(wall["column"], at, rnd.random() * TAU)
    if h is not None:
        bpy.ops.mesh.primitive_cube_add(size=4, location=(at[0], at[1], h + 2.0))
        cutter = bpy.context.active_object
        cutter.rotation_euler = (rnd.uniform(0.25, 0.45), rnd.uniform(-0.2, 0.2), rnd.random() * TAU)
        cutter.hide_render = True
        cutter.hide_viewport = True
        for o in objs:
            if o.type == "MESH":
                md = o.modifiers.new("break", "BOOLEAN")
                md.object = cutter
                md.operation = "DIFFERENCE"
                md.solver = "EXACT"
        lib.place(lib.source("assets/kaykit/dungeon/rubble_half.gltf.glb"), (at[0] + 1.2, at[1] - 0.5, 0), rnd.random() * TAU, 0.3)
# a fallen drum of a column
fallen, fobjs = lib.real_copy(wall["column"], (-10.5, 1.0, 0.72), 0.0)
fallen.rotation_euler = (math.pi / 2, 0, 0.9)
fallen.scale = (1, 1, 1)
for x, y, s_ in [(8.0, 3.5, 1.0), (-4.5, 8.5, 0.8), (6.0, -6.0, 1.1), (-11.0, 4.0, 1.0), (10.5, 9.0, 0.9)]:
    lib.place(lib.source("assets/kaykit/dungeon/rubble_large.gltf.glb"), (x, y, 0), rnd.random() * TAU, s_ * 0.3)
lib.place(src("sword_shield_broken"), (-9.0, -6.0, 0), 0.3)

# --- iron lightning rods round the seal ----------------------------------------------------------
iron = lib.flat_mat("rod_iron", (0.05, 0.05, 0.055), 0.4, 0.9)
copper = lib.flat_mat("copper", (0.45, 0.26, 0.16), 0.4, 0.8)
for k, a_deg in enumerate([45, 135, 225, 315]):
    a = math.radians(a_deg)
    at = (9.0 * math.sin(a), 9.0 * math.cos(a))
    bits.cyl("rod_foot", 0.9, 0.4, court_stone, (*at, 0.2), seg=8, r2=0.75)
    bits.cyl("rod", 0.38, 4.6, iron, (*at, 2.7), seg=4, r2=0.1)
    for i in range(3):
        bits.torus("coil", 0.36 - i * 0.03, 0.05, copper, (*at, 1.6 + i * 0.15), seg=16, rseg=6)
    for i in range(4):
        aa = TAU * i / 4
        bits.cyl("spike", 0.06, 0.7, iron, (at[0] + math.cos(aa) * 0.14, at[1] + math.sin(aa) * 0.14, 5.3), (math.sin(aa) * 0.35, -math.cos(aa) * 0.35, 0), seg=4, r2=0.0)
    lib.fx_marker("rod", (*at, 5.4))

# --- torn banners of fallen kingdoms, in the wind -------------------------------------------------
B_TINT = dict(red_cloth=(0.55, 0.42, 0.42), runner=(0.6, 0.55, 0.5))
bobjs = []
for i, a_deg in enumerate([-60, -84, 60, 84, -108, 108]):
    a = math.radians(a_deg)
    name = ["banner_thin_red", "banner_patternA_red", "banner_shield_red"][i % 3]
    root, objs = lib.real_copy(lib.source(P + "new/%s.gltf" % name, mat_tint=B_TINT), ((R - 1.4) * math.sin(a), (R - 1.4) * math.cos(a), 0.2), -a)
    root.scale = (1.2, 1.2, 1.4)
    bobjs += objs
lib.cloth_wave(bobjs, {"red_cloth", "runner"}, N, strength=0.35, size=0.6, radius=1.2, seed=1)

# --- light: the storm's cold light, the flashes ----------------------------------------------------
lib.light("SUN", (0, 0, 20), (0.55, 0.65, 1.0), 0.55, rot=(math.radians(55), 0, math.radians(170)), name="moon", shadow=True)
storm = lib.light("SUN", (0, 0, 20), (0.62, 0.74, 1.0), 0.0, rot=(math.radians(50), math.radians(10), math.radians(160)), name="storm")
lib.key_series(storm.data, "energy", [0.0 + 7.0 * v for v in flash])
fill = lib.light("POINT", (0, -6, 9), (0.45, 0.55, 0.85), 1500, radius=4, name="fill", shadow=False)

# --- camera ---------------------------------------------------------------------------------------
centre = (0.0, 5.0, 0.0)
el = math.radians(float(os.environ.get("ELEV", "38")))
dist = float(os.environ.get("DIST", "40"))
path = lib.gentle_path(centre, el, dist, -24, (centre[0], centre[1] + 0.4, 1.5))
cam = lib.camera((0, -30, 30), centre, lens=float(os.environ.get("LENS", "35")))
lib.cyclic_camera(cam, N, path)

os.makedirs(OUT, exist_ok=True)
lib.export_fx(OUT + "fx.json")
import json
json.dump(dict(flashes=FLASHES), open(OUT + "flashes.json", "w"))
lib.save(OUT + "c2.blend")
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

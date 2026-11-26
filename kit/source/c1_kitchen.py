"""C1: Behemoth's kitchens (First Circle) - iso three-quarter view, slow drift, fires, embers, smoke."""
import sys, os, math, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy
import lib, bits
from lib import TAU

W, H = [int(v) for v in os.environ.get("RES", "1280x720").split("x")]
N = int(os.environ.get("FRAMES", "192"))
SAMPLES = int(os.environ.get("SAMPLES", "8"))
OUT = os.environ.get("OUT", "/tmp/c1/")

lib.reset()
sc = lib.setup_render(W, H, N, SAMPLES, exposure=float(os.environ.get("EXPOSURE", "0.0")))
lib.flame_mat(strength=5.0)  # C1 was graded with the brighter flames (the shared default is now 3.2)
lib.world((0.006, 0.007, 0.012), 1.0, vol_density=float(os.environ.get("VOL","0")), vol_color=(0.8,0.7,0.6))
rnd = random.Random(7)
P = "assets/props/"

# --- floor: the kitchen's checker tiles, with the dirt worked in near the walls ---------------
floor_mat = lib.ground_surface_mat("tiles", gain=0.55, patch="dirt", patch_amount=0.45, patch_scale=4.0)
bpy.ops.mesh.primitive_plane_add(size=1, location=(0, 0, 0))
fl = bpy.context.active_object
fl.scale = (34, 26, 1)
fl.data.materials.append(floor_mat)
# the void below and around
bpy.ops.mesh.primitive_plane_add(size=200, location=(0, 0, -0.02))
void = bpy.context.active_object
void.data.materials.append(lib.flat_mat("void", (0.004, 0.003, 0.003), 1.0))

# --- walls: brick (ground.json walls.themes.kitchen), shelves variant -------------------------
brick = lib.wall_surface_mat("brick")
brick_shade = lib.wall_surface_mat("brick", shade=0.45)
flat = dict(wall=brick, shade=brick_shade, stone=lib.wall_surface_mat("stone"),
            iron=lib.flat_mat("w_iron", (0.13, 0.13, 0.14), 0.55, 0.7),
            wood=lib.flat_mat("w_wood", (0.3, 0.18, 0.1), 0.85),
            clay=lib.flat_mat("w_clay", (0.5, 0.27, 0.17), 0.8),
            cloth=lib.flat_mat("w_cloth", (0.4, 0.33, 0.24), 0.95),
            dark=lib.flat_mat("w_dark", (0.03, 0.02, 0.02), 1.0),
            gold=lib.flat_mat("w_gold", (0.6, 0.42, 0.15), 0.35, 1.0))
wall = {k: lib.source(P + "walls/%s.glb" % k, flat) for k in
        ["wall_a", "wall_b", "wall_shelves", "wall_niche", "wall_buttress", "pillar", "wall_low", "torch"]}

XN, YN = 14.0, 10.0  # inner faces at about x=-XN, y=+YN
north = ["wall_a", "wall_shelves", "wall_b", "wall_a", "wall_niche", "wall_b", "wall_shelves"]
for i, k in enumerate(north):
    lib.place(wall[k], (-XN + 2 + 4 * i, YN + 0.57, 0), 0.0)
west = ["wall_b", "wall_shelves", "wall_a", "wall_buttress", "wall_b"]
for i, k in enumerate(west):
    lib.place(wall[k], (-XN - 0.57, YN - 2 - 4 * i, 0), math.pi / 2)
lib.place(wall["pillar"], (-XN - 0.4, YN + 0.4, 0), 0)
# low walls on the near sides frame the room as the game's cut-away does
for i in range(7):
    lib.place(wall["wall_low"], (-XN + 2 + 4 * i, -YN - 4.6, 0), 0.0)
for i in range(6):
    lib.place(wall["wall_low"], (XN + 4.6, YN - 2 - 4 * i, 0), math.pi / 2)

# --- props ------------------------------------------------------------------------------------
E = dict(coal_glow=((1.0, 0.3, 0.05), 2.2), ember=((1.0, 0.35, 0.06), 3.0), glass_amber=((1.0, 0.55, 0.18), 5.0),
         wax_red=(None, 0.0))
MT = dict(forge_stone=(0.35, 0.3, 0.28), stone=(0.55, 0.5, 0.48))
src = lambda name, sub="new": lib.source(P + "%s/%s.gltf" % (sub, name), emit=E, mat_tint=MT)

# Behemoth's cauldron, its fire under it and the stew glowing in it
caul_at = (-2.5, 2.8)
lib.place(src("cauldron"), (*caul_at, 0), 0.4, 0.85)
stew = bits.cyl("stew", 1.55, 0.05, bits.stew_mat(N), (caul_at[0], caul_at[1], 3.05), seg=32)
# the coals in the fire pit glowing out from under the pot
bits.torus("coals", 1.05, 0.16, lib.flat_mat("coals", (0.05, 0.02, 0.01), 0.9, 0.0, (1.0, 0.3, 0.04), 3.0), (caul_at[0], caul_at[1], 0.12), seg=24, rseg=6)
for k in range(5):
    a = TAU * k / 5
    lib.flame((caul_at[0] + math.cos(a) * 0.9, caul_at[1] + math.sin(a) * 0.9, 0.15), 0.55, N, seed=10 + k)
fire_light = lib.light("POINT", (caul_at[0], caul_at[1], 0.7), (1.0, 0.42, 0.12), 2200, radius=0.8, name="caul_fire", shadow=False)
lib.flicker(fire_light, N, 2200, 0.28, seed=3)
stew_light = lib.light("POINT", (caul_at[0], caul_at[1], 3.6), (1.0, 0.35, 0.1), 220, radius=1.4, name="stew")
lib.flicker(stew_light, N, 220, 0.15, seed=4, fast=False)
lib.fx_marker("smoke", (caul_at[0], caul_at[1], 3.4), rate=1.0, width=2.2, height=9.0, color=(0.36, 0.33, 0.31))
lib.fx_marker("embers", (caul_at[0], caul_at[1], 0.6), count=36, spread=2.4, rise=7.0)
lib.fx_marker("steam", (caul_at[0], caul_at[1], 3.2), count=0)

# ovens: the forge model along the north wall, coals glowing
for x in (5.0, 10.0):
    lib.place(src("forge"), (x, YN - 1.0, 0), 0.0, 1.0)
    f, L = lib.flame((x, YN - 1.25, 0.75), 0.32, N, seed=int(x * 3), light_energy=260, light_up=0.5)
    L.location.y -= 0.9
    lib.fx_marker("embers", (x, YN - 1.4, 1.2), count=10, spread=0.6, rise=5.0)
    lib.fx_marker("smoke", (x, YN - 0.9, 4.9), rate=0.5, width=0.8, height=5.0, color=(0.3, 0.28, 0.27))

# braziers in the room
for i, at in enumerate([(9.5, -5.5), (-10.5, -6.5)]):
    lib.place(src("fire_bowl"), (*at, 0), 0.3)
    for k in range(3):
        a = TAU * k / 3 + i
        lib.flame((at[0] + math.cos(a) * 0.35, at[1] + math.sin(a) * 0.35, 1.85), 0.55, N, seed=40 + i * 5 + k)
    L = lib.light("POINT", (at[0], at[1], 2.9), (1.0, 0.45, 0.14), 700, radius=0.5, name="brazier")
    lib.flicker(L, N, 700, 0.3, seed=50 + i)
    lib.fx_marker("embers", (at[0], at[1], 2.2), count=22, spread=0.8, rise=6.0)
    lib.fx_marker("smoke", (at[0], at[1], 2.6), rate=0.6, width=1.0, height=6.0, color=(0.3, 0.28, 0.27))

gc_at = (-6.8, -2.6)
lib.place(src("gruel_cauldron", "third"), (*gc_at, 0), 0.7, 1.15)
for k in range(3):
    a = TAU * k / 3 + 0.4
    lib.flame((gc_at[0] + math.cos(a) * 0.45, gc_at[1] + math.sin(a) * 0.45, 0.1), 0.42, N, seed=60 + k)
L = lib.light("POINT", (gc_at[0], gc_at[1], 0.5), (1.0, 0.42, 0.12), 1100, radius=0.4, name="gruel_fire", shadow=False)
lib.flicker(L, N, 1100, 0.3, seed=61)
lib.fx_marker("embers", (gc_at[0], gc_at[1], 0.4), count=16, spread=1.0, rise=5.0)
lib.fx_marker("smoke", (gc_at[0], gc_at[1], 2.4), rate=0.7, width=1.2, height=6.0, color=(0.42, 0.4, 0.34))
for name, at, rot in [("plate_stack", (-4.6, -4.6, 0), 0.3), ("jar", (-5.0, -1.0, 0), 0.9), ("box_small", (-9.0, -0.8, 0), 0.4),
                      ("bone_heap", (-9.5, -5.0, 0), 2.1), ("barrel_small", (-3.6, -6.6, 0), 0.0)]:
    lib.place(src(name), at, rot, 0.6 if name == "bone_heap" else 1.0)

# the long table, set
tab_at = (3.5, 0.0)
lib.place(src("table_long_decorated_A"), (*tab_at, 0), math.pi / 2)
for k, name in enumerate(["plate_food_A", "plate_stack", "plate_food_B", "bottle_A_brown", "plate_food_A", "bottle_B_green"]):
    lib.place(src(name), (tab_at[0] - 1.6 + k * 0.62, tab_at[1] + rnd.uniform(-0.4, 0.4), 1.0), rnd.random() * TAU)
for k in range(3):
    for side in (-1, 1):
        lib.place(src("stool"), (tab_at[0] - 1.2 + k * 1.2, tab_at[1] + side * 1.6, 0), rnd.random() * TAU)
B = bits.mats()
lib.place(src("candle_triple"), (tab_at[0] + 0.3, tab_at[1] - 0.2, 1.0), 0.5)
for k, (dx, dy) in enumerate([(0.0, 0.0), (0.2, 0.12), (-0.18, 0.1)]):
    pass
cl = lib.light("POINT", (tab_at[0] + 0.3, tab_at[1] - 0.2, 1.8), (1.0, 0.6, 0.3), 90, radius=0.1, name="candle", shadow=False)
lib.flicker(cl, N, 90, 0.2, seed=91)
bits.cleaver("cleaver1", B["steel"], B["wood"], (tab_at[0] + 0.9, tab_at[1] + 0.2, 1.17), (0.25, 0, 0.6), s=1.3)
bits.cleaver("cleaver2", B["steel"], B["wood"], (tab_at[0] - 1.2, tab_at[1] - 0.5, 1.12), (-0.3, 0.1, 2.4), s=1.1)
# a butcher's block with a cleaver bitten into it
lib.place(src("barrel_small"), (0.5, -5.0, 0), 0.4, (1.2, 1.2, 0.95))
bits.cleaver("cleaver3", B["steel"], B["wood"], (0.55, -5.0, 1.1), (0.0, 0.55, 1.2), s=1.4)

# meat hooks: a beam on two posts along the west side, chains, hooks and joints
beam_y0, beam_y1, beam_x = -6.0, 3.0, -11.6
bits.box("beam", (0.28, beam_y1 - beam_y0 + 0.6, 0.28), B["wood"], (beam_x, (beam_y0 + beam_y1) / 2, 3.9), bevel=0.02)
for y in (beam_y0, beam_y1):
    bits.box("post", (0.26, 0.26, 3.9), B["wood"], (beam_x, y, 1.95), bevel=0.02)
hangers = []
for k in range(6):
    y = beam_y0 + 0.9 + k * (beam_y1 - beam_y0 - 1.8) / 5
    piv = bpy.data.objects.new("hanger", None)
    sc.collection.objects.link(piv)
    piv.location = (beam_x, y, 3.76)
    n_links = rnd.randint(5, 9)
    bits.chain("ch%d" % k, n_links, 0.12, B["iron"], (0, 0, 0), parent=piv)
    z = -n_links * 0.12 * 0.78 - 0.12
    bits.hook("hk%d" % k, B["iron"], (0, 0, z - 0.1), parent=piv)
    if k != 3:
        bits.meat("meat%d" % k, B["meat"], (0, 0, z - 0.55), parent=piv, seed=k,
                  size=(0.2 + rnd.random() * 0.08, 0.17, 0.4 + rnd.random() * 0.15))
    sw = lib.periodic_noise(N, 200 + k, ((1, 1.0), (2, 0.4)))
    lib.key_series(piv, "rotation_euler", [0.05 * v for v in sw], index=0)
    sw2 = lib.periodic_noise(N, 300 + k, ((1, 1.0), (3, 0.3)))
    lib.key_series(piv, "rotation_euler", [0.03 * v for v in sw2], index=1)

# along the walls: shelves, barrels, kegs, crates, bone heap, sacks
for name, at, rot in [("shelves", (-XN + 0.6, -3.0), math.pi / 2), ("keg_decorated", (-XN + 1.2, 6.8), math.pi / 2),
                      ("barrel_large", (-8.5, YN - 1.2), 0.3), ("barrel_small_stack", (-6.0, YN - 0.8), 0.0),
                      ("crates_stacked", (1.0, YN - 0.9), 0.2), ("box_small", (2.1, YN - 1.0), 0.6),
                      ("barrel_small", (12.4, YN - 1.0), 0.0), ("keg", (12.2, 6.0), math.pi),
                      ("jar", (-XN + 1.0, -5.2), 0.2), ("jar", (-XN + 0.9, -6.0), 1.2),
                      ("bone_heap", (-XN + 2.0, YN - 2.2), 0.8), ("table_medium", (12.0, 1.5), 0.1),
                      ("plate_stack", (12.0, 1.4, 1.0), 0.0), ("bottle_A_brown", (12.3, 1.9, 1.0), 0.0),
                      ("barrel_small", (-12.5, -8.0), 0.4)]:
    loc = (at[0], at[1], at[2] if len(at) > 2 else 0)
    lib.place(src(name), loc, rot)
lib.place(lib.source(P + "floor/grate.glb"), (0.5, 1.0, 0.005), 0.0)
lib.place(lib.source(P + "floor/grate.glb"), (6.0, 5.0, 0.005), 0.0)

# wall lamps (the kitchen's cage lanterns) and torches
cage = src("lamp_cage", "lamps")
for i, x in enumerate([-8.0, 2.0, 7.5]):
    lib.place(cage, (x, YN, 2.7), 0.0)
    L = lib.light("POINT", (x, YN - 0.9, 2.4), (1.0, 0.6, 0.28), 260, radius=0.15, name="cage", shadow=False)
    lib.flicker(L, N, 260, 0.12, seed=70 + i)
for i, y in enumerate([4.0, -7.0]):
    lib.place(cage, (-XN, y, 2.7), math.pi / 2)
    L = lib.light("POINT", (-XN + 0.9, y, 2.4), (1.0, 0.6, 0.28), 260, radius=0.15, name="cage", shadow=False)
    lib.flicker(L, N, 260, 0.12, seed=80 + i)

# a faint cold fill from above so the silhouettes read
lib.light("SUN", (0, 0, 20), (0.55, 0.62, 0.9), 0.06, rot=(0.5, 0.25, -0.9), name="fill", shadow=False)

# Behemoth, idle at his stove behind the cauldron
if os.environ.get("BEHEMOTH", "0") == "1":
    root, arm, meshes = lib.character(lib.REPO + "assets/characters/behemoth/behemoth.glb", (-6.4, 5.6, 0),
                                      math.radians(-60), 2.3, "Idle", N)

# --- camera: iso three-quarter from the south-east, a slow drift -------------------------------
centre = (-0.5, 3.2, 0.0)
el = math.radians(42)
dist = 31.0
path = lib.gentle_path(centre, el, dist, -38, (centre[0], centre[1] + 0.5, 0.8))
cam = lib.camera((0, -30, 30), centre, lens=float(os.environ.get("LENS", "38")))
lib.cyclic_camera(cam, N, path)

os.makedirs(OUT, exist_ok=True)
lib.export_fx(OUT + "fx.json")
lib.save(OUT + "c1.blend")
sc.render.filepath = OUT + "f_"
if os.environ.get("MODE") == "build":   # scene file only, rendered elsewhere
    raise SystemExit(0)
if os.environ.get("MODE", "still") == "still":
    for f in [int(x) for x in os.environ.get("STILLS", "0").split(",")]:
        sc.frame_set(f)
        sc.render.filepath = OUT + "still_%03d.png" % f
        bpy.ops.render.render(write_still=True)
else:
    sc.frame_start = int(os.environ.get("F0", "0"))
    sc.frame_end = int(os.environ.get("F1", str(N - 1)))
    bpy.ops.render.render(animation=True)

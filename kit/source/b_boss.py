"""B1-B3: each boss in its own arena, low angle, idle animation, slow orbit, embers (portrait 4:5)."""
import sys, os, math, random, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy
import lib, bits, bosses
from lib import TAU

BOSS = os.environ.get("BOSS", "verrier")
W, H = [int(v) for v in os.environ.get("RES", "864x1080").split("x")]
N = int(os.environ.get("FRAMES", "144"))
SAMPLES = int(os.environ.get("SAMPLES", "8"))
OUT = os.environ.get("OUT", "/tmp/b/")
HERE = os.path.dirname(os.path.abspath(__file__))
TEX = os.environ.get("TEX", os.path.join(HERE, "tex")) + "/"
P = "assets/props/"
rnd = random.Random(5)

lib.reset()
sc = lib.setup_render(W, H, N, SAMPLES, exposure=float(os.environ.get("EXPOSURE", "0.0")))


def walls_ring(surface, R, n, kinds, pillars=True, rows=1, gain=1.0, skip=(), skip_upper=()):
    """Wall pieces on a ring of radius R facing the middle: 2n+1 of them centred on +y (k = -n..n);
    `skip` leaves out pieces by k (a window's place), `skip_upper` only their upper course."""
    mat = lib.wall_surface_mat(surface, gain=gain)
    flat = dict(wall=mat, shade=lib.wall_surface_mat(surface, shade=0.45, gain=gain), stone=lib.wall_surface_mat("stone"),
                iron=lib.flat_mat("w_iron", (0.13, 0.13, 0.14), 0.55, 0.7), wood=lib.flat_mat("w_wood", (0.3, 0.18, 0.1), 0.85),
                clay=lib.flat_mat("w_clay", (0.5, 0.27, 0.17), 0.8), cloth=lib.flat_mat("w_cloth", (0.4, 0.33, 0.24), 0.95),
                dark=lib.flat_mat("w_dark", (0.03, 0.02, 0.02), 1.0), gold=lib.flat_mat("w_gold", (0.6, 0.42, 0.15), 0.35, 1.0))
    src = {k: lib.source(P + "walls/%s.glb" % k, flat, key=surface + k) for k in set(kinds) | {"pillar", "wall_a"}}
    step = math.degrees(2 * math.asin(2.0 / R))
    for k in range(-n, n + 1):
        ar = math.radians(k * step)
        if k not in skip:
            for row in range(rows):
                if row > 0 and k in skip_upper:
                    continue
                lib.place(src[kinds[(k + n) % len(kinds)] if row == 0 else "wall_a"],
                          ((R + 0.57) * math.sin(ar), (R + 0.57) * math.cos(ar), row * 4.4), -ar)
        if pillars and k < n and not (k in skip and k + 1 in skip):
            aj = math.radians((k + 0.5) * step)
            lib.place(src["pillar"], ((R - 0.2) * math.sin(aj), (R - 0.2) * math.cos(aj), 0), -aj)
    return src


def floor(mat, size=60):
    bpy.ops.mesh.primitive_plane_add(size=size, location=(0, 0, 0))
    o = bpy.context.active_object
    o.data.materials.append(mat)
    return o


def cam_orbit(target, dist, height, az0=0.0, swing=8.0, lens=40, push=0.6, look_z=None, bob=0.15):
    cam = lib.camera((0, -dist, height), target, lens=lens)
    if os.environ.get("CALM", "1") == "1":   # an almost static camera: a slight breathing push-in and drift
        swing, push, bob = 0.8, 0.15, 0.0
    def path(th):
        az = math.radians(az0 + swing * math.sin(th))
        d = dist - push * (0.5 - 0.5 * math.cos(th))
        loc = (target[0] + d * math.sin(az), target[1] - d * math.cos(az), height + bob * math.sin(2 * th))
        return loc, (target[0], target[1], look_z if look_z is not None else target[2])
    lib.cyclic_camera(cam, N, path)
    return cam


preset = "boss"
extra = {}

if BOSS == "behemoth":
    lib.world((0.004, 0.003, 0.003), 1.0, vol_density=0.0025, vol_color=(0.9, 0.75, 0.6))
    sc.eevee.volumetric_tile_size = "2"
    floor(lib.ground_surface_mat("tiles", gain=0.5, patch="dirt", patch_amount=0.5, patch_scale=3.0))
    walls_ring("brick", 9.0, 3, ["wall_a", "wall_shelves", "wall_b", "wall_niche"])
    E = dict(coal_glow=((1.0, 0.3, 0.05), 2.2), ember=((1.0, 0.35, 0.06), 3.0))
    MT = dict(forge_stone=(0.35, 0.3, 0.28), stone=(0.55, 0.5, 0.48))
    src = lambda name, sub="new": lib.source(P + "%s/%s.gltf" % (sub, name), emit=E, mat_tint=MT)
    # the great cauldron behind him, its fire and stew
    ca = (-3.6, 5.2)
    lib.place(src("cauldron"), (*ca, 0), 0.5, 0.75)
    bits.cyl("stew", 1.35, 0.05, bits.stew_mat(N), (ca[0], ca[1], 2.68), seg=32)
    for k in range(5):
        a = TAU * k / 5
        lib.flame((ca[0] + math.cos(a) * 0.8, ca[1] + math.sin(a) * 0.8, 0.12), 0.5, N, seed=10 + k)
    L = lib.light("POINT", (ca[0], ca[1], 0.6), (1.0, 0.42, 0.12), 1800, radius=0.8, name="caul_fire", shadow=False)
    lib.flicker(L, N, 1800, 0.25, seed=3)
    lib.fx_marker("smoke", (ca[0], ca[1], 3.0), rate=0.9, width=1.8, height=7.0, color=(0.36, 0.33, 0.31))
    lib.fx_marker("embers", (ca[0], ca[1], 0.5), count=40, spread=2.0, rise=6.0)
    lib.place(src("forge"), (4.2, 6.6, 0), -0.5)
    f, L = lib.flame((4.0, 6.3, 0.75), 0.32, N, seed=21, light_energy=300, light_up=0.5)
    for i, at in enumerate([(-3.9, 3.6), (4.0, 3.2)]):
        lib.place(src("fire_bowl"), (*at, 0), 0.3)
        for k in range(3):
            a = TAU * k / 3 + i
            lib.flame((at[0] + math.cos(a) * 0.35, at[1] + math.sin(a) * 0.35, 1.85), 0.6, N, seed=40 + i * 5 + k)
        L = lib.light("POINT", (at[0], at[1], 2.8), (1.0, 0.45, 0.14), 650, radius=0.5, name="brazier")
        lib.flicker(L, N, 650, 0.3, seed=50 + i)
        lib.fx_marker("embers", (at[0], at[1], 2.2), count=26, spread=0.7, rise=5.0)
        lib.fx_marker("smoke", (at[0], at[1], 2.5), rate=0.5, width=0.8, height=5.0, color=(0.3, 0.28, 0.27))
    B = bits.mats()
    for k in range(5):
        x = -4.5 + k * 2.2
        y = 7.5 + rnd.uniform(-0.6, 0.6)
        piv = bpy.data.objects.new("hanger", None)
        sc.collection.objects.link(piv)
        piv.location = (x, y, 5.2)
        bits.chain("ch%d" % k, 7, 0.12, B["iron"], (0, 0, 0), parent=piv)
        bits.hook("hk%d" % k, B["iron"], (0, 0, -0.85), parent=piv)
        bits.meat("meat%d" % k, B["meat"], (0, 0, -1.4), parent=piv, seed=k)
        lib.key_series(piv, "rotation_euler", [0.05 * math.sin(TAU * f / N + k) for f in range(N)], index=0)
    for name, at, rot in [("barrel_large", (-6.5, 3.0), 0.3), ("keg", (6.5, 3.5), -0.6), ("bone_heap", (5.5, -0.5), 0.8),
                          ("table_long_decorated_A", (-6.0, -0.5), 1.2)]:
        lib.place(src(name), (*at, 0), rot, 0.7 if name == "bone_heap" else 1.0)
    SHOW = os.environ.get("BEHEMOTH_BLEND", "")
    if SHOW:   # the re-rigged Behemoth (machete and lantern skinned to his hands)
        root, arm, hgt, glow = bosses.behemoth_showcase(SHOW, (0, 0, 0), math.radians(float(os.environ.get("YAW", "8"))), 2.0, N)
    else:
        root, arm, hgt, glow = bosses.behemoth((0, 0, 0), math.radians(8), 2.0, N, os.environ.get("ACTION", "Idle"))
    # the lantern: glowing glass and its light
    Lg = lib.light("POINT", (0, 0, 0), (1.0, 0.6, 0.25), 55, radius=0.08, name="lantern", shadow=False)
    Lg.parent = glow
    lib.flicker(Lg, N, 55, 0.15, seed=77)
    # rim lights from the fires behind
    rim = lib.light("SPOT", (-1.5, 4.5, 4.5), (1.0, 0.45, 0.15), 3000, radius=1.0, name="rim", spot=math.radians(50))
    lib.aim(rim, (0, 0, 2.0))
    lib.flicker(rim, N, 3000, 0.2, seed=78)
    key = lib.light("SPOT", (2.5, -5.0, 1.0), (1.0, 0.55, 0.25), 1200, radius=1.0, name="key", spot=math.radians(40))
    lib.aim(key, (0, 0, 2.5))
    lib.flicker(key, N, 1200, 0.15, seed=79)
    fill = lib.light("POINT", (-3, -5, 3), (0.5, 0.55, 0.8), 120, radius=2, name="fill", shadow=False)
    lib.fx_marker("embers", (0, 0.5, 0.2), count=30, spread=2.5, rise=6.0)
    if SHOW:   # a near-still camera: a small push-in and a two-degree drift
        cam = cam_orbit((0, 0, 1.9), float(os.environ.get("CDIST", "7.6")), float(os.environ.get("CH", "0.8")),
                        az0=float(os.environ.get("AZ0", "6")), swing=2.0, lens=40, push=0.18, bob=0.0,
                        look_z=float(os.environ.get("LOOKZ", "1.95")))
    else:
        cam = cam_orbit((0, 0, 1.9), 7.6, 0.8, az0=6, swing=9, lens=40, push=0.5, look_z=1.95)

elif BOSS == "verrier":
    lib.world((0.004, 0.006, 0.012), 1.0, vol_density=0.005, vol_color=(0.6, 0.7, 0.9))
    sc.eevee.volumetric_tile_size = "2"
    floor(lib.ground_surface_mat("shrine", gain=0.6, patch="cracked", patch_amount=0.3, patch_scale=5.0, wet=0.4))
    temple = lib.wall_surface_mat("temple", gain=0.95)
    stone_m = lib.wall_surface_mat("stone")
    walls_ring("temple", 9.0, 3, ["wall_a", "wall_buttress", "wall_niche", "wall_b"], skip=(0,))
    FL = [(30, 1.0), (35, 0.6), (100, 0.85), (104, 0.5)]
    flash = lib.flash_values(N, FL)
    extra["flashes"] = FL
    # a tall broken window right behind him, the storm in it
    court_stone = lib.flat_mat("court_stone", (0.26, 0.24, 0.27), 0.85)
    for wx, scl in [(0.0, 1.0)]:
        root_w = bpy.data.objects.new("window", None)
        sc.collection.objects.link(root_w)
        root_w.location = (wx, 9.4, 0)
        for (x, y, z, sx, sy, sz, r_) in [(-2.0, 0, 4.0, 1.0, 1.0, 8.0, 0), (2.0, 0, 4.0, 1.0, 1.0, 8.0, 0),
                                          (0, 0, 0.55, 5.0, 1.15, 1.1, 0), (0.3, -0.1, 4.6, 0.18, 0.18, 4.2, 0.45)]:
            bits.box("winpart", (sx, sy, sz), stone_m if sx > 0.5 else court_stone, (x, y, z), (0, r_, 0), parent=root_w, bevel=0.03)
        for side in (-1, 1):
            bits.box("arch", (2.4, 1.0, 0.5), stone_m, (side * 0.95, 0, 8.4), (0, side * 0.55, 0), parent=root_w, bevel=0.03)
        sky = bits.box("sky", (3.2, 0.05, 8.4), None, (0, 0.35, 4.6), parent=root_w)
        skm = bpy.data.materials.new("storm_sky")
        snt = skm.node_tree if skm.use_nodes else (setattr(skm, "use_nodes", True) or skm.node_tree)
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
        lib.key_series(se.inputs[1], "default_value", [0.8 + 14.0 * v for v in flash])
        sky.data.materials.append(skm)
        sky.visible_shadow = False
    back = lib.light("AREA", (0, 9.0, 4.5), (0.6, 0.72, 1.0), 0, name="win_light", size=3.0)
    back.rotation_euler = (math.radians(-90 - 15), 0, 0)
    back.data.shape = "RECTANGLE"
    back.data.size = 3.0
    back.data.size_y = 8.0
    lib.key_series(back.data, "energy", [150 + 6000 * v for v in flash])
    storm = lib.light("SUN", (0, 0, 20), (0.62, 0.74, 1.0), 0.0, rot=(math.radians(60), 0, math.radians(180)), name="storm")
    lib.key_series(storm.data, "energy", [0.05 + 3.0 * v for v in flash])
    # the seal under his feet, glowing gold
    bpy.ops.mesh.primitive_plane_add(size=9.0, location=(0, 0, 0.012))
    seal = bpy.context.active_object
    sm = bpy.data.materials.new("seal")
    nt = sm.node_tree if sm.use_nodes else (setattr(sm, "use_nodes", True) or sm.node_tree)
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    Nn, Ln = nt.nodes, nt.links.new
    out = Nn.new("ShaderNodeOutputMaterial")
    tc = Nn.new("ShaderNodeTexCoord")
    it = Nn.new("ShaderNodeTexImage")
    it.image = lib.img(TEX + "seal.png", "Non-Color")
    Ln(tc.outputs["UV"], it.inputs[0])
    pm = Nn.new("ShaderNodeMath"); pm.operation = "MULTIPLY"
    Ln(it.outputs["Color"], pm.inputs[0])
    lib.key_series(pm.inputs[1], "default_value", [1.6 + 0.6 * math.sin(TAU * 2 * f / N) for f in range(N)])
    b = Nn.new("ShaderNodeBsdfPrincipled")
    b.inputs["Base Color"].default_value = (0.55, 0.38, 0.12, 1)
    b.inputs["Metallic"].default_value = 1.0
    b.inputs["Roughness"].default_value = 0.35
    b.inputs["Emission Color"].default_value = (1.0, 0.62, 0.18, 1)
    Ln(pm.outputs[0], b.inputs["Emission Strength"])
    tr = Nn.new("ShaderNodeBsdfTransparent")
    mx = Nn.new("ShaderNodeMixShader")
    Ln(it.outputs["Color"], mx.inputs[0]); Ln(tr.outputs[0], mx.inputs[1]); Ln(b.outputs[0], mx.inputs[2])
    Ln(mx.outputs[0], out.inputs[0])
    sm.surface_render_method = "DITHERED"
    seal.data.materials.append(sm)
    seal.visible_shadow = False
    up = lib.light("POINT", (0, -0.8, 0.4), (1.0, 0.62, 0.22), 260, radius=1.5, name="seal_up", shadow=False)
    lib.key_series(up.data, "energy", [260 * (1.6 + 0.6 * math.sin(TAU * 2 * f / N)) / 1.6 for f in range(N)])
    for i, side in enumerate((-1, 1)):
        at = (4.6 * side, 5.0)
        lib.place(lib.source(P + "new/fire_bowl.gltf", emit=dict(coal_glow=((1.0, 0.3, 0.05), 2.2))), (*at, 0), 0.2)
        for k in range(3):
            a = TAU * k / 3 + i
            lib.flame((at[0] + math.cos(a) * 0.35, at[1] + math.sin(a) * 0.35, 1.85), 0.6, N, seed=400 + i * 5 + k)
        L = lib.light("POINT", (at[0], at[1] - 0.4, 2.8), (1.0, 0.48, 0.16), 500, radius=0.5, name="brazier")
        lib.flicker(L, N, 500, 0.3, seed=410 + i)
        lib.fx_marker("embers", (at[0], at[1], 2.2), count=24, spread=0.7, rise=5.0)
        lib.fx_marker("smoke", (at[0], at[1], 2.5), rate=0.5, width=0.8, height=5.0, color=(0.3, 0.3, 0.33))
    B_TINT = dict(red_cloth=(0.55, 0.42, 0.42), runner=(0.6, 0.55, 0.5))
    bobjs = []
    for i, a_deg in enumerate([-38, 38]):
        a = math.radians(a_deg)
        rr, objs = lib.real_copy(lib.source(P + "new/banner_patternA_red.gltf", mat_tint=B_TINT), (8.4 * math.sin(a), 8.4 * math.cos(a), 0.2), -a)
        rr.scale = (1.3, 1.3, 1.5)
        bobjs += objs
    lib.cloth_wave(bobjs, {"red_cloth", "runner"}, N, strength=0.3, size=0.6, radius=1.2, seed=2)
    root, arm, hgt = bosses.verrier((0, 0, 0), 0.0, 1.55, N, os.environ.get("ACTION", "2H_Melee_Idle"), wings_open=0.3)
    rim = lib.light("SPOT", (0.5, 4.0, 5.5), (0.6, 0.72, 1.0), 2600, radius=0.6, name="rim", spot=math.radians(45))
    lib.aim(rim, (0, 0, 2.2))
    key = lib.light("SPOT", (-3.0, -4.5, 2.0), (1.0, 0.72, 0.42), 420, radius=1.0, name="key", spot=math.radians(40))
    lib.aim(key, (0, 0, 2.5))
    fill = lib.light("POINT", (3, -5, 3), (0.45, 0.55, 0.85), 70, radius=2, name="fill", shadow=False)
    lib.fx_marker("embers", (0, 0.5, 0.2), count=10, spread=2.5, rise=5.0)
    preset = "boss_storm"
    cam = cam_orbit((0, 0, 2.0), 8.2, 0.8, az0=-6, swing=9, lens=34, push=0.6, look_z=2.15)

elif BOSS == "luvart":
    lib.world((0.006, 0.012, 0.014), 1.0, vol_density=0.012, vol_color=(0.75, 0.9, 0.9), anisotropy=0.5)
    ee = sc.eevee
    ee.use_raytracing = True
    try:
        ee.ray_tracing_method = "SCREEN"
        ee.ray_tracing_options.resolution_scale = "2"
    except Exception as ex:
        print(ex)
    ee.volumetric_tile_size = "2"
    floor(lib.ground_surface_mat("vault_wet", gain=0.4))
    WL = 0.2
    bpy.ops.mesh.primitive_plane_add(size=60, location=(0, 0, WL))
    water = bpy.context.active_object
    wm = bpy.data.materials.new("water")
    nt = wm.node_tree if wm.use_nodes else (setattr(wm, "use_nodes", True) or wm.node_tree)
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    Nn, Ln = nt.nodes, nt.links.new
    out = Nn.new("ShaderNodeOutputMaterial")
    geo = Nn.new("ShaderNodeNewGeometry")
    r1 = lib.ripple_bump(nt, geo.outputs["Position"], N, scale=1.3, cycles=3, width=0.04, seed=0.0)
    r2 = lib.ripple_bump(nt, geo.outputs["Position"], N, scale=2.0, cycles=4, width=0.035, seed=3.3)
    add = Nn.new("ShaderNodeMath"); add.operation = "ADD"
    Ln(r1, add.inputs[0]); Ln(r2, add.inputs[1])
    bump = Nn.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.3
    bump.inputs["Distance"].default_value = 0.02
    Ln(add.outputs[0], bump.inputs["Height"])
    b = Nn.new("ShaderNodeBsdfPrincipled")
    b.inputs["Base Color"].default_value = (0.004, 0.009, 0.010, 1)
    b.inputs["Roughness"].default_value = 0.03
    b.inputs["Specular IOR Level"].default_value = 1.0
    b.inputs["IOR"].default_value = 2.4
    Ln(bump.outputs[0], b.inputs["Normal"])
    Ln(b.outputs[0], out.inputs[0])
    water.data.materials.append(wm)
    walls_ring("crumbling_wet", 10.0, 3, ["wall_a", "wall_niche", "wall_b", "wall_broken"], rows=2, gain=0.75,
               skip_upper=(-1, 0, 1))
    GLASS = dict(glass_amber=((1.0, 0.6, 0.2), 1.0), glass_azure=((0.25, 0.5, 1.0), 1.0), glass_rose=((1.0, 0.3, 0.35), 1.0))
    ch = lambda name: lib.source(P + "chapel/%s.gltf" % name, emit=GLASS)
    lib.place(ch("rose_window"), (0, 10.3, 0.4), 0.0, 1.0)
    for (x, y) in [(-5.5, 6.0), (5.5, 6.0)]:
        lib.place(ch("pillar"), (x, y, 0), 0.0)
    lib.place(ch("altar"), (0, 7.4, 0), 0.0, 0.9)
    bits.candles((-1.5, 7.4), 6, 0.4, N, seed=1, base_z=1.2, light=100, hmax=0.4)
    bits.candles((1.5, 7.4), 6, 0.4, N, seed=2, base_z=1.2, light=100, hmax=0.4)
    for i, (x, y) in enumerate([(-3.4, 1.4), (3.2, 2.0), (-2.2, -1.6), (2.6, -1.2), (-5.0, 4.5), (5.0, 4.2)]):
        bits.candles((x, y), rnd.randint(8, 13), 0.6, N, seed=10 + i, base_z=WL, light=90, hmax=0.6)
    iron = lib.flat_mat("chain_iron", (0.05, 0.05, 0.05), 0.4, 0.9)
    censer = lib.source(P + "luvart/censer.glb")
    for i, (x, y, drop) in enumerate([(-3.2, 3.5, 4.3), (3.6, 4.5, 4.8)]):
        piv = bpy.data.objects.new("censer_pivot", None)
        sc.collection.objects.link(piv)
        piv.location = (x, y, 9.5)
        bits.chain("cch%d" % i, int(drop / 0.125), 0.16, iron, (0, 0, 0), parent=piv, thick=0.022)
        c = lib.place(censer, (0, 0, -drop - 0.45), rnd.random() * TAU, 0.8)
        c.parent = piv
        amp = math.radians(5.0 + 2 * i)
        lib.key_series(piv, "rotation_euler", [amp * math.sin(TAU * f / N + i) for f in range(N)], index=0)
        lib.fx_marker("smoke", (x, y, 9.5 - drop - 0.2), rate=0.4, width=0.4, height=3.5, color=(0.55, 0.6, 0.6))
    root, arm, hgt = bosses.luvart((0, 0, WL), 0.0, 1.6, N, os.environ.get("ACTION", "Scythe_Idle"), wings_open=0.8)
    # Madeleine floating at his side, a little behind
    mroot, marm, mh = bosses.madeleine((-3.5, 0.9, 1.4), math.radians(22), 1.15, N, "Nun_Idle")
    lib.key_series(mroot, "location", [1.4 + 0.18 * math.sin(TAU * 2 * f / N) for f in range(N)], index=2)
    ml = lib.light("POINT", (-3.0, 0.0, 2.6), (0.75, 0.95, 0.95), 120, radius=0.5, name="madeleine_glow", shadow=False, spec=0.0)
    rim = lib.light("SPOT", (0.0, 6.0, 7.5), (0.7, 0.95, 0.95), 4200, radius=1.0, name="rim", spot=math.radians(40))
    lib.aim(rim, (0, 0, 2.4))
    key = lib.light("SPOT", (3.0, -5.0, 2.5), (1.0, 0.82, 0.6), 650, radius=1.0, name="key", spot=math.radians(40), spec=0.3)
    lib.aim(key, (0, 0, 2.6))
    halo_l = lib.light("POINT", (0, 0.5, 4.4), (1.0, 0.85, 0.5), 120, radius=0.3, name="halo_light", shadow=False, spec=0.0)
    shaft = lib.light("SPOT", (0.5, 1.0, 16), (0.62, 0.92, 0.9), 6000, radius=1.5, name="shaft", spot=math.radians(22), spec=0.4)
    fill = lib.light("POINT", (-3, -6, 3), (0.4, 0.62, 0.62), 160, radius=2, name="fill", shadow=False, spec=0.0)
    lib.fx_marker("embers", (0, 0.5, 0.4), count=0, spread=2.5, rise=5.0)
    preset = "boss_rain"
    cam = cam_orbit((0, 0, 2.6), 9.0, 0.9, az0=5, swing=8, lens=32, push=0.6, look_z=2.7)

os.makedirs(OUT, exist_ok=True)
lib.export_fx(OUT + "fx.json")
json.dump(dict(preset=preset, **extra), open(OUT + "meta.json", "w"))
lib.save(OUT + "b.blend")
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

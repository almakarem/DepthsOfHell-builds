"""Shared helpers for the Depths of Hell site background videos.

Builds scenes from the game's own assets (assets/props/**, assets/walls,
assets/ground, assets/characters) in Blender (pip bpy, EEVEE), with seamless
loops: every animated value is a periodic function of the frame with a whole
number of cycles over the loop length.
"""
import bpy, math, os, random, json
import mathutils
from mathutils import Vector, Matrix, Euler

REPO = os.environ.get("DOH_REPO", "/home/user/depthsofhell") + "/"
TAU = math.tau


# --- scene -------------------------------------------------------------------------------

def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    return sc


def setup_render(w, h, frames, samples=8, fps=24, volumetrics=False, exposure=0.0, look="AgX - Base Contrast"):
    sc = bpy.context.scene
    try:
        sc.render.engine = "BLENDER_EEVEE"
    except TypeError:   # Blender 4.2-4.x call it EEVEE Next
        sc.render.engine = "BLENDER_EEVEE_NEXT"
    sc.render.resolution_x = w
    sc.render.resolution_y = h
    sc.render.resolution_percentage = 100
    sc.render.fps = fps
    sc.frame_start = 0
    sc.frame_end = frames - 1
    ee = sc.eevee
    for k, v in dict(taa_render_samples=samples, use_shadows=True, shadow_ray_count=1, shadow_step_count=4,
                     use_raytracing=False, volumetric_tile_size="8", volumetric_samples=32,
                     use_volumetric_shadows=False, shadow_resolution_scale=0.5,
                     fast_gi_method="GLOBAL_ILLUMINATION", use_fast_gi=False,
                     clamp_surface_indirect=10.0).items():
        try:
            setattr(ee, k, v)
        except Exception as ex:
            print("eevee setting skipped", k, ex)
    sc.view_settings.view_transform = "AgX"
    try:
        sc.view_settings.look = look
    except Exception as ex:
        print("look skipped", ex)
    sc.view_settings.exposure = exposure
    sc.render.film_transparent = False
    sc.render.image_settings.file_format = "PNG"
    sc.render.image_settings.color_depth = "8"
    sc.render.image_settings.compression = 15
    sc.render.use_motion_blur = False
    return sc


def world(color=(0.0, 0.0, 0.0), strength=1.0, vol_density=0.0, vol_color=(0.5, 0.5, 0.5), anisotropy=0.3):
    sc = bpy.context.scene
    w = bpy.data.worlds.new("World")
    sc.world = w
    w.use_nodes = True
    nt = w.node_tree
    bg = nt.nodes.get("Background")
    bg.inputs[0].default_value = (*color, 1)
    bg.inputs[1].default_value = strength
    if vol_density > 0:
        out = nt.nodes.get("World Output")
        vs = nt.nodes.new("ShaderNodeVolumePrincipled")
        vs.inputs["Density"].default_value = vol_density
        vs.inputs["Color"].default_value = (*vol_color, 1)
        vs.inputs["Anisotropy"].default_value = anisotropy
        nt.links.new(vs.outputs[0], out.inputs["Volume"])
    return w


# --- coordinates (Godot y-up -> Blender z-up) ----------------------------------------------

C = Matrix(((1, 0, 0, 0), (0, 0, -1, 0), (0, 1, 0, 0), (0, 0, 0, 1)))  # godot -> blender
CI = C.inverted()


def g2b(v):
    return Vector((v[0], -v[2], v[1]))


def godot_xform(pos=(0, 0, 0), rot_deg=(0, 0, 0), scale=(1, 1, 1)):
    """A Godot Transform3D (rotation_degrees in Godot's YXZ order) as a Blender matrix."""
    rx, ry, rz = [math.radians(a) for a in rot_deg]
    R = Matrix.Rotation(ry, 4, "Y") @ Matrix.Rotation(rx, 4, "X") @ Matrix.Rotation(rz, 4, "Z")
    S = Matrix.Diagonal((*scale, 1)) if not isinstance(scale, (int, float)) else Matrix.Diagonal((scale, scale, scale, 1))
    M = Matrix.Translation(Vector(pos)) @ R @ S
    return C @ M @ CI


# --- materials ------------------------------------------------------------------------------

_img_cache = {}


def img(path, colorspace="sRGB"):
    key = (path, colorspace)
    if key in _img_cache:
        return _img_cache[key]
    im = bpy.data.images.load(path, check_existing=True)
    im.colorspace_settings.name = colorspace
    _img_cache[key] = im
    return im


def _nodes(mat):
    mat.use_nodes = True
    nt = mat.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    return nt, out


def flat_mat(name, color, rough=0.8, metal=0.0, emit=None, emit_strength=0.0):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    nt, out = _nodes(m)
    b = nt.nodes.new("ShaderNodeBsdfPrincipled")
    b.inputs["Base Color"].default_value = (*color, 1)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    if emit:
        b.inputs["Emission Color"].default_value = (*emit, 1)
        b.inputs["Emission Strength"].default_value = emit_strength
    nt.links.new(b.outputs[0], out.inputs[0])
    return m


def emit_mat(name, color, strength):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    nt, out = _nodes(m)
    e = nt.nodes.new("ShaderNodeEmission")
    e.inputs[0].default_value = (*color, 1)
    e.inputs[1].default_value = strength
    nt.links.new(e.outputs[0], out.inputs[0])
    return m


def triplanar_mat(name, tex_dir, size=4.0, tint=(1, 1, 1), top_dir=None, top_size=2.0, top_tint=(1, 1, 1),
                  foot_dark=0.45, foot_height=1.4, shade=1.0, rough_mult=1.0, bump=0.35, gain=1.0,
                  wet=0.0, flat_top=False):
    """The game's wall shader (shaders/wall.gdshader) as Blender nodes: the painting laid on by
    world position, `size` metres a repeat, faces pointing up take `top_dir`, dark at the foot."""
    m = bpy.data.materials.new(name)
    nt, out = _nodes(m)
    N = nt.nodes
    L = nt.links.new
    geo = N.new("ShaderNodeNewGeometry")
    sep = N.new("ShaderNodeSeparateXYZ")
    L(geo.outputs["Position"], sep.inputs[0])

    def tex(d, sz, cs_srgb=True, file="albedo.png"):
        mp = N.new("ShaderNodeVectorMath")
        mp.operation = "SCALE"
        mp.inputs["Scale"].default_value = 1.0 / sz
        L(geo.outputs["Position"], mp.inputs[0])
        t = N.new("ShaderNodeTexImage")
        t.image = img(d + file, "sRGB" if cs_srgb else "Non-Color")
        t.projection = "BOX"
        t.projection_blend = 0.12
        L(mp.outputs[0], t.inputs[0])
        return t

    alb = tex(tex_dir, size)
    rha = tex(tex_dir, size, False, "rha.png")
    tintn = N.new("ShaderNodeMix")
    tintn.data_type = "RGBA"
    tintn.blend_type = "MULTIPLY"
    tintn.inputs["Factor"].default_value = 1.0
    L(alb.outputs[0], tintn.inputs["A"])
    tintn.inputs["B"].default_value = (tint[0] * gain * shade, tint[1] * gain * shade, tint[2] * gain * shade, 1)
    col = tintn.outputs["Result"]
    if top_dir:
        topt = tex(top_dir, top_size)
        tt = N.new("ShaderNodeMix")
        tt.data_type = "RGBA"
        tt.blend_type = "MULTIPLY"
        tt.inputs["Factor"].default_value = 1.0
        L(topt.outputs[0], tt.inputs["A"])
        tt.inputs["B"].default_value = (*[c * gain for c in top_tint], 1)
        nz = N.new("ShaderNodeSeparateXYZ")
        L(geo.outputs["Normal"], nz.inputs[0])
        stp = N.new("ShaderNodeMath")
        stp.operation = "GREATER_THAN"
        stp.inputs[1].default_value = 0.7
        L(nz.outputs[2], stp.inputs[0])
        mx = N.new("ShaderNodeMix")
        mx.data_type = "RGBA"
        L(stp.outputs[0], mx.inputs["Factor"])
        L(col, mx.inputs["A"])
        L(tt.outputs["Result"], mx.inputs["B"])
        col = mx.outputs["Result"]
    # dark at the foot
    if foot_dark > 0:
        mr = N.new("ShaderNodeMapRange")
        mr.interpolation_type = "SMOOTHSTEP"
        mr.inputs["From Min"].default_value = 0.0
        mr.inputs["From Max"].default_value = foot_height
        mr.inputs["To Min"].default_value = 1.0 - foot_dark
        mr.inputs["To Max"].default_value = 1.0
        L(sep.outputs[2], mr.inputs["Value"])
        fm = N.new("ShaderNodeMix")
        fm.data_type = "RGBA"
        fm.blend_type = "MULTIPLY"
        fm.inputs["Factor"].default_value = 1.0
        L(col, fm.inputs["A"])
        cmb = N.new("ShaderNodeCombineColor")
        for i in range(3):
            L(mr.outputs[0], cmb.inputs[i])
        L(cmb.outputs[0], fm.inputs["B"])
        col = fm.outputs["Result"]
    b = N.new("ShaderNodeBsdfPrincipled")
    L(col, b.inputs["Base Color"])
    sr = N.new("ShaderNodeSeparateColor")
    L(rha.outputs[0], sr.inputs[0])
    rm = N.new("ShaderNodeMath")
    rm.operation = "MULTIPLY"
    rm.inputs[1].default_value = rough_mult * (1.0 - 0.55 * wet)
    rm.use_clamp = True
    L(sr.outputs[0], rm.inputs[0])
    L(rm.outputs[0], b.inputs["Roughness"])
    bp = N.new("ShaderNodeBump")
    bp.inputs["Strength"].default_value = bump
    bp.inputs["Distance"].default_value = 0.05
    L(sr.outputs[1], bp.inputs["Height"])
    L(bp.outputs[0], b.inputs["Normal"])
    if wet > 0:
        b.inputs["Specular IOR Level"].default_value = 0.5 + 0.4 * wet
    L(b.outputs[0], out.inputs[0])
    return m


def ground_mat(name, surface, size, tint, rough_mult=1.0, bump=0.4, gain=1.0, wet=0.0, patch=None, patch_amount=0.0,
               patch_scale=8.0):
    """A floor surface (assets/ground/<surface>) laid by world xy, `size` metres a repeat, with an
    optional second surface blended in noise patches (ground.json's patch)."""
    m = bpy.data.materials.new(name)
    nt, out = _nodes(m)
    N = nt.nodes
    L = nt.links.new
    geo = N.new("ShaderNodeNewGeometry")

    def layer(surf, sz, tnt):
        d = REPO + "assets/ground/%s/" % surf
        mp = N.new("ShaderNodeVectorMath")
        mp.operation = "SCALE"
        mp.inputs["Scale"].default_value = 1.0 / sz
        L(geo.outputs["Position"], mp.inputs[0])
        a = N.new("ShaderNodeTexImage")
        a.image = img(d + "albedo.png")
        L(mp.outputs[0], a.inputs[0])
        r = N.new("ShaderNodeTexImage")
        r.image = img(d + "rha.png", "Non-Color")
        L(mp.outputs[0], r.inputs[0])
        t = N.new("ShaderNodeMix")
        t.data_type = "RGBA"
        t.blend_type = "MULTIPLY"
        t.inputs["Factor"].default_value = 1.0
        L(a.outputs[0], t.inputs["A"])
        t.inputs["B"].default_value = (tnt[0] * gain, tnt[1] * gain, tnt[2] * gain, 1)
        return t.outputs["Result"], r.outputs[0]

    col, rha = layer(surface, size, tint)
    if patch:
        pcol, prha = layer(patch[0], patch[1], patch[2])
        nz = N.new("ShaderNodeTexNoise")
        nz.inputs["Scale"].default_value = 1.0 / patch_scale
        nz.inputs["Detail"].default_value = 4
        L(geo.outputs["Position"], nz.inputs["Vector"])
        mr = N.new("ShaderNodeMapRange")
        mr.inputs["From Min"].default_value = 0.62 - patch_amount * 0.5
        mr.inputs["From Max"].default_value = 0.68 - patch_amount * 0.5
        L(nz.outputs[0], mr.inputs["Value"])
        mx = N.new("ShaderNodeMix")
        mx.data_type = "RGBA"
        L(mr.outputs[0], mx.inputs["Factor"])
        L(col, mx.inputs["A"])
        L(pcol, mx.inputs["B"])
        col = mx.outputs["Result"]
        mx2 = N.new("ShaderNodeMix")
        mx2.data_type = "RGBA"
        L(mr.outputs[0], mx2.inputs["Factor"])
        L(rha, mx2.inputs["A"])
        L(prha, mx2.inputs["B"])
        rha = mx2.outputs["Result"]
    b = N.new("ShaderNodeBsdfPrincipled")
    L(col, b.inputs["Base Color"])
    sr = N.new("ShaderNodeSeparateColor")
    L(rha, sr.inputs[0])
    rm = N.new("ShaderNodeMath")
    rm.operation = "MULTIPLY"
    rm.inputs[1].default_value = rough_mult * (1.0 - 0.6 * wet)
    rm.use_clamp = True
    L(sr.outputs[0], rm.inputs[0])
    L(rm.outputs[0], b.inputs["Roughness"])
    bp = N.new("ShaderNodeBump")
    bp.inputs["Strength"].default_value = bump
    bp.inputs["Distance"].default_value = 0.04
    L(sr.outputs[1], bp.inputs["Height"])
    L(bp.outputs[0], b.inputs["Normal"])
    L(b.outputs[0], out.inputs[0])
    return m


def wall_surface_mat(surface, shade=1.0, gain=1.0):
    """The material for a ground.json walls surface (e.g. 'brick', 'temple', 'crumbling_wet')."""
    g = json.load(open(REPO + "data/ground.json"))
    W = g["walls"]
    s = W["surfaces"][surface]
    d = REPO + s["dir"].replace("res://", "")
    top = W["surfaces"][W.get("top", "stone")]
    return triplanar_mat("wall_%s_%s" % (surface, shade), d, s.get("size", 4.0), s.get("tint", [1, 1, 1]),
                         top_dir=REPO + top["dir"].replace("res://", ""), top_size=top.get("size", 2.0),
                         top_tint=top.get("tint", [1, 1, 1]), shade=shade, gain=gain,
                         rough_mult=s.get("roughness", 1.0))


def ground_surface_mat(surface, gain=1.0, patch=None, patch_amount=0.0, patch_scale=8.0, wet=0.0):
    g = json.load(open(REPO + "data/ground.json"))
    S = g["surfaces"]
    s = S[surface]
    base = s["albedo"].split("/")[-2]
    p = None
    if patch:
        ps = S[patch]
        p = (ps["albedo"].split("/")[-2], ps.get("size", 6.0), ps.get("tint", [1, 1, 1]))
    return ground_mat("ground_" + surface, base, s.get("size", 6.0), s.get("tint", [1, 1, 1]),
                      rough_mult=s.get("roughness", 1.0), gain=gain, patch=p, patch_amount=patch_amount,
                      patch_scale=patch_scale, wet=wet)


# --- assets ---------------------------------------------------------------------------------

_sources = {}


def _hidden_collection(name):
    col = bpy.data.collections.get(name)
    if col is None:
        col = bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(col)
        lc = bpy.context.view_layer.layer_collection.children[name]
        lc.exclude = True
    return col


def import_file(path, **kw):
    path = path if path.startswith("/") else REPO + path
    before = set(bpy.data.objects)
    if path.endswith(".fbx"):
        bpy.ops.import_scene.fbx(filepath=path)
    else:
        bpy.ops.import_scene.gltf(filepath=path, **kw)
    return [o for o in bpy.data.objects if o not in before]


def source(path, mat_map=None, key=None, emit=None, tint=None, mat_tint=None):
    """Imports `path` once into a hidden collection and returns that collection, for instancing.
    mat_map: material name -> bpy material to swap in. emit: material name -> (color, strength)
    to make glow (coals, embers, flames)."""
    key = key or path
    if key in _sources:
        return _sources[key]
    col = bpy.data.collections.new("src_" + os.path.basename(key))
    _hidden_collection("SOURCES").children.link(col)
    objs = import_file(path)
    for o in objs:
        for c in o.users_collection:
            c.objects.unlink(o)
        col.objects.link(o)
        if o.type == "MESH":
            if o.name.startswith("Icosphere"):
                o.hide_render = True
            for slot in o.material_slots:
                if slot.material is None:
                    continue
                base = slot.material.name.split(".")[0]
                if mat_map and base in mat_map:
                    slot.material = mat_map[base]
                elif emit and base in emit:
                    _add_emission(slot.material, *emit[base])
                elif mat_tint and base in mat_tint:
                    _tint(slot.material, mat_tint[base])
                elif tint:
                    _tint(slot.material, tint)
    _sources[key] = col
    return col


def _bsdf(mat):
    if not mat.use_nodes:
        return None
    for n in mat.node_tree.nodes:
        if n.type == "BSDF_PRINCIPLED":
            return n
    return None


def _add_emission(mat, color, strength):
    b = _bsdf(mat)
    if b is None:
        return
    nt = mat.node_tree
    bc = b.inputs["Base Color"]
    if bc.is_linked and color is None:
        nt.links.new(bc.links[0].from_socket, b.inputs["Emission Color"])
    else:
        b.inputs["Emission Color"].default_value = (*(color or (1, 0.4, 0.1)), 1)
    b.inputs["Emission Strength"].default_value = strength


def _tint(mat, tint):
    b = _bsdf(mat)
    if b is None:
        return
    nt = mat.node_tree
    bc = b.inputs["Base Color"]
    if bc.is_linked:
        src = bc.links[0].from_socket
        mx = nt.nodes.new("ShaderNodeMix")
        mx.data_type = "RGBA"
        mx.blend_type = "MULTIPLY"
        mx.inputs["Factor"].default_value = 1.0
        nt.links.new(src, mx.inputs["A"])
        mx.inputs["B"].default_value = (*tint, 1)
        nt.links.new(mx.outputs["Result"], bc)
    else:
        c = bc.default_value
        bc.default_value = (c[0] * tint[0], c[1] * tint[1], c[2] * tint[2], 1)


def place(col, loc=(0, 0, 0), rot=0.0, scale=1.0, name=None, rot_xyz=None):
    """A collection instance of `col` at `loc` (Blender coords), turned `rot` radians about z."""
    e = bpy.data.objects.new(name or ("i_" + col.name), None)
    e.instance_type = "COLLECTION"
    e.instance_collection = col
    e.location = loc
    e.rotation_euler = rot_xyz if rot_xyz else (0, 0, rot)
    e.scale = (scale, scale, scale) if isinstance(scale, (int, float)) else scale
    bpy.context.scene.collection.objects.link(e)
    return e


def real_copy(col, loc=(0, 0, 0), rot=0.0, scale=1.0, link_to=None):
    """A real (non-instanced) linked-data copy of a source collection's objects, under one empty,
    for things that animate or deform."""
    root = bpy.data.objects.new("r_" + col.name, None)
    (link_to or bpy.context.scene.collection).objects.link(root)
    mapping = {}
    for o in col.objects:
        c = o.copy()
        mapping[o] = c
        (link_to or bpy.context.scene.collection).objects.link(c)
    for o, c in mapping.items():
        if o.parent in mapping:
            c.parent = mapping[o.parent]
        else:
            c.parent = root
    root.location = loc
    root.rotation_euler = (0, 0, rot)
    root.scale = (scale,) * 3 if isinstance(scale, (int, float)) else scale
    return root, list(mapping.values())


# --- lights and animation -------------------------------------------------------------------

def light(kind, loc, color, energy, radius=0.1, name="L", shadow=True, rot=(0, 0, 0), spot=None, size=None, spec=1.0):
    ld = bpy.data.lights.new(name, kind)
    try:
        ld.specular_factor = spec
    except Exception:
        pass
    ld.color = color
    ld.energy = energy
    if kind in ("POINT", "SPOT"):
        ld.shadow_soft_size = radius
    if kind == "AREA" and size:
        ld.size = size
    if kind == "SPOT" and spot:
        ld.spot_size = spot
        ld.spot_blend = 0.6
    ld.use_shadow = shadow
    o = bpy.data.objects.new(name, ld)
    o.location = loc
    o.rotation_euler = rot
    bpy.context.scene.collection.objects.link(o)
    return o


def periodic_noise(n_frames, seed, harmonics=((3, 1.0), (7, 0.6), (13, 0.4), (23, 0.25), (37, 0.15))):
    """Values in about -1..1 for frames 0..n-1 that loop exactly (whole cycles only)."""
    rnd = random.Random(seed)
    ph = [rnd.random() * TAU for _ in harmonics]
    norm = sum(a for _, a in harmonics)
    return [sum(a * math.sin(TAU * k * f / n_frames + p) for (k, a), p in zip(harmonics, ph)) / norm
            for f in range(n_frames)]


def key_series(id_data, path, values, index=-1, frame0=0):
    """Keyframes values[i] at frame frame0+i on id_data.path, linear, fast. id_data may be an ID or
    a struct inside one (a node socket)."""
    if index >= 0:
        id_data.keyframe_insert(path, index=index, frame=frame0)
    else:
        id_data.keyframe_insert(path, frame=frame0)
    owner = id_data.id_data
    full = path if owner == id_data else id_data.path_from_id(path)
    ad = owner.animation_data
    act = ad.action
    fc = None
    for f in _fcurves(act, owner):
        if f.data_path == full and (index < 0 or f.array_index == index):
            fc = f
            break
    fc.keyframe_points.clear()
    fc.keyframe_points.add(len(values))
    co = []
    for i, v in enumerate(values):
        co += [frame0 + i, v]
    fc.keyframe_points.foreach_set("co", co)
    for kp in fc.keyframe_points:
        kp.interpolation = "LINEAR"
    fc.update()
    return fc


def loop_noise(nt, vec_socket, n_frames, radius=1.5):
    """A 4D noise node whose pattern travels round a circle in its z/w dimensions over the loop
    (so it moves and loops without reversing). Returns the noise node."""
    N = nt.nodes
    add = N.new("ShaderNodeVectorMath")
    add.operation = "ADD"
    nt.links.new(vec_socket, add.inputs[0])
    nz = N.new("ShaderNodeTexNoise")
    nz.noise_dimensions = "4D"
    nt.links.new(add.outputs[0], nz.inputs["Vector"])
    key_series(add.inputs[1], "default_value", [radius * math.cos(TAU * f / n_frames) for f in range(n_frames)], index=2)
    key_series(nz.inputs["W"], "default_value", [radius * math.sin(TAU * f / n_frames) for f in range(n_frames)])
    return nz


def _fcurves(act, id_data=None):
    # Blender 4.4+ layered actions
    try:
        return act.fcurves
    except Exception:
        pass
    out = []
    for layer in act.layers:
        for strip in layer.strips:
            for cb in strip.channelbags:
                out += list(cb.fcurves)
    return out


def flicker(light_obj, n_frames, base, amount=0.35, seed=0, fast=True):
    hz = ((5, 1.0), (11, 0.7), (19, 0.5), (31, 0.4), (47, 0.3), (61, 0.2)) if fast else ((2, 1.0), (5, 0.6), (9, 0.3))
    vals = periodic_noise(n_frames, seed, hz)
    key_series(light_obj.data, "energy", [max(0.0, base * (1 + amount * v)) for v in vals])


def camera(loc, look_at, lens=35, name="Cam", sensor=36):
    cd = bpy.data.cameras.new(name)
    cd.lens = lens
    cd.sensor_width = sensor
    cd.clip_start = 0.1
    cd.clip_end = 400
    o = bpy.data.objects.new(name, cd)
    bpy.context.scene.collection.objects.link(o)
    o.location = loc
    aim(o, look_at)
    bpy.context.scene.camera = o
    return o


def aim(o, target):
    d = Vector(target) - Vector(o.location)
    o.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()


def cyclic_camera(cam, n_frames, path_fn):
    """path_fn(theta) -> (location, look_at); theta runs 0..2pi over the loop. Keys every frame."""
    locs, rots = [], []
    prev = None
    for f in range(n_frames):
        th = TAU * f / n_frames
        loc, tgt = path_fn(th)
        cam.location = loc
        aim(cam, tgt)
        e = cam.rotation_euler.copy()
        if prev is not None:
            e.make_compatible(prev)
        prev = e
        locs.append(Vector(loc))
        rots.append(e)
    for i in range(3):
        key_series(cam, "location", [l[i] for l in locs], index=i)
        key_series(cam, "rotation_euler", [r[i] for r in rots], index=i)


def gentle_path(centre, el, dist, az0_deg, tgt, push=0.012, drift_deg=0.3):
    """A near-still establishing camera for a theta loop: a small eased push-in that returns
    (dist * push at mid-loop) and a sub-degree sideways drift, aimed at a fixed point."""
    def path(th):
        ease = 0.5 - 0.5 * math.cos(th)          # 0 -> 1 -> 0, zero slope at the seam
        d = dist * (1 - push * ease)
        az = math.radians(az0_deg + drift_deg * math.sin(th))
        loc = (centre[0] - d * math.cos(el) * math.sin(az), centre[1] - d * math.cos(el) * math.cos(az), d * math.sin(el))
        return loc, tgt
    return path


def save(path):
    bpy.ops.wm.save_as_mainfile(filepath=path)


# --- effects in the scene -------------------------------------------------------------------

def flame_mat(name="flame", core=(1.0, 0.5, 0.12), edge=(0.9, 0.1, 0.01), strength=3.2):
    m = bpy.data.materials.get(name)
    if m:
        return m
    m = bpy.data.materials.new(name)
    nt, out = _nodes(m)
    N = nt.nodes
    L = nt.links.new
    tc = N.new("ShaderNodeTexCoord")
    sep = N.new("ShaderNodeSeparateXYZ")
    L(tc.outputs["Generated"], sep.inputs[0])
    ramp = N.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].color = (*core, 1)
    ramp.color_ramp.elements[1].color = (*edge, 1)
    ramp.color_ramp.elements[0].position = 0.15
    ramp.color_ramp.elements[1].position = 0.85
    L(sep.outputs[2], ramp.inputs[0])
    lw = N.new("ShaderNodeLayerWeight")
    lw.inputs[0].default_value = 0.5
    # fresnel-ish soft edge: facing -> 1
    inv = N.new("ShaderNodeMath")
    inv.operation = "SUBTRACT"
    inv.inputs[0].default_value = 1.0
    L(lw.outputs["Facing"], inv.inputs[1])
    pw = N.new("ShaderNodeMath")
    pw.operation = "POWER"
    pw.inputs[1].default_value = 1.6
    L(inv.outputs[0], pw.inputs[0])
    top = N.new("ShaderNodeMath")
    top.operation = "SUBTRACT"
    top.inputs[0].default_value = 1.0
    L(sep.outputs[2], top.inputs[1])
    a = N.new("ShaderNodeMath")
    a.operation = "MULTIPLY"
    L(pw.outputs[0], a.inputs[0])
    L(top.outputs[0], a.inputs[1])
    em = N.new("ShaderNodeEmission")
    L(ramp.outputs[0], em.inputs[0])
    em.inputs[1].default_value = strength
    tr = N.new("ShaderNodeBsdfTransparent")
    mx = N.new("ShaderNodeMixShader")
    L(a.outputs[0], mx.inputs[0])
    L(tr.outputs[0], mx.inputs[1])
    L(em.outputs[0], mx.inputs[2])
    L(mx.outputs[0], out.inputs[0])
    try:
        m.surface_render_method = "BLENDED"
    except Exception:
        m.blend_method = "BLEND"
    try:
        m.use_transparent_shadow = True
    except Exception:
        pass
    return m


_flame_mesh = None


def flame(loc, size, n_frames, seed=0, mat=None, light_energy=0.0, light_color=(1.0, 0.5, 0.18), light_radius=0.15,
          light_up=0.3, shadow=True):
    """A flickering flame tongue (two crossed teardrops) and, if light_energy, its flickering light."""
    global _flame_mesh
    if _flame_mesh is None:
        bpy.ops.mesh.primitive_uv_sphere_add(segments=12, ring_count=8, radius=1)
        o = bpy.context.active_object
        me = o.data
        for v in me.vertices:
            z = (v.co.z + 1) / 2  # 0..1
            r = math.sin(math.pi * min(1, z ** 0.8)) * (1 - z) ** 0.4 * 1.15
            l = math.hypot(v.co.x, v.co.y) or 1
            v.co.x = v.co.x / l * r * 0.5 if l > 1e-5 else 0
            v.co.y = v.co.y / l * r * 0.5 if l > 1e-5 else 0
            v.co.z = z * 2.0
        _flame_mesh = me
        bpy.data.objects.remove(o)
    rnd = random.Random(seed)
    o = bpy.data.objects.new("flame", _flame_mesh)
    bpy.context.scene.collection.objects.link(o)
    o.data.materials.clear() if False else None
    if not o.data.materials:
        o.data.materials.append(mat or flame_mat())
    o.location = loc
    o.visible_shadow = False
    try:
        o.visible_shadow = False
    except Exception:
        pass
    sx = periodic_noise(n_frames, seed * 7 + 1, ((7, 1.0), (13, 0.6), (29, 0.4)))
    sz = periodic_noise(n_frames, seed * 7 + 2, ((5, 1.0), (11, 0.7), (23, 0.5), (41, 0.3)))
    rz = periodic_noise(n_frames, seed * 7 + 3, ((3, 1.0), (8, 0.5)))
    key_series(o, "scale", [size * 0.5 * (1 + 0.12 * v) for v in sx], index=0)
    key_series(o, "scale", [size * 0.5 * (1 + 0.12 * v) for v in sx], index=1)
    key_series(o, "scale", [size * (1 + 0.28 * v) for v in sz], index=2)
    key_series(o, "rotation_euler", [0.12 * v for v in rz], index=0)
    key_series(o, "rotation_euler", [rnd.random() * TAU + 0.5 * v for v in rz], index=2)
    L = None
    if light_energy > 0:
        L = light("POINT", (loc[0], loc[1], loc[2] + light_up), light_color, light_energy, radius=light_radius,
                  name="fire", shadow=shadow)
        flicker(L, n_frames, light_energy, 0.3, seed=seed + 100)
    return o, L


FX = []


def fx_marker(kind, loc, **params):
    """An effect the 2D post pass draws (embers, smoke, sparks): its world position is projected
    to the screen for every frame by export_fx."""
    FX.append(dict(kind=kind, loc=list(loc), **params))


def export_fx(path):
    import bpy_extras
    sc = bpy.context.scene
    cam = sc.camera
    frames = []
    for f in range(sc.frame_start, sc.frame_end + 1):
        sc.frame_set(f)
        pts = []
        for m in FX:
            p = Vector(m["loc"])
            co = bpy_extras.object_utils.world_to_camera_view(sc, cam, p)
            # screen size of one metre at that depth
            up = cam.matrix_world.to_3x3() @ Vector((0, 1, 0))
            co2 = bpy_extras.object_utils.world_to_camera_view(sc, cam, p + up)
            px = abs(co2.y - co.y) * sc.render.resolution_y
            pts.append([co.x, 1 - co.y, co.z, px])
        frames.append(pts)
    cm = cam.matrix_world
    json.dump(dict(markers=FX, frames=frames, w=sc.render.resolution_x, h=sc.render.resolution_y), open(path, "w"))


# --- characters -----------------------------------------------------------------------------

def character(path, loc=(0, 0, 0), rot=0.0, scale=1.0, action="Idle", n_frames=192, bone_heuristic="BLENDER",
              speed=1.0):
    """Imports a game character (KayKit rig) with `action` looping a whole number of times over the
    loop (its speed eased so it fits). Returns (root empty, armature, meshes)."""
    acts_before = set(bpy.data.actions)
    objs = import_file(path, bone_heuristic=bone_heuristic)
    new_acts = [a for a in bpy.data.actions if a not in acts_before]
    arm = next(o for o in objs if o.type == "ARMATURE")
    meshes = [o for o in objs if o.type == "MESH"]
    for o in meshes:
        if o.name.startswith("Icosphere"):
            o.hide_render = True
            o.hide_viewport = True
    root = bpy.data.objects.new("char_root", None)
    bpy.context.scene.collection.objects.link(root)
    for o in objs:
        if o.parent is None:
            o.parent = root
    root.location = loc
    root.rotation_euler = (0, 0, rot)
    root.scale = (scale,) * 3
    act = None
    for a in new_acts:
        base = a.name.split(".")[0]
        if base == action or base == action + "_" + arm.name.split(".")[0] or base == action + "_Rig":
            act = a
            break
    ad = arm.animation_data or arm.animation_data_create()
    ad.action = None
    for t in list(ad.nla_tracks):
        ad.nla_tracks.remove(t)
    if act:
        f0, f1 = act.frame_range
        length = (f1 - f0) / speed
        reps = max(1, round(n_frames / length))
        tr = ad.nla_tracks.new()
        st = tr.strips.new("loop", 0, act)
        st.action_frame_start = f0
        st.action_frame_end = f1
        try:
            if act.slots:
                st.action_slot = act.slots[0]
        except Exception:
            pass
        st.repeat = reps
        st.scale = n_frames / (reps * (f1 - f0))
        st.frame_start = 0
        st.frame_end = n_frames
        st.extrapolation = "HOLD"
        print("anim", act.name, f0, f1, "reps", reps, "scale", st.scale)
    else:
        print("no action", action, [a.name for a in bpy.data.actions][:20])
    return root, arm, meshes


def flash_values(n_frames, flashes, base=0.0, seed=5):
    """Lightning: for each (frame, strength) a sharp spike that decays with a flicker; periodic."""
    rnd = random.Random(seed)
    vals = [base] * n_frames
    for fr, s in flashes:
        for d in range(0, 14):
            f = (fr + d) % n_frames
            k = s * math.exp(-d / 2.4)
            if d in (1, 4):
                k *= 0.35
            vals[f] = max(vals[f], base + k)
    return vals


def cloth_wave(objs, cloth_mats, n_frames, strength=0.12, size=0.9, radius=1.5, seed=0, top=None):
    """Wind in hanging cloth: a Displace modifier along the normals, weighted by how far down the
    cloth each vertex hangs, its noise texture carried round a circle so it loops."""
    tex = bpy.data.textures.new("wind%d" % seed, "CLOUDS")
    tex.noise_scale = size
    tex.noise_depth = 1
    em = bpy.data.objects.new("wind_drv%d" % seed, None)
    bpy.context.scene.collection.objects.link(em)
    key_series(em, "location", [radius * math.cos(TAU * f / n_frames) for f in range(n_frames)], index=0)
    key_series(em, "location", [radius * math.sin(TAU * f / n_frames) for f in range(n_frames)], index=2)
    done = set()
    for o in objs:
        if o.type != "MESH":
            continue
        me = o.data
        names = [m.name.split(".")[0] if m else "" for m in me.materials]
        idx = {i for i, n in enumerate(names) if n in cloth_mats}
        if not idx:
            continue
        vg = o.vertex_groups.get("cloth") or o.vertex_groups.new(name="cloth")
        zs = [v.co.z for v in me.vertices]
        cloth_v = set()
        for p in me.polygons:
            if p.material_index in idx:
                cloth_v.update(p.vertices)
        if not cloth_v:
            continue
        zt = top if top is not None else max(me.vertices[i].co.z for i in cloth_v)
        zb = min(me.vertices[i].co.z for i in cloth_v)
        for i in cloth_v:
            w = (zt - me.vertices[i].co.z) / max(1e-3, zt - zb)
            vg.add([i], max(0.0, min(1.0, w)) ** 1.2, "REPLACE")
        md = o.modifiers.new("wind", "DISPLACE")
        md.texture = tex
        md.texture_coords = "OBJECT"
        md.texture_coords_object = em
        md.direction = "NORMAL"
        md.vertex_group = "cloth"
        md.strength = strength
        md.mid_level = 0.5
    return em


def wax_tips(col, mats=("wax", "wax_red"), cell=0.05):
    """Tops of the candles in a source collection (local coords): the highest wax vertex of each
    small xy cluster that stands proud of its neighbours."""
    tips = {}
    for o in col.objects:
        if o.type != "MESH":
            continue
        me = o.data
        names = [m.name.split(".")[0] if m else "" for m in me.materials]
        idx = {i for i, n in enumerate(names) if n in mats}
        vs = set()
        for p in me.polygons:
            if p.material_index in idx:
                vs.update(p.vertices)
        mw = o.matrix_world
        for i in vs:
            w = mw @ me.vertices[i].co
            k = (round(w.x / cell), round(w.y / cell))
            if k not in tips or tips[k].z < w.z:
                tips[k] = w.copy()
    # keep cluster maxima that are the highest within ~2 cells
    out = []
    for k, v in tips.items():
        best = True
        for dx in (-2, -1, 0, 1, 2):
            for dy in (-2, -1, 0, 1, 2):
                kk = (k[0] + dx, k[1] + dy)
                if kk != k and kk in tips and tips[kk].z > v.z + 1e-4:
                    best = False
        if best:
            out.append(v)
    # merge near-duplicates
    res = []
    for v in sorted(out, key=lambda q: -q.z):
        if all((v - r).length > cell * 2.5 for r in res):
            res.append(v)
    return res


def ripple_bump(nt, pos_socket, n_frames, scale=1.5, cycles=3, width=0.05, seed=0.0):
    """Rain rings on water: one ring per Voronoi cell, each starting at its own moment, expanding and
    fading; `cycles` drops per cell per loop. Returns a height socket."""
    N = nt.nodes
    L = nt.links.new
    vor = N.new("ShaderNodeTexVoronoi")
    vor.voronoi_dimensions = "3D"
    vor.inputs["Scale"].default_value = scale
    mp = N.new("ShaderNodeVectorMath")
    mp.operation = "ADD"
    mp.inputs[1].default_value = (seed, seed * 1.7, 0)
    L(pos_socket, mp.inputs[0])
    L(mp.outputs[0], vor.inputs["Vector"])
    sep = N.new("ShaderNodeSeparateColor")
    L(vor.outputs["Color"], sep.inputs[0])
    tnode = N.new("ShaderNodeMath")
    tnode.operation = "ADD"
    L(sep.outputs[0], tnode.inputs[0])
    key_series(tnode.inputs[1], "default_value", [cycles * f / n_frames for f in range(n_frames)])
    ph = N.new("ShaderNodeMath")
    ph.operation = "FRACT"
    L(tnode.outputs[0], ph.inputs[0])
    rad = N.new("ShaderNodeMath")
    rad.operation = "MULTIPLY"
    rad.inputs[1].default_value = 0.45
    L(ph.outputs[0], rad.inputs[0])
    dd = N.new("ShaderNodeMath")
    dd.operation = "SUBTRACT"
    L(vor.outputs["Distance"], dd.inputs[0])
    L(rad.outputs[0], dd.inputs[1])
    ab = N.new("ShaderNodeMath")
    ab.operation = "ABSOLUTE"
    L(dd.outputs[0], ab.inputs[0])
    ring = N.new("ShaderNodeMapRange")
    ring.inputs["From Min"].default_value = 0.0
    ring.inputs["From Max"].default_value = width
    ring.inputs["To Min"].default_value = 1.0
    ring.inputs["To Max"].default_value = 0.0
    L(ab.outputs[0], ring.inputs["Value"])
    fade = N.new("ShaderNodeMath")
    fade.operation = "SUBTRACT"
    fade.inputs[0].default_value = 1.0
    L(ph.outputs[0], fade.inputs[1])
    amp = N.new("ShaderNodeMath")
    amp.operation = "MULTIPLY"
    L(ring.outputs[0], amp.inputs[0])
    L(fade.outputs[0], amp.inputs[1])
    return amp.outputs[0]

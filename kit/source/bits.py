"""Small hand-built set dressing the game has no model for (hooks, cleavers, chains, beams)."""
import bpy, bmesh, math, random
from mathutils import Vector, Matrix
import lib


def _obj(name, me, mat=None, loc=(0, 0, 0), rot=(0, 0, 0), parent=None):
    o = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(o)
    if mat:
        me.materials.append(mat)
    o.location = loc
    o.rotation_euler = rot
    if parent:
        o.parent = parent
    return o


def box(name, size, mat, loc=(0, 0, 0), rot=(0, 0, 0), parent=None, bevel=0.0):
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        v.co = Vector((v.co.x * size[0], v.co.y * size[1], v.co.z * size[2]))
    if bevel > 0:
        bmesh.ops.bevel(bm, geom=list(bm.edges), offset=bevel, segments=1, affect="EDGES")
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    return _obj(name, me, mat, loc, rot, parent)


def cyl(name, r, h, mat, loc=(0, 0, 0), rot=(0, 0, 0), seg=10, parent=None, r2=None):
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=seg, radius1=r, radius2=r if r2 is None else r2, depth=h)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    for p in me.polygons:
        p.use_smooth = True
    return _obj(name, me, mat, loc, rot, parent)


def torus(name, R, r, mat, loc=(0, 0, 0), rot=(0, 0, 0), parent=None, arc=1.0, seg=12, rseg=6):
    me = bpy.data.meshes.new(name)
    verts, faces = [], []
    n = seg
    closed = arc >= 0.999
    rings = n if closed else n + 1
    for i in range(rings):
        a = math.tau * arc * i / n
        cx, cy = math.cos(a) * R, math.sin(a) * R
        for j in range(rseg):
            b = math.tau * j / rseg
            d = R + r * math.cos(b)
            verts.append((math.cos(a) * d, math.sin(a) * d, r * math.sin(b)))
    for i in range(n):
        i2 = (i + 1) % rings
        for j in range(rseg):
            j2 = (j + 1) % rseg
            faces.append((i * rseg + j, i2 * rseg + j, i2 * rseg + j2, i * rseg + j2))
    me.from_pydata(verts, [], faces)
    for p in me.polygons:
        p.use_smooth = True
    return _obj(name, me, mat, loc, rot, parent)


def chain(name, links, link_len, mat, top, parent=None, thick=0.018):
    """A hanging chain of `links` from `top` downward (local to parent). Returns the links."""
    out = []
    R = link_len * 0.5
    for i in range(links):
        z = -i * link_len * 0.78
        rot = (math.pi / 2, 0, (math.pi / 2) * (i % 2))
        t = torus("%s_%d" % (name, i), R, thick, mat, (top[0], top[1], top[2] + z - R), rot, parent, seg=10, rseg=5)
        t.scale = (0.62, 1.0, 1.0)
        out.append(t)
    return out


def hook(name, mat, loc, parent=None, size=0.22):
    """An S-shaped butcher's hook: an open ring bent up at the bottom."""
    h = torus(name + "_lo", size * 0.5, 0.018, mat, (loc[0], loc[1], loc[2]), (math.pi / 2, 0, 0), parent, arc=0.72, seg=12)
    h.rotation_euler = (math.pi / 2, 1.9, 0)
    s = torus(name + "_hi", size * 0.3, 0.016, mat, (loc[0], loc[1], loc[2] + size * 0.75), (math.pi / 2, 0, 0), parent,
              arc=0.7, seg=10)
    s.rotation_euler = (math.pi / 2, -1.2, 0)
    return h


def meat(name, mat, loc, size=(0.22, 0.18, 0.45), parent=None, seed=0):
    rnd = random.Random(seed)
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=12, v_segments=8, radius=1.0)
    for v in bm.verts:
        n = 1 + 0.12 * math.sin(v.co.x * 5 + seed) * math.cos(v.co.z * 4 + seed * 2) + rnd.uniform(-0.04, 0.04)
        taper = 1.0 - 0.35 * max(0, v.co.z)
        v.co = Vector((v.co.x * size[0] * n * taper, v.co.y * size[1] * n * taper, v.co.z * size[2]))
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    for p in me.polygons:
        p.use_smooth = True
    return _obj(name, me, mat, loc, (0, 0, rnd.random() * 6), parent)


def cleaver(name, steel, wood, loc=(0, 0, 0), rot=(0, 0, 0), parent=None, s=1.0):
    root = bpy.data.objects.new(name, None)
    bpy.context.scene.collection.objects.link(root)
    root.location = loc
    root.rotation_euler = rot
    root.scale = (s, s, s)
    if parent:
        root.parent = parent
    box(name + "_blade", (0.42, 0.012, 0.22), steel, (0.0, 0, 0.0), parent=root, bevel=0.004)
    cyl(name + "_handle", 0.022, 0.26, wood, (-0.32, 0, 0.07), (0, math.pi / 2, 0), parent=root, seg=8)
    return root


def mats():
    return dict(
        iron=lib.flat_mat("b_iron", (0.06, 0.055, 0.055), 0.45, 0.85),
        rust=lib.flat_mat("b_rust", (0.16, 0.07, 0.035), 0.7, 0.4),
        steel=lib.flat_mat("b_steel", (0.35, 0.34, 0.33), 0.28, 1.0),
        wood=lib.flat_mat("b_wood", (0.16, 0.08, 0.04), 0.8, 0.0),
        meat=lib.flat_mat("b_meat", (0.11, 0.02, 0.015), 0.5, 0.0),
        fat=lib.flat_mat("b_fat", (0.55, 0.42, 0.3), 0.5, 0.0),
    )


def stew_mat(n_frames):
    """Bubbling stew: dark crust over a glowing red-orange broth, the bubbles drifting in a loop."""
    m = bpy.data.materials.new("stew")
    nt = m.node_tree if m.use_nodes else (setattr(m, "use_nodes", True) or m.node_tree)
    for nd in list(nt.nodes):
        nt.nodes.remove(nd)
    N = nt.nodes; L = nt.links.new
    out = N.new("ShaderNodeOutputMaterial")
    tc = N.new("ShaderNodeTexCoord")
    nz = lib.loop_noise(nt, tc.outputs["Object"], n_frames, 0.6)
    nz.inputs["Scale"].default_value = 1.3
    nz.inputs["Detail"].default_value = 4.0
    ramp = N.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position = 0.40
    ramp.color_ramp.elements[0].color = (1.0, 0.16, 0.015, 1)
    ramp.color_ramp.elements[1].position = 0.56
    ramp.color_ramp.elements[1].color = (0.03, 0.008, 0.004, 1)
    L(nz.outputs["Fac"], ramp.inputs[0])
    b = N.new("ShaderNodeBsdfPrincipled")
    b.inputs["Base Color"].default_value = (0.08, 0.02, 0.01, 1)
    b.inputs["Roughness"].default_value = 0.55
    L(ramp.outputs[0], b.inputs["Emission Color"])
    b.inputs["Emission Strength"].default_value = 0.5
    L(b.outputs[0], out.inputs[0])
    return m


def candles(center, n, radius, n_frames, seed=0, wax=None, light=60.0, hmin=0.12, hmax=0.55, base_z=0.0,
            light_color=(1.0, 0.62, 0.3)):
    """A cluster of church candles of different heights, each lit, and one flickering light for them."""
    rnd = random.Random(seed)
    wax = wax or lib.flat_mat("candle_wax", (0.78, 0.72, 0.58), 0.6)
    tops = []
    for i in range(n):
        a = rnd.random() * math.tau
        r = math.sqrt(rnd.random()) * radius
        h = rnd.uniform(hmin, hmax)
        cr = rnd.uniform(0.035, 0.07)
        x, y = center[0] + math.cos(a) * r, center[1] + math.sin(a) * r
        cyl("candle", cr, h, wax, (x, y, base_z + h / 2), seg=8)
        lib.flame((x, y, base_z + h + 0.005), rnd.uniform(0.05, 0.075), n_frames, seed=seed * 100 + i,
                  mat=lib.flame_mat("candle_flame", core=(1.0, 0.75, 0.35), edge=(1.0, 0.35, 0.06), strength=6.0))
        tops.append((x, y, base_z + h))
    L = None
    if light > 0:
        L = lib.light("POINT", (center[0], center[1], base_z + hmax + 0.35), light_color, light, radius=0.05,
                      name="candles", shadow=False, spec=0.0)
        lib.flicker(L, n_frames, light, 0.12, seed=seed + 500)
    return tops, L

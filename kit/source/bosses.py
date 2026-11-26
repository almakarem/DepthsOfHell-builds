"""Boss figures, dressed as in the game. Each builder returns (root, armature, height)."""
import bpy, math
from mathutils import Matrix, Vector
import lib, bits, dress
from lib import godot_xform as gx

REPO = lib.REPO


def _wing_pivots(arm, root, roots, sizes, poses, wing_path, chest="chest", mirror_mode="scale"):
    out = []
    for i, (r, span, pose) in enumerate(zip(roots, sizes, poses)):
        for side in (1, -1):
            holder = dress.on_bone(arm, root, chest, (r[0] * side, r[1], r[2]), "wing_holder")
            pivot = dress.node(holder, gx((0, 0, 0), (pose[0], pose[1] * side, pose[2] * side)), "wing_pivot")
            h2 = dress.node(pivot, gx(scale=(side, 1, 1)), "wing_mirror")
            w = dress.node(h2, gx((0.5 * span, 0, 0), (0, 90, 0), (span,) * 3), "wing")
            dress.scene_under(w, REPO + wing_path)
            out.append(pivot)
    return out


def verrier(loc, rot, scale, n_frames, action="Idle", wings_open=0.2):
    root, arm, meshes = lib.character(REPO + "assets/characters/verrier/verrier.glb", loc, rot, scale, action, n_frames)
    # sceptre in the right hand, the seal on the left forearm
    s = dress.bone_node(arm, "handslot.r", name="sceptre_slot")
    dress.prop(s, "assets/props/verrier/sceptre.glb", 2.25, 0.36)
    l = dress.bone_node(arm, "handslot.l", name="seal_slot")
    sr = dress.node(l, gx((0, 0.02, 0.2)), "seal_root")
    SEAL_CENTRE = Vector((0.1, 0.18, 0.08))
    face = Vector((0.77, 0.08, 0.63)).normalized()
    q = face.rotation_difference(Vector((0, 0, 1)))  # Godot Basis(Quaternion(face, BACK))
    turn = dress.node(sr, lib.C @ q.to_matrix().to_4x4() @ lib.CI, "seal_turn")
    p = dress.node(turn, gx(tuple(-SEAL_CENTRE * 0.62), (0, 0, 0), (0.62,) * 3), "seal")
    dress.scene_under(p, REPO + "assets/props/verrier/seal.glb")
    # the cracked iron halo behind his head
    hh = dress.on_bone(arm, root, "head", (0, 2.24, -0.22), "halo")
    iron = lib.flat_mat("halo_iron", (0.2, 0.19, 0.2), 0.7, 0.5)
    count = 22
    for i in range(count):
        if i in (3, 4, 14):
            continue
        ang = math.tau * i / count
        w = math.tau * 0.31 / count * (0.82 if i in (2, 5, 13, 15) else 1.02)
        seg = bits.box("halo_seg", (w, 0.03, 0.045), iron)
        seg.parent = hh
        seg.matrix_parent_inverse = Matrix.Identity(4)
        seg.matrix_basis = gx((math.cos(ang) * 0.31, math.sin(ang) * 0.31, 0), (0, 0, math.degrees(ang + math.pi / 2)))
    # torn wings on his back, folded (opened a little)
    FOLDED = (8, 62, -72)
    SPREAD = (-6, 12, 18)
    pose = tuple(a + (b - a) * wings_open for a, b in zip(FOLDED, SPREAD))
    _wing_pivots(arm, root, [(0.1, 1.72, -0.2)], [1.55], [pose], "assets/props/verrier/wing.glb")
    return root, arm, 2.39 * scale


def luvart(loc, rot, scale, n_frames, action="Scythe_Idle", wings_open=0.75, scythes=True):
    root, arm, meshes = lib.character(REPO + "assets/characters/luvart/luvart.glb", loc, rot, scale, action, n_frames)
    FOLDED = [(-6, 52, -64), (-4, 46, -80), (-2, 40, -96)]
    SPREAD = [(-8, 16, 34), (-4, 12, 4), (0, 10, -26)]
    poses = [tuple(a + (b - a) * wings_open for a, b in zip(f, s)) for f, s in zip(FOLDED, SPREAD)]
    _wing_pivots(arm, root, [(0.12, 1.86, -0.2), (0.1, 1.6, -0.22), (0.08, 1.34, -0.2)], [1.7, 1.3, 0.95], poses,
                 "assets/props/luvart/wing.glb")
    h = dress.on_bone(arm, root, "head", (0, 2.2, -0.28), "halo")
    hs = dress.node(h, gx(scale=(0.8,) * 3), "halo_s")
    dress.scene_under(hs, REPO + "assets/props/luvart/halo.glb", emit=dict(halo_gold=((1.0, 0.8, 0.45), 2.0)))
    if scythes:
        for side, bone in ((1, "handslot.r"), (-1, "handslot.l")):
            s = dress.bone_node(arm, bone, name="scythe_slot")
            m = dress.node(s, gx(scale=(side, 1, 1)), "scythe_mirror")
            dress.prop(m, "assets/props/luvart/scythe.glb", 1.45, 0.3)
    return root, arm, 2.4 * scale


def madeleine(loc, rot, scale, n_frames, action="Nun_Idle"):
    root, arm, meshes = lib.character(REPO + "assets/characters/madeleine/madeleine.glb", loc, rot, scale, action, n_frames)
    # the censer hanging under her right hand on its chain (kept hanging straight down)
    hang = bpy.data.objects.new("censer_hang", None)
    bpy.context.scene.collection.objects.link(hang)
    hang.scale = (scale,) * 3
    cl = hang.constraints.new("CHILD_OF")
    cl.target = arm
    cl.subtarget = "handslot.r"
    cl.use_rotation_x = cl.use_rotation_y = cl.use_rotation_z = False
    cl.use_scale_x = cl.use_scale_y = cl.use_scale_z = False
    cl.inverse_matrix = Matrix.Identity(4)
    iron = lib.flat_mat("chain_iron", (0.05, 0.05, 0.05), 0.4, 0.9)
    bits.chain("mch", 5, 0.12, iron, (0, 0, 0), parent=hang, thick=0.012)
    c = dress.node(hang, Matrix.Translation((0, 0, -0.55 - 0.21)) @ Matrix.Diagonal((0.42, 0.42, 0.42, 1)), "censer")
    dress.scene_under(c, REPO + "assets/props/luvart/censer.glb")
    # the angel mask floating beside her face
    mh = dress.on_bone(arm, root, "head", (0.26, 2.12, 0.22), "mask_holder")
    mk = dress.node(mh, gx((0, 0, 0), (0, math.degrees(-math.pi / 2 - 0.35), 0), (0.3,) * 3), "mask")
    dress.scene_under(mk, REPO + "assets/props/luvart/mask.glb")
    return root, arm, 2.19 * scale


def behemoth(loc, rot, scale, n_frames, action="Idle"):
    root, arm, meshes = lib.character(REPO + "assets/characters/behemoth/behemoth.glb", loc, rot, scale, action, n_frames)
    gear = 1.0 / 1.4
    s = dress.bone_node(arm, "handslot.r", name="machete_slot")
    g = dress.node(s, gx(scale=(1.3 * gear,) * 3), "machete")
    dress.prop(g, "assets/props/blade/blade.fbx", 1.5, 0.22, math.pi / 2)
    l = dress.bone_node(arm, "handslot.l", name="lantern_slot")
    hook = dress.node(l, gx(scale=(gear,) * 3), "lantern_hook")
    lan = dress.node(hook, gx((0, -0.15, 0.05)), "lantern")
    lm = dress.prop(lan, "assets/props/lantern/lantern.fbx", 0.6, 0.9)
    glow = bpy.data.objects.new("lantern_glow_at", None)
    bpy.context.scene.collection.objects.link(glow)
    glow.parent = lan
    glow.matrix_parent_inverse = Matrix.Identity(4)
    glow.matrix_basis = gx((0, -0.28, 0))
    return root, arm, 2.2 * scale, glow


def behemoth_showcase(path, loc, rot, scale, n_frames, clips=(("Idle", None), ("Idle_Lantern", None)),
                      lantern_at=(0.30, -0.10, 0.75)):
    """The re-rigged Behemoth from the showcase .blend: his body, the machete in his right fist and the
    lantern on his left (both skinned to the hand slots; the hidden meat fork is left out). `clips` are
    played one after another to fill the loop: (action, frames or None = share what is left).
    Returns (root, rig, height, glow) like behemoth()."""
    want = ["Rig", "Behemoth", "Machete", "Lantern"]
    if path.lower().endswith((".glb", ".gltf")):   # the same showcase exported as glTF (readable by any Blender)
        before = set(bpy.data.objects)
        bpy.ops.import_scene.gltf(filepath=path, bone_heuristic="BLENDER")
        new = [o for o in bpy.data.objects if o not in before]
        for o in new:
            if o.name.split(".")[0] not in want:
                bpy.data.objects.remove(o)
        objs = {o.name.split(".")[0]: o for o in bpy.data.objects if o in new and o.name.split(".")[0] in want}
        for o in objs.values():
            for c in list(o.users_collection):
                c.objects.unlink(o)
    else:
        with bpy.data.libraries.load(path, link=False) as (src, dst):
            dst.objects = [n for n in src.objects if n in want]
            dst.actions = [c for c, _ in clips if c in src.actions]
        objs = {o.name.split(".")[0]: o for o in dst.objects}
    # its prop textures point into the game's assets on the machine that made it: use this repo's copy
    import os
    for im in bpy.data.images:
        if im.packed_file or "/assets/" not in im.filepath:
            continue
        local = REPO + "assets/" + im.filepath.split("/assets/", 1)[1]
        if os.path.exists(local):
            im.filepath = local
            im.reload()
    root = bpy.data.objects.new("behemoth_root", None)
    bpy.context.scene.collection.objects.link(root)
    root.location = loc
    root.rotation_euler = (0, 0, rot)
    root.scale = (scale,) * 3
    for o in objs.values():
        bpy.context.scene.collection.objects.link(o)
        o.hide_render = o.hide_viewport = False
    # warm the lantern's glass glow (its glow map is white) to the kitchen's fire colour
    for sl in objs["Lantern"].material_slots:
        m = sl.material
        if not (m and m.use_nodes):
            continue
        nt = m.node_tree
        for nd in [n for n in nt.nodes if n.type == "BSDF_PRINCIPLED"]:
            sock = nd.inputs["Emission Color"]
            mix = nt.nodes.new("ShaderNodeMix")
            mix.data_type = "RGBA"
            mix.blend_type = "MULTIPLY"
            ident = lambda socks, i: [x for x in socks if x.identifier == i][0]
            ident(mix.inputs, "Factor_Float").default_value = 1.0
            a_in, b_in, out = ident(mix.inputs, "A_Color"), ident(mix.inputs, "B_Color"), ident(mix.outputs, "Result_Color")
            b_in.default_value = (1.0, 0.55, 0.2, 1.0)
            if sock.is_linked:
                nt.links.new(sock.links[0].from_socket, a_in)
            else:
                a_in.default_value = sock.default_value
            nt.links.new(out, sock)
            nd.inputs["Emission Strength"].default_value = 5.0
    rig = objs["Rig"]
    rig.parent = root
    rig.matrix_parent_inverse = Matrix.Identity(4)
    ad = rig.animation_data or rig.animation_data_create()
    for t in list(ad.nla_tracks):
        ad.nla_tracks.remove(t)
    ad.action = None
    def find_action(c):
        for n in (c, c + "_Rig", c + "_Armature"):
            if n in bpy.data.actions:
                return bpy.data.actions[n]
        raise KeyError(c)
    acts = [find_action(c) for c, _ in clips]
    fixed = sum(fr for _, fr in clips if fr)
    free = [c for c, fr in clips if not fr]
    natural = sum(acts[i].frame_range[1] - acts[i].frame_range[0] for i, (c, fr) in enumerate(clips) if not fr)
    tr = ad.nla_tracks.new()
    t0 = 0.0
    for i, ((c, fr), act) in enumerate(zip(clips, acts)):
        f0, f1 = act.frame_range
        length = fr if fr else round((n_frames - fixed) * (f1 - f0) / natural)
        if i == len(clips) - 1:
            length = n_frames - t0
        st = tr.strips.new(c, int(round(t0)), act)
        st.extrapolation = "HOLD_FORWARD"
        st.blend_type = "REPLACE"
        st.scale = length / (f1 - f0)
        st.frame_end = t0 + length
        t0 += length
    print("behemoth clips", [(s.name, s.frame_start, s.frame_end) for s in tr.strips])
    # the lantern light sits in the glass and follows the left hand
    bpy.context.scene.frame_set(0)
    glow = bpy.data.objects.new("lantern_glow_at", None)
    bpy.context.scene.collection.objects.link(glow)
    glow.parent = rig
    glow.parent_type = "BONE"
    glow.parent_bone = "handslot.l"
    bpy.context.view_layer.update()
    # the middle of the lantern as it hangs at the loop's first frame
    dg = bpy.context.evaluated_depsgraph_get()
    le = objs["Lantern"].evaluated_get(dg)
    me = le.to_mesh()
    vs = [le.matrix_world @ v.co for v in me.vertices]
    centre = Vector([(min(v[i] for v in vs) + max(v[i] for v in vs)) / 2 for i in range(3)])
    le.to_mesh_clear()
    glow.matrix_world = Matrix.Translation(centre)
    return root, rig, 1.55 * scale, glow

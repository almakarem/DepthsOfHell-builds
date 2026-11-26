"""The bosses' gear, as the game puts it on (scripts/enemies/*_look.gd, behemoth.gd), rebuilt in
Blender: Godot node transforms converted to Blender's z-up space, bone attachments on the KayKit rig
(imported with bone_heuristic BLENDER so the bone frames are the glTF ones)."""
import bpy, math
from mathutils import Matrix, Vector
import lib
from lib import C, CI, godot_xform

REPO = lib.REPO


def node(parent=None, gx=None, name="n"):
    """An empty under `parent` whose local transform is the Godot transform `gx` (a Blender matrix
    from lib.godot_xform)."""
    e = bpy.data.objects.new(name, None)
    bpy.context.scene.collection.objects.link(e)
    e.empty_display_size = 0.1
    if parent is not None:
        e.parent = parent
        e.matrix_parent_inverse = Matrix.Identity(4)
    e.matrix_basis = gx if gx is not None else Matrix.Identity(4)
    return e


def scene_under(parent, path, mat_tint=None, emit=None):
    """Imports a glb/gltf under `parent` (its root objects keep their own transforms)."""
    objs = lib.import_file(path)
    for o in objs:
        if o.parent is None:
            o.parent = parent
            o.matrix_parent_inverse = Matrix.Identity(4)
        if o.type == "MESH":
            for s in o.material_slots:
                if s.material is None:
                    continue
                base = s.material.name.split(".")[0]
                if emit and base in emit:
                    lib._add_emission(s.material, *emit[base])
                if mat_tint and base in mat_tint:
                    lib._tint(s.material, mat_tint[base])
    return objs


def bone_node(arm, bone, gx=None, name="slot"):
    """An empty that follows `bone` (BoneAttachment3D): its local transform gx in the bone's frame."""
    e = bpy.data.objects.new(name, None)
    bpy.context.scene.collection.objects.link(e)
    e.parent = arm
    e.parent_type = "BONE"
    e.parent_bone = bone
    b = arm.data.bones[bone]
    e.matrix_parent_inverse = Matrix.Translation((0, -b.length, 0))
    e.matrix_basis = gx if gx is not None else Matrix.Identity(4)
    return e


def on_bone(arm, root, bone, at, name="holder"):
    """VerrierLook._on_bone: a holder that sits at model-space point `at` (rest pose, no rotation
    relative to the model) and then follows `bone`."""
    arm.data.pose_position = "REST"
    bpy.context.view_layer.update()
    want = root.matrix_world @ (C @ Matrix.Translation(Vector(at)) @ CI)
    e = bpy.data.objects.new(name, None)
    bpy.context.scene.collection.objects.link(e)
    e.parent = arm
    e.parent_type = "BONE"
    e.parent_bone = bone
    b = arm.data.bones[bone]
    e.matrix_parent_inverse = Matrix.Translation((0, -b.length, 0))
    pb = arm.pose.bones[bone]
    bone_world = arm.matrix_world @ pb.matrix
    e.matrix_basis = bone_world.inverted() @ want
    arm.data.pose_position = "POSE"
    bpy.context.view_layer.update()
    return e


def prop(parent, path, length, grip, yaw=0.0, **kw):
    """Behemoth._prop / VerrierLook.held: a 1 m prop sized to `length`, gripped `grip` up its height."""
    m = node(parent, godot_xform((0, (0.5 - grip) * length, 0), (0, math.degrees(yaw), 0), (length,) * 3), "prop")
    scene_under(m, REPO + path if not path.startswith("/") else path, **kw)
    return m


def find_bone(arm, *names):
    for n in names:
        if n in arm.data.bones:
            return n
    low = {b.name.lower(): b.name for b in arm.data.bones}
    for n in names:
        if n.lower() in low:
            return low[n.lower()]
    raise KeyError(names)

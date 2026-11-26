"""Opens a scene .blend, packs every external file into it and saves a copy: pack_blend.py <in> <out>"""
import bpy, sys
src, dst = sys.argv[-2], sys.argv[-1]
bpy.ops.wm.open_mainfile(filepath=src)
missing = [i.name for i in bpy.data.images if i.source == "FILE" and not i.packed_file and not i.has_data and not __import__("os").path.exists(bpy.path.abspath(i.filepath))]
bpy.ops.file.pack_all()
bpy.ops.wm.save_as_mainfile(filepath=dst, compress=True, copy=True)
print("packed", dst, "images", len(bpy.data.images), "missing", missing)

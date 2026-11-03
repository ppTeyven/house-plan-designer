"""核查 GLB 导入 Blender 后：材质是否保留、是否分配到网格、颜色是否还在。"""
import bpy, os, sys

path = os.environ.get("BL_IN")
bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete(use_global=False)
bpy.ops.import_scene.gltf(filepath=path)

print("materials in file:", len(bpy.data.materials))
for m in bpy.data.materials:
    bc = "-"
    if m.use_nodes:
        b = m.node_tree.nodes.get("Principled BSDF")
        if b and "Base Color" in b.inputs:
            v = b.inputs["Base Color"].default_value
            bc = f"({v[0]:.3f},{v[1]:.3f},{v[2]:.3f})"
    print(f"  MAT {m.name:<18} base={bc} users={m.users}")

print("--- mesh -> material assignment ---")
nomesh = 0
for o in bpy.context.scene.objects:
    if o.type != 'MESH':
        continue
    noms = [m.name if m else None for m in o.data.materials]
    if not noms:
        nomesh += 1
    if o.name.startswith(("pillow", "seat_0", "base")):
        print(f"  {o.name:<18} mats={noms}")
print("meshes without material:", nomesh)
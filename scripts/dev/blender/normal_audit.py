"""法线方向统计 —— 定量回答"面到底朝哪"，不再靠目视渲染图猜。

用法：
  blender --background --python normal_audit.py -- <glb> [name_prefix]
"""
import bpy
import sys
import bmesh

args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
GLB = args[0]
PREFIX = args[1] if len(args) > 1 else ""

bpy.ops.import_scene.gltf(filepath=GLB)
bpy.context.view_layer.update()

for o in list(bpy.context.scene.objects):
    if o.type != 'MESH':
        continue
    if PREFIX and not o.name.startswith(PREFIX):
        continue
    me = o.data
    up = dn = 0
    px = nx = py = ny = pz = nz = 0
    for p in me.polygons:
        n = p.normal
        if n.z > 0.3:
            up += 1
        elif n.z < -0.3:
            dn += 1
        if abs(n.x) > 0.7:
            if n.x > 0:
                px += 1
            else:
                nx += 1
        if abs(n.y) > 0.7:
            if n.y > 0:
                py += 1
            else:
                ny += 1
        if abs(n.z) > 0.7:
            if n.z > 0:
                pz += 1
            else:
                nz += 1
    print("AUDIT %-18s faces=%-6d  up=%-5d down=%-5d | +X=%-5d -X=%-5d +Y=%-5d -Y=%-5d +Z=%-5d -Z=%-5d"
          % (o.name, len(me.polygons), up, dn, px, nx, py, ny, pz, nz))

print()
print("=== 翻转 shell 后对比 ===")
for o in list(bpy.context.scene.objects):
    if o.type != 'MESH' or not o.name.startswith('shell'):
        continue
    me = o.data
    bm = bmesh.new()
    bm.from_mesh(me)
    bmesh.ops.reverse_faces(bm, faces=bm.faces)
    bm.to_mesh(me)
    bm.free()
    me.update()
    px = nx = py = ny = pz = nz = 0
    for p in me.polygons:
        n = p.normal
        if abs(n.x) > 0.7:
            if n.x > 0:
                px += 1
            else:
                nx += 1
        if abs(n.y) > 0.7:
            if n.y > 0:
                py += 1
            else:
                ny += 1
        if abs(n.z) > 0.7:
            if n.z > 0:
                pz += 1
            else:
                nz += 1
    print("FLIP  %-18s +X=%-5d -X=%-5d +Y=%-5d -Y=%-5d +Z=%-5d -Z=%-5d"
          % (o.name, px, nx, py, ny, pz, nz))
    break

"""核对抱枕/扶手垫等关键部件的材质与世界坐标包围盒。

【为什么需要】
  渲染图上"看不到抱枕"有两种可能：
    (a) 抱枕根本没生成
    (b) 抱枕生成了但埋进了靠垫/坐垫里，或被别的部件挡住
  光看图分不清，必须查数据。
"""
import bpy
import sys
import os
import mathutils

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import glb_clean

args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
GLB = args[0]
model = glb_clean.import_clean(GLB)
bpy.context.view_layer.update()

print("对象总数: %d" % len(model))
print()
print("%-18s %-22s %8s %8s %8s   %s" % ("名称", "材质", "minX", "maxX", "minZ", "maxZ"))
print("-" * 96)
for o in sorted(model, key=lambda x: x.name):
    if o.type != 'MESH':
        continue
    if not any(k in o.name for k in ('pillow', 'arm_pad', 'seat_0', 'seat_1',
                                      'seat_2', 'backc_0', 'backc_1', 'backc_2',
                                      'shell', 'seat_deck')):
        continue
    mat = o.data.materials[0].name if o.data.materials else "-"
    bb = [o.matrix_world @ mathutils.Vector(c) for c in o.bound_box]
    xs = [p.x for p in bb]
    zs = [p.z for p in bb]
    print("%-18s %-22s %8.3f %8.3f %8.3f   %8.3f"
          % (o.name, mat, min(xs), max(xs), min(zs), max(zs)))

print()
print("=== 材质颜色 ===")
for m in bpy.data.materials:
    if not m.use_nodes:
        continue
    b = m.node_tree.nodes.get("Principled BSDF")
    if not b:
        continue
    c = b.inputs["Base Color"].default_value
    print("  %-24s base=(%.3f, %.3f, %.3f)  rough=%.2f"
          % (m.name, c[0], c[1], c[2], b.inputs["Roughness"].default_value))

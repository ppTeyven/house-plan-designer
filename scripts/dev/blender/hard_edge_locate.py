"""定位硬边的具体位置 —— 查明 180° 折角到底出现在哪。

【为什么要定位】
jaggedness.py 测出：shell 硬边 5.2%、最大折角 180°；
坐垫均边长 24mm、最长边 274mm。
180° 折角 = 两个面完全背对 = 典型的"封盖/底面与侧壁接缝"，
这类硬边在渲染里就是一条生硬的折线 → 用户看到的"锯齿感"。

做法：找出二面角 > 150° 的边，打印其世界坐标，
这样能确认是"封盖接缝"（正常，但要平滑）还是"几何错误"。

用法：blender --background --python hard_edge_locate.py -- <glb> [obj_name]
"""
import bpy
import sys
import os
import math
import bmesh
import mathutils

args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
GLB = args[0]
ONLY = args[1] if len(args) > 1 else None

bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
bpy.ops.import_scene.gltf(filepath=GLB)
bpy.context.view_layer.update()

SKIP = ("pipe", "stitch", "tuft", "leg_cup", "alu_leg", "seam")

print("=" * 90)
print("硬边定位（二面角 > 150° 的边）")
print("=" * 90)

for o in sorted(bpy.context.scene.objects, key=lambda x: x.name):
    if o.type != 'MESH' or not o.data.polygons:
        continue
    if any(k in o.name for k in SKIP):
        continue
    if ONLY and o.name != ONLY:
        continue

    bm = bmesh.new()
    bm.from_mesh(o.data)
    bm.normal_update()

    buckets = {}
    sharp = []
    for e in bm.edges:
        if len(e.link_faces) != 2:
            continue
        deg = math.degrees(e.link_faces[0].normal.angle(e.link_faces[1].normal, 0.0))
        if deg <= 150.0:
            continue
        mid = (e.verts[0].co + e.verts[1].co) * 0.5
        w = o.matrix_world @ mid
        # 按 50mm 网格分桶
        key = (round(w.x / 0.05), round(w.y / 0.05), round(w.z / 0.05))
        buckets.setdefault(key, []).append((deg, w))
        sharp.append((deg, w))

    if not sharp:
        bm.free()
        continue

    sharp.sort(key=lambda t: -t[0])
    print()
    print("%s  硬边数 %d（占全部边 %.1f%%）"
          % (o.name, len(sharp), len(sharp) / max(len(bm.edges), 1) * 100))
    print("  最陡 5 条:")
    for deg, w in sharp[:5]:
        print("     %6.1f°  at (%.3f, %.3f, %.3f)" % (deg, w.x, w.y, w.z))
    print("  聚集区（50mm 网格，列出前 6）:")
    top = sorted(buckets.items(), key=lambda kv: -len(kv[1]))[:6]
    for key, items in top:
        cx = sum(i[1].x for i in items) / len(items)
        cy = sum(i[1].y for i in items) / len(items)
        cz = sum(i[1].z for i in items) / len(items)
        mx = max(i[0] for i in items)
        print("     %3d 条  中心(%.3f, %.3f, %.3f)  最陡 %.0f°"
              % (len(items), cx, cy, cz, mx))
    bm.free()

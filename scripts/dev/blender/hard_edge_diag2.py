"""硬棱检测 —— 区分【真硬棱】与【正常折面】。

【v23 · 判据修正】
早期用 `dot < 0.985` 当硬棱判据，但那是错的：
多边形管的纵向边天然有折角（12 边形 → 30° → dot = 0.866），
用 0.985 会把正常折面全算成硬棱。

正确的三类分开统计：
  ① 【法线反向】dot < -0.85  → 真 bug，渲染出来是黑斑/生硬折线
  ② 【明显折角】30° < 夹角 <= 150° → 几何分辨率不足（可加大 sides/res）
  ③ 【平滑】夹角 <= 30° → 正常

用户说的"锯齿感"= ① + ②，要两个都压下去。

用法：blender --background --python hard_edge_diag2.py -- <glb>
"""
import bpy
import sys
import os
import math
import bmesh

args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
GLB = args[0]
ONLY = args[1] if len(args) > 1 else None

bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
bpy.ops.import_scene.gltf(filepath=GLB)
bpy.context.view_layer.update()

print("=" * 108)
print("硬棱检测（v23 判据：法线反向 / 明显折角 / 平滑）")
print("=" * 108)
print("%-24s %8s %9s %9s %9s %9s %10s" %
      ("对象", "边数", "反向", "反向%", "折角", "折角%", "均边长mm"))
print("-" * 108)

tot_rev = 0
tot_ang = 0
tot_edges = 0

for o in sorted(bpy.context.scene.objects, key=lambda x: x.name):
    if o.type != 'MESH' or not o.data.polygons:
        continue
    if ONLY and o.name != ONLY:
        continue

    bm = bmesh.new()
    bm.from_mesh(o.data)
    bm.normal_update()

    rev = 0
    ang = 0
    edges = 0
    elens = []
    for e in bm.edges:
        if len(e.link_faces) != 2:
            continue
        edges += 1
        elens.append(e.calc_length())
        d = e.link_faces[0].normal.dot(e.link_faces[1].normal)
        if d < -0.85:
            rev += 1
        else:
            deg = math.degrees(math.acos(max(-1.0, min(1.0, d))))
            if deg > 30.0:
                ang += 1

    if edges == 0:
        bm.free()
        continue

    avg = sum(elens) / len(elens) * 1000
    tot_rev += rev
    tot_ang += ang
    tot_edges += edges

    flag = ""
    if rev > 0:
        flag = "  ← 法线反向"
    print("%-24s %8d %9d %8.2f%% %9d %8.2f%% %10.2f%s" %
          (o.name, edges, rev, rev / edges * 100,
           ang, ang / edges * 100, avg, flag))
    bm.free()

print("-" * 108)
print("%-24s %8d %9d %8.2f%% %9d %8.2f%%" %
      ("合计", tot_edges, tot_rev, tot_rev / max(tot_edges, 1) * 100,
       tot_ang, tot_ang / max(tot_edges, 1) * 100))
print()
if tot_rev == 0:
    print("✅ 法线反向硬棱 = 0 —— 无黑斑、无生硬折线")
else:
    print("❌ 仍有 %d 处法线反向" % tot_rev)
if tot_ang / max(tot_edges, 1) < 0.02:
    print("✅ 明显折角占比 < 2% —— 表面已足够圆润")
else:
    print("⚠️  明显折角占比 %.2f%% —— 几何分辨率仍可提高"
          % (tot_ang / max(tot_edges, 1) * 100))

"""诊断"管件残留硬棱"—— 确认是不是"端盖面法线朝向错误"。

【背景】
BFS 局部修复把硬棱从 1089 降到 412，残留全在滚边/针脚管件上
（seat_pipe / arm_pipe / pillow_pipe ...）。这些是【开放的细管】：
两端有封盖（use_fill_caps=True），中间是环状面带。

管件的硬矛盾几乎必然出现在【端盖 vs 侧壁】的接缝：
  · 侧壁绕序由曲线扫掠决定
  · 端盖绕序由 Blender 的 bevel fill 决定
  · 两者可能相反 → 端盖法线朝内 → 与侧壁形成 180° 折线

【验证方法】
对每条冲突边，判断它是否靠近管件【端头】：
  · 找该管件网格中"离路径两端最近"的一圈边
  · 若冲突边集中在这圈 → 端盖问题
  · 若均匀分布在管身 → 扫掠面带问题

同时统计：端盖面（有且仅有一个邻接面边界）的法线朝向分布。

用法：blender --background --python diag_pipe_caps.py -- <glb>
"""
import bpy
import sys
import os
import math
import bmesh

args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
GLB = args[0]

bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
bpy.ops.import_scene.gltf(filepath=GLB)
bpy.context.view_layer.update()

print("=" * 96)
print("管件端盖诊断")
print("=" * 96)
print("%-22s %8s %10s %10s %10s" %
      ("管件", "冲突边", "边界边数", "端盖面数", "端盖朝内"))
print("-" * 96)

for o in sorted(bpy.context.scene.objects, key=lambda x: x.name):
    if o.type != 'MESH' or not o.data.polygons:
        continue
    if not any(k in o.name for k in ("pipe", "stitch", "tuft")):
        continue

    bm = bmesh.new()
    bm.from_mesh(o.data)
    bm.normal_update()

    conflicts = 0
    for e in bm.edges:
        if len(e.link_faces) == 2:
            if e.link_faces[0].normal.dot(e.link_faces[1].normal) < -0.985:
                conflicts += 1

    # 边界边（只有 1 个邻面）= 管件端口
    boundary = [e for e in bm.edges if len(e.link_faces) == 1]
    # 端盖面：所有边都是边界边的面
    caps = []
    for f in bm.faces:
        if all(len(e.link_faces) == 1 for e in f.edges):
            caps.append(f)

    # 端盖"朝内"判定：面心相对网格中心的方向 vs 法线
    if caps:
        cen = bmesh.ops.calc_center_median(bm, faces=bm.faces)["cent"]
        inward = 0
        for f in caps:
            c = f.calc_center_median()
            radial = c - cen
            if radial.length > 1e-6 and f.normal.dot(radial.normalized()) < 0:
                inward += 1
    else:
        inward = 0

    print("%-22s %8d %10d %10d %10d"
          % (o.name, conflicts, len(boundary), len(caps), inward))
    bm.free()

"""直接测 pipe_on_surface —— 定位滚边管件硬棱的真正成因。

【背景】
diag_export_tri.py 证明：导出三角化不是责任方（内存里就有）。
diag_bevel_min.py 证明：简单直管/圆弧管没有硬棱（0 处）。
但真实沙发里的滚边有 373 处。

两者差异：真实滚边走的是 pipe_on_surface() —— 
把路径逐点【投射到软包曲面】上，沿曲面法线抬升。

【怀疑】
投射后相邻采样点可能：
  ① 位置重合（曲面在平面区法线几乎不变）
  ② 顺序颠倒（法线乱转导致路径自交）
  ③ 出现极短段 → bevel 产生退化几何

【测试】
对真实软包件（soft_slab 生成的坐垫）做 pipe_on_surface，
然后检查：
  · 投射后路径的相邻点距离分布
  · 生成的 curve 转网格后的硬棱数
  · 与"未投射的平面路径"对照

用法：blender --background --python diag_pipe_on_surface.py
"""
import bpy
import sys
import os
import math
import bmesh

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bl_lib as B

print("=" * 92)
print("pipe_on_surface 成因诊断")
print("=" * 92)

B.wipe()

# 造一个坐垫软包
cushion = B.soft_slab("cush", (0.589, 0.52, 0.14), (0, 0, 0.35),
                      res_u=96, res_v=40)
bpy.context.view_layer.update()


def count_rev(ob):
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bm.normal_update()
    n = 0
    for e in bm.edges:
        if len(e.link_faces) == 2:
            if e.link_faces[0].normal.dot(e.link_faces[1].normal) < -0.985:
                n += 1
    bm.free()
    return n


def path_stats(pts, label):
    ds = [(pts[i + 1][0] - pts[i][0],
           pts[i + 1][1] - pts[i][1],
           pts[i + 1][2] - pts[i][2]) for i in range(len(pts) - 1)]
    lens = [math.sqrt(d[0] ** 2 + d[1] ** 2 + d[2] ** 2) for d in ds]
    lens_sorted = sorted(lens)
    print("  %-22s 点数 %4d  最短 %8.4fmm  中位 %7.3fmm  最长 %8.3fmm  "
          "<0.4mm: %d" %
          (label, len(pts), lens_sorted[0] * 1000,
           lens_sorted[len(lens) // 2] * 1000, lens_sorted[-1] * 1000,
           sum(1 for x in lens if x < 0.0004)))
    return lens


# ① 平面矩形路径（不做投射）
rect = [(-0.25, -0.2, 0.40), (0.25, -0.2, 0.40),
        (0.25, 0.2, 0.40), (-0.25, 0.2, 0.40)]
path_stats(rect, "平面矩形路径")

ob1 = B.pipe_path("flat_pipe", rect, None, r=0.0055, closed=True)
bpy.ops.object.select_all(action='DESELECT')
ob1.select_set(True)
bpy.context.view_layer.objects.active = ob1
bpy.ops.object.convert(target='MESH')
m1 = bpy.context.view_layer.objects.active
print("  平面路径 → 网格 硬棱 %d (面数 %d)" % (count_rev(m1), len(m1.data.polygons)))

# ② pipe_on_surface（投射到坐垫顶面）
print()
path = [(-0.25, -0.2, 0.45), (0.25, -0.2, 0.45),
        (0.25, 0.2, 0.45), (-0.25, 0.2, 0.45)]
ob2 = B.pipe_on_surface("surf_pipe", path, cushion, None, r=0.0055)
bpy.ops.object.select_all(action='DESELECT')
ob2.select_set(True)
bpy.context.view_layer.objects.active = ob2
bpy.ops.object.convert(target='MESH')
m2 = bpy.context.view_layer.objects.active
print("  投射路径 → 网格 硬棱 %d (面数 %d)" % (count_rev(m2), len(m2.data.polygons)))

# ③ 检查投射后的实际点（重建同样的流程）
from mathutils.bvhtree import BVHTree
bm = bmesh.new()
bm.from_mesh(cushion.data)
bvh = BVHTree.FromBMesh(bm)
bm.free()
dense = B._catmull_rom(path, samples_per_seg=10)
lifted = []
for p in dense:
    hit = bvh.find_nearest(p)
    if hit and hit[0] is not None:
        pos, nor = hit[0], hit[1]
        lifted.append((pos.x + nor.x * 0.0025,
                       pos.y + nor.y * 0.0025,
                       pos.z + nor.z * 0.0025))
path_stats(lifted, "投射后路径(未去重)")

dedup = [lifted[0]]
for p in lifted[1:]:
    if math.dist(dedup[-1], p) >= 0.0004:
        dedup.append(p)
path_stats(dedup, "投射后路径(去重后)")

ob3 = B.pipe_path("surf_pipe2", dedup, None, r=0.0055, closed=True)
bpy.ops.object.select_all(action='DESELECT')
ob3.select_set(True)
bpy.context.view_layer.objects.active = ob3
bpy.ops.object.convert(target='MESH')
m3 = bpy.context.view_layer.objects.active
print("  去重后 → 网格 硬棱 %d (面数 %d)" % (count_rev(m3), len(m3.data.polygons)))

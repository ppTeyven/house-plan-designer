"""最小复现 —— Blender curve bevel 转网格是否自带法线硬棱？

【为什么做最小复现】
管件（滚边/针脚）的硬棱已经排除：
  ✗ 曲线路径重复点（diag_curve_dup.py 证实 0 条零长段）
  ✗ 端盖绕序（diag_pipe_caps.py 证实 0 个端盖面）
  ✓ 冲突面全是三角形、顶点间距 ~0.2~0.7mm

那么剩下的唯一嫌疑是【Blender 的 bevel→mesh 转换本身】。
如果一根最简单的直管（4 个点、bevel_depth=r）转网格后就有硬棱，
说明这是 Blender 导出/转换的行为，需要在【转换后】统一修复，
而不是在建模代码里找原因。

【测试矩阵】
  1. 直管 4 点
  2. 直管 2 点
  3. 折线 3 点（尖角）
  4. 不同 bevel_resolution（0 / 2 / 4 / 6）
  5. use_fill_caps 开/关

每项测：转换后网格的硬棱数（dot < -0.985 的相邻边）
以及 recalc_face_normals 之后是否恢复。

用法：blender --background --python diag_bevel_min.py
"""
import bpy
import sys
import os
import math
import bmesh

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bl_lib as B


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


def count_rev_after_recalc(ob):
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(ob.data)
    ob.data.update()
    bm.free()
    return count_rev(ob)


def make_pipe(name, pts, r=0.0055, bevel_res=4, caps=True):
    cu = bpy.data.curves.new(name + "_cv", type='CURVE')
    cu.dimensions = '3D'
    cu.resolution_u = 12
    cu.bevel_depth = r
    cu.bevel_resolution = bevel_res
    cu.use_fill_caps = caps
    sp = cu.splines.new('POLY')
    sp.points.add(len(pts) - 1)
    for i, p in enumerate(pts):
        sp.points[i].co = (p[0], p[1], p[2], 1.0)
    ob = bpy.data.objects.new(name, cu)
    bpy.context.collection.objects.link(ob)
    return ob


def convert(ob):
    bpy.ops.object.select_all(action='DESELECT')
    ob.select_set(True)
    bpy.context.view_layer.objects.active = ob
    bpy.ops.object.convert(target='MESH')
    return bpy.context.view_layer.objects.active


print("=" * 100)
print("Blender curve bevel → mesh 最小复现")
print("=" * 100)
print("%-34s %7s %9s %9s %9s" %
      ("用例", "面数", "硬棱", "recalc后", "端盖数"))
print("-" * 100)

CASES = [
    ("直管4点 res=4 caps=on", [(0, 0, 0), (0.1, 0, 0), (0.2, 0, 0), (0.3, 0, 0)], 4, True),
    ("直管2点 res=4 caps=on", [(0, 0, 0), (0.3, 0, 0)], 4, True),
    ("直管4点 res=4 caps=off", [(0, 0, 0), (0.1, 0, 0), (0.2, 0, 0), (0.3, 0, 0)], 4, False),
    ("直管4点 res=0 caps=on", [(0, 0, 0), (0.1, 0, 0), (0.2, 0, 0), (0.3, 0, 0)], 0, True),
    ("直管4点 res=2 caps=on", [(0, 0, 0), (0.1, 0, 0), (0.2, 0, 0), (0.3, 0, 0)], 2, True),
    ("直管4点 res=6 caps=on", [(0, 0, 0), (0.1, 0, 0), (0.2, 0, 0), (0.3, 0, 0)], 6, True),
    ("折线3点 res=4 caps=on", [(0, 0, 0), (0.15, 0, 0), (0.3, 0.1, 0)], 4, True),
]

for tag, pts, bres, caps in CASES:
    B.wipe()
    ob = make_pipe("t", pts, bevel_res=bres, caps=caps)
    me = convert(ob)
    nf = len(me.data.polygons)
    rev = count_rev(me)
    rev2 = count_rev_after_recalc(me)
    bm = bmesh.new()
    bm.from_mesh(me.data)
    caps_n = sum(1 for f in bm.faces
                 if all(len(e.link_faces) == 1 for e in f.edges))
    bm.free()
    print("%-34s %7d %9d %9d %9d" % (tag, nf, rev, rev2, caps_n))

print()
print("结论：若『直管』这种最简单的情况也有硬棱 → 是 Blender bevel 转换的行为，")
print("      必须在转换后统一修复；不能指望改建模参数。")

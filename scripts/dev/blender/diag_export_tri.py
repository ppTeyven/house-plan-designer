"""决定性测试 —— 滚边管件的硬棱是【几何 bug】还是【GLB 导出 bug】？

【背景】
BFS 修复后沙发还剩 373 处法线反向硬棱，全部集中在滚边管件上
（seat_pipe / arm_pipe / pillow_pipe / backc_pipe / seat_seam_pipe）。

两种可能：
  ① Blender 内存里的网格就有问题 → 建模代码/curve bevel 的锅
  ② Blender 内存里正常，导出 GLB 后才出现 → glTF 三角化的锅
     （glTF 只支持三角形，非平面四边形被三角化时可能产生翻转/退化三角形）

【测试】
同一根管子：
  1. 在内存里测硬棱
  2. 导出 GLB
  3. 重新导入测硬棱
  对比 → 直接定位责任方

同时测：导出前加不加 triangulate（导出器默认会三角化）

用法：blender --background --python diag_export_tri.py
"""
import bpy
import sys
import os
import math
import bmesh
import tempfile

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


def export_glb(ob, path):
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.export_scene.gltf(filepath=path, export_format='GLB',
                              export_materials='EXPORT', use_selection=True,
                              export_apply=True)


def import_glb(path):
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    bpy.ops.import_scene.gltf(filepath=path)
    bpy.context.view_layer.update()
    return [o for o in bpy.context.scene.objects if o.type == 'MESH' and o.data.polygons]


tmpdir = tempfile.mkdtemp()

print("=" * 92)
print("导出三角化是否是管件硬棱的责任方")
print("=" * 92)
print("%-40s %10s %10s %10s" % ("用例", "内存硬棱", "GLB后", "面数变化"))
print("-" * 92)

# 用真实的曲线路径形状（螺旋/转折），更容易触发
CASES = [
    ("直管4点", [(0, 0, 0), (0.1, 0, 0), (0.2, 0, 0), (0.3, 0, 0)], 4, True),
    ("直管4点 caps=off", [(0, 0, 0), (0.1, 0, 0), (0.2, 0, 0), (0.3, 0, 0)], 4, False),
    ("圆弧12点", [(0.3 * math.cos(a), 0.3 * math.sin(a), 0)
                  for a in [i * math.pi / 6 for i in range(12)]], 4, True),
    ("圆弧12点 caps=off", [(0.3 * math.cos(a), 0.3 * math.sin(a), 0)
                           for a in [i * math.pi / 6 for i in range(12)]], 4, False),
    ("圆弧12点 res=2", [(0.3 * math.cos(a), 0.3 * math.sin(a), 0)
                        for a in [i * math.pi / 6 for i in range(12)]], 2, True),
]

for tag, pts, bres, caps in CASES:
    B.wipe()
    ob = make_pipe("t", pts, bevel_res=bres, caps=caps)
    me = convert(ob)
    before = count_rev(me)
    nf_before = len(me.data.polygons)
    p = os.path.join(tmpdir, "t.glb")
    export_glb(me, p)
    objs = import_glb(p)
    after = sum(count_rev(o) for o in objs)
    nf_after = sum(len(o.data.polygons) for o in objs)
    print("%-40s %10d %10d %10s" %
          (tag, before, after, "%d→%d" % (nf_before, nf_after)))

print()
print("判读：")
print("  内存=0 且 GLB>0  → 【导出三角化 bug】→ 在导出前用 triangulate 修好")
print("  内存>0           → 【建模/curve bevel bug】→ 改生成逻辑")
print("  两边都>0         → 两者都有问题")

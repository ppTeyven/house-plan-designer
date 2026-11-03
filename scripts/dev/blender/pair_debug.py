"""查明 arm_pad_L ↔ arm_pad_R / arm_pad ↔ seat 穿模的真相。

【为什么要查】
  穿模检测报 "arm_pad_L ↔ arm_pad_R 穿入 9.7% 顶点, 最深 275mm"，
  但两者横向相距 1.78m（扶手垫 x: -1.131..-0.889 vs 0.889..1.131），
  物理上不可能相交 → 这仍是误报。
  同时 "arm_pad_R ↔ seat 穿入 36%" 需要确认是真穿模还是检测口径问题。

做法：
  1. 打印两部件的 AABB
  2. 找出真正"穿入"的具体顶点坐标（世界坐标）
  3. 对这些顶点，看它到对方 AABB 的最近距离
  → 如果顶点根本不在对方 AABB 内，说明检测口径有 bug。
"""
import bpy
import sys
import os
import mathutils

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import glb_clean

args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
GLB = args[0]
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
model = glb_clean.import_clean(GLB)
bpy.context.view_layer.update()

byname = {o.name: o for o in model}


def aabb(o):
    pts = [o.matrix_world @ mathutils.Vector(c) for c in o.bound_box]
    return ([min(p[i] for p in pts) for i in range(3)],
            [max(p[i] for p in pts) for i in range(3)])


PAIRS = [("arm_pad_L", "arm_pad_R"), ("arm_pad_R", "seat_1"), ("arm_pad_R", "seat_2"),
         ("backc_0", "seat_0"), ("backc_1", "seat_1"), ("backc_2", "seat_2"),
         ("backc_0", "seat_1"), ("backc_1", "seat_2")]

for an, bn in PAIRS:
    A = byname.get(an)
    B = byname.get(bn)
    if not A or not B:
        print("MISS %s / %s" % (an, bn))
        continue
    amin, amax = aabb(A)
    bmin, bmax = aabb(B)
    print("=" * 78)
    print("%s  AABB x[%.3f %.3f] y[%.3f %.3f] z[%.3f %.3f]"
          % (an, amin[0], amax[0], amin[1], amax[1], amin[2], amax[2]))
    print("%s  AABB x[%.3f %.3f] y[%.3f %.3f] z[%.3f %.3f]"
          % (bn, bmin[0], bmax[0], bmin[1], bmax[1], bmin[2], bmax[2]))

    # AABB 是否重叠
    ov = [min(amax[i], bmax[i]) - max(amin[i], bmin[i]) for i in range(3)]
    print("AABB 重叠量: x=%.4f y=%.4f z=%.4f" % tuple(ov))

    # 找出 A 中落在 B 的 AABB 内的顶点
    inside = []
    for v in A.data.vertices:
        p = A.matrix_world @ v.co
        if all(bmin[i] - 1e-4 <= p[i] <= bmax[i] + 1e-4 for i in range(3)):
            inside.append(p)
    print("A 的顶点落在 B 的 AABB 内: %d / %d" % (len(inside), len(A.data.vertices)))
    if inside:
        for p in inside[:6]:
            print("   顶点 (%.3f, %.3f, %.3f)" % (p.x, p.y, p.z))

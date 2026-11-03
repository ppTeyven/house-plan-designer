"""顶面高度剖面测量 —— 定量回答"坐垫顶面平不平、缝有多大"。

【为什么需要】
  "坐垫有 3 个突起""坐垫之间有缝"这类问题，
  靠渲染图目视判断会被透视和光照带偏。
  这里沿 X / Y 打【高度剖面】：每隔一小步向下打射线，
  记录每一步命中点的 z 值，得到顶面轮廓线，
  于是：突起多高、缝多宽，全部是数字。

用法：
  blender --background --python profile_probe.py -- <glb> [prefix]
"""
import bpy
import sys
import os
import mathutils
from mathutils.bvhtree import BVHTree
import bmesh

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import glb_clean

args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
GLB = args[0]
PREFIX = args[1] if len(args) > 1 else "seat_"

model = glb_clean.import_clean(GLB)
bpy.context.view_layer.update()

targets = [o for o in model if o.name.startswith(PREFIX)]
# 【重要】排除"纯装饰件"（滚边/针脚/绗缝纽扣）。
#   这些是贴在布面上的细管/线，不构成可坐表面，
#   包含进来会把"顶面轮廓"判高（管半径抬高 5~10mm）。
#
#   【不要排除 seam（压缝条）】
#   v22 踩坑：曾经把 'seat_seam_0' 一起排除，
#   结果射线从坐垫间的 4mm 细缝直接穿到座板（z=0.169），
#   误判成"300mm 深的沟"。压缝条正是用来填这个缝的，必须计入。
EXCLUDE = ('pipe', 'stitch', 'tuft')
targets = [o for o in targets
           if not any(k in o.name for k in EXCLUDE)]
print("=== 顶面高度剖面（%s）===" % PREFIX)
print("对象:", ", ".join(o.name for o in targets))

# 建立 BVH
trees = []
for o in targets:
    dg = bpy.context.evaluated_depsgraph_get()
    me = o.evaluated_get(dg).to_mesh()
    bm = bmesh.new()
    bm.from_mesh(me)
    trees.append((o.name, BVHTree.FromBMesh(bm)))
    bm.free()
    o.evaluated_get(dg).to_mesh_clear()


def top_at(x, y):
    """从 z=1.2 往下打射线，返回命中的最高 z。"""
    org = mathutils.Vector((x, y, 1.20))
    d = mathutils.Vector((0, 0, -1))
    best = None
    for nm, tree in trees:
        loc, nor, idx, dist = tree.ray_cast(org, d)
        if loc is None:
            continue
        if best is None or loc.z > best:
            best = loc.z
    return best


print()
print("[A] 沿 X 扫过整个座面 (y=0.05, 距地面)")
Y = 0.05
step = 0.01
x = -0.95
prev = None
prof = []
while x <= 0.95:
    z = top_at(x, Y)
    prof.append((x, z))
    x += step

# 打印剖面（每 4cm 一个点）+ 自动找出局部凸起与凹陷
print("  x      z(mm)")
for i in range(0, len(prof), 4):
    xx, zz = prof[i]
    bar = "#" * int(max(0, (zz - 0.30)) * 400) if zz else ""
    print("  %+.3f  %s" % (xx, ("%.1f" % (zz * 1000)) if zz else "  --  "))

print()
print("[B] 起伏分析（相邻点差 > 3mm 视为突变）")
ups = downs = 0
max_rise = 0.0
for i in range(1, len(prof)):
    a, b = prof[i - 1][1], prof[i][1]
    if a is None or b is None:
        continue
    d = (b - a) * 1000
    if d > 3:
        ups += 1
        max_rise = max(max_rise, d)
    elif d < -3:
        downs += 1
print("  上升段(>3mm): %d   下降段(>3mm): %d   单段最大上升: %.1fmm"
      % (ups, downs, max_rise))

zs = [z for _, z in prof if z is not None]
if zs:
    print("  顶面 z 范围: %.1f ~ %.1f mm  (起伏 %.1f mm)"
          % (min(zs) * 1000, max(zs) * 1000, (max(zs) - min(zs)) * 1000))

print()
print("[C] 缝隙检测（顶面下凹超过 12mm 记为缝）")
gaps = []
in_gap = False
gs = ge = 0.0
for xx, zz in prof:
    if zz is None:
        continue
    if zz < 0.408:
        if not in_gap:
            in_gap = True
            gs = xx
        ge = xx
    else:
        if in_gap:
            gaps.append((gs, ge))
            in_gap = False
if in_gap:
    gaps.append((gs, ge))
for gs, ge in gaps:
    print("  缝: x %+.3f ~ %+.3f  宽 %.1f mm" % (gs, ge, (ge - gs) * 1000))
if not gaps:
    print("  未检测到明显缝隙")

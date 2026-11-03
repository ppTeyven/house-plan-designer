"""验证顺序单调投射是否消除了滚边自交 + 法线反向。

【对比】
  A. 旧：每点独立 find_nearest → 自交 7484 对，法线反向 10250
  B. 新：顺序单调投射 → ？

用法：blender --background --python diag_monotone.py
"""
import bpy
import sys
import os
import math
import bmesh
import mathutils

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bl_lib as B
from mathutils.bvhtree import BVHTree


def rev_count(ob, thresh=-0.85):
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bm.normal_update()
    n = 0
    worst = 1.0
    for e in bm.edges:
        if len(e.link_faces) == 2:
            d = e.link_faces[0].normal.dot(e.link_faces[1].normal)
            if d < thresh:
                n += 1
            worst = min(worst, d)
    bm.free()
    return n, worst


def self_intersect(pts, r, min_gap=8):
    """检测中心线自交。

    【重要 · 判据修正】
    早期版本用"任意两点的距离 < 2r"当自交 —— 这是错的！
    管子是连续的，相邻采样点间距（~1mm）本来就远小于管径（20mm），
    必然"相交"。这属于误报。

    真正的自交 = 【空间上远离的两段】互相穿过。
    正确判据：只看索引间隔 > min_gap 的点对，
    它们的距离仍 < 2r → 才是真的自交。
    """
    N = len(pts)
    hits = 0
    worst = 1e9
    for i in range(N):
        for j in range(i + min_gap, N):
            d = (pts[i] - pts[j]).length
            if d < 2 * r:
                hits += 1
                worst = min(worst, d)
    return hits, worst


B.wipe()

SEAT_W, SEAT_D, SEAT_T = 0.589, 0.52, 0.14
SEAT_TOP = 0.421
cush = B.soft_slab("cush", (SEAT_W, SEAT_D, SEAT_T), (0, 0, 0.35),
                    res_u=96, res_v=40)
bpy.context.view_layer.update()

pts = []
for i in range(89):
    a = 2 * math.pi * i / 88
    cs, sn = math.cos(a), math.sin(a)
    px = (SEAT_W / 2 - 0.016) * math.copysign(abs(cs) ** 0.62, cs)
    py = (SEAT_D / 2 - 0.016) * math.copysign(abs(sn) ** 0.62, sn)
    pts.append((px, py, SEAT_TOP - 0.020))

print("=" * 92)
print("顺序单调投射验证")
print("=" * 92)

# 旧方式（独立投射）
bm = bmesh.new()
bm.from_mesh(cush.data)
bvh = BVHTree.FromBMesh(bm)
bm.free()
dense = B._catmull_rom(pts, samples_per_seg=10)
old = []
for p in dense:
    hit = bvh.find_nearest(mathutils.Vector(p))
    if hit and hit[0] is not None:
        pos, nor = hit[0], hit[1]
        old.append(mathutils.Vector((pos.x + nor.x * 0.0036,
                                    pos.y + nor.y * 0.0036,
                                    pos.z + nor.z * 0.0036)))
hits_old, worst_old = self_intersect(old, 0.010)
print("旧（独立投射）: 自交 %d 对  最近 %.2fmm" % (hits_old, worst_old * 1000))
ob_old = B.pipe_mesh("old", old, None, r=0.010, closed=True, sides=20)
n_old, d_old = rev_count(ob_old)
print("              法线反向 %d  最小dot %.4f" % (n_old, d_old))

# 新方式（pipe_on_surface 内置的顺序单调）
print()
ob_new = B.pipe_on_surface("new", pts, cush, None, r=0.010, lift=0.0036)
n_new, d_new = rev_count(ob_new)
print("新（顺序单调）: 法线反向 %d  最小dot %.4f  面数 %d"
      % (n_new, d_new, len(ob_new.data.polygons)))

# 从新网格反推中心线，做自交检查
bm2 = bmesh.new()
bm2.from_mesh(ob_new.data)
bm2.verts.ensure_lookup_table()
nring = 0
pts_new = []
for vi in range(0, len(bm2.verts), 20):
    nring += 1
    pts_new.append(bm2.verts[vi].co.copy())
bm2.free()
hits_new, worst_new = self_intersect(pts_new, 0.010)
print("              自交 %d 对  最近 %.2fmm  环数 %d"
      % (hits_new, worst_new * 1000, nring))

print()
print("判读：")
print("  自交 %d → %d   法线反向 %d → %d" %
      (hits_old, hits_new, n_old, n_new))

# 【真判据】相邻环的间距 vs 管径 —— 若段长远小于管径，
# 说明采样过密（不是 bug，只是浪费面数）；若某处间距突然暴涨 → 路径跳变。
bm3 = bmesh.new()
bm3.from_mesh(ob_new.data)
bm3.verts.ensure_lookup_table()
segs = []
for vi in range(0, len(bm3.verts), 20):
    segs.append(bm3.verts[vi].co.copy())
bm3.free()
dists = [(segs[i + 1] - segs[i]).length for i in range(len(segs) - 1)]
dists_sorted = sorted(dists)
print()
print("  相邻环间距: 最小 %.2fmm  中位 %.2fmm  最大 %.2fmm  (管径 20mm)"
      % (dists_sorted[0] * 1000, dists_sorted[len(dists) // 2] * 1000,
         dists_sorted[-1] * 1000))
jump = [(i, d) for i, d in enumerate(dists) if d > dists_sorted[len(dists) // 2] * 6]
print("  异常跳变点: %d" % len(jump))

if n_new == 0 and hits_new == 0:
    print("✅ 完全解决")
elif n_new < n_old / 10:
    print("✅ 大幅改善")
else:
    print("⚠️  仍需继续")

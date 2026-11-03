"""验证 pipe_on_surface 在真实曲面上生成的管是否【自交】。

【关键推理】
pipe_mesh 单独测试：内存 0 反向，导出 0 反向 ✔
但真实沙发里：导出后 10250 反向 ✘

唯一区别：真实路径是 pipe_on_surface 投射到【软包曲面】后的结果。
若路径在某些地方【自交】（管子穿过自己）或【急剧折返】，
平行传输的上方向参考会失效 → 某些环的截面翻转 → 法线反向。

【自交检测】
对管轴中心线检查：
  · 相邻较远的环之间，距离是否 < 2r（管子必然交叠）
  · 切向是否急剧变化（折返）

【测试】
用真实 soft_slab 坐垫 + 真实滚边路径做 pipe_on_surface，
检查：
  ① 投射后路径的自交情况
  ② 生成的 pipe_mesh 的法线反向数
  ③ 与"人工构造的简单路径"对照

用法：blender --background --python diag_real_pipe.py
"""
import bpy
import sys
import os
import math
import bmesh
import mathutils

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bl_lib as B


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


def self_intersect(pts, r):
    """检测中心线自交：间隔 k 的两环距离 < 2r"""
    N = len(pts)
    hits = 0
    worst = 1e9
    for i in range(N):
        for j in range(i + 3, N):
            d = (pts[i] - pts[j]).length
            if d < 2 * r:
                hits += 1
                worst = min(worst, d)
    return hits, worst


B.wipe()

print("=" * 92)
print("真实曲面滚边：自交 + 法线诊断")
print("=" * 92)

# 造一个真实坐垫
SEAT_W, SEAT_D, SEAT_T = 0.589, 0.52, 0.14
SEAT_TOP = 0.421
cush = B.soft_slab("cush", (SEAT_W, SEAT_D, SEAT_T), (0, 0, 0.35),
                    res_u=96, res_v=40)
bpy.context.view_layer.update()

# 真实滚边路径（照抄 make_sofa_v18.py 的写法）
pts = []
for i in range(89):
    a = 2 * math.pi * i / 88
    cs, sn = math.cos(a), math.sin(a)
    px = (SEAT_W / 2 - 0.016) * math.copysign(abs(cs) ** 0.62, cs)
    py = (SEAT_D / 2 - 0.016) * math.copysign(abs(sn) ** 0.62, sn)
    pts.append((px, py, SEAT_TOP - 0.020))

print("\n--- 原路径（平面矩形环）---")
hits, worst = self_intersect([mathutils.Vector(p) for p in pts], 0.010)
print("  自交对 %d  最近距离 %.2fmm" % (hits, worst * 1000))

# 投射
ob = B.pipe_on_surface("p", pts, cush, None, r=0.010, lift=0.0036)
# 取回路径（从 curve 或 mesh 反推）—— pipe_on_surface 现在返回 mesh
print("\n--- pipe_on_surface 结果 ---")
n, worstdot = rev_count(ob)
print("  法线反向 %d   最小 dot %.4f   面数 %d"
      % (n, worstdot, len(ob.data.polygons)))

# 手动重建投射路径，检测自交
from mathutils.bvhtree import BVHTree
bm = bmesh.new()
bm.from_mesh(cush.data)
bvh = BVHTree.FromBMesh(bm)
bm.free()
dense = B._catmull_rom(pts, samples_per_seg=10)
lifted = []
for p in dense:
    hit = bvh.find_nearest(p)
    if hit and hit[0] is not None:
        pos, nor = hit[0], hit[1]
        lifted.append(mathutils.Vector(
            (pos.x + nor.x * 0.0036, pos.y + nor.y * 0.0036, pos.z + nor.z * 0.0036)))
hits, worst = self_intersect(lifted, 0.010)
print("  投射后路径点数 %d" % len(lifted))
print("  自交对 %d  最近距离 %.2fmm" % (hits, worst * 1000))

# 切向急剧变化检测
max_turn = 0
for i in range(1, len(lifted) - 1):
    t0 = (lifted[i] - lifted[i - 1]).normalized()
    t1 = (lifted[i + 1] - lifted[i]).normalized()
    max_turn = max(max_turn, math.degrees(t0.angle(t1)))
print("  最大切向转折 %.1f°" % max_turn)

# 直接用投射路径生成管
ob2 = B.pipe_mesh("p2", lifted, None, r=0.010, closed=True, sides=20)
n2, w2 = rev_count(ob2)
print("\n--- 直接用投射路径生成管 ---")
print("  法线反向 %d   最小 dot %.4f" % (n2, w2))

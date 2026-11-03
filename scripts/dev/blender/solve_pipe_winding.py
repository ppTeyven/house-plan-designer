"""数值求出 pipe_mesh 的正确三角形绕序 —— 不再手推。

【为什么】
手推绕序错了两次。改用数值验证：对每个候选绕序，
直接算出三角形法线，看它是否与"从轴心指向三角形重心"的方向一致。
外法线 = 离心方向 → 这就是正确绕序。

【方法】
对每个三角形 (v0,v1,v2)：
  centroid = (v0+v1+v2)/3
  axis_pt = 该环截面的中心点
  outward = centroid - axis_pt
  n = (v1-v0) × (v2-v0)
  若 n·outward > 0 → 该绕序正确（法线朝外）

然后用这个判据反推正确的顶点顺序。

用法：blender --background --python solve_pipe_winding.py
"""
import bpy
import sys
import os
import math
import mathutils

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bl_lib as B


def analyse(pts, closed, r=0.0055, sides=12):
    P = [mathutils.Vector(p) for p in pts]
    N = len(P)
    if closed and (P[0] - P[-1]).length < 0.0004:
        P = P[:-1]
        N = len(P)

    # 切向
    tangents = []
    for i in range(N):
        if closed:
            t = P[(i + 1) % N] - P[(i - 1) % N]
        elif i == 0:
            t = P[1] - P[0]
        elif i == N - 1:
            t = P[-1] - P[-2]
        else:
            t = P[i + 1] - P[i - 1]
        tangents.append(t.normalized())

    # up 参考
    ups = []
    ref = mathutils.Vector((0, 0, 1))
    for i in range(N):
        t = tangents[i]
        if abs(t.dot(ref)) > 0.95:
            ref = mathutils.Vector((0, 1, 0))
        n = ref - t * ref.dot(t)
        n.normalize()
        ups.append(n)

    # 顶点
    verts = []
    for i in range(N):
        t = tangents[i]
        n = ups[i]
        b = t.cross(n).normalized()
        C = P[i]
        for j in range(sides):
            a = 2.0 * math.pi * j / sides
            off = n * (math.cos(a) * r) + b * (math.sin(a) * r)
            verts.append(C + off)

    # 中心点
    centers = []
    for i in range(N):
        t = tangents[i]
        n = ups[i]
        b = t.cross(n).normalized()
        centers.append(P[i])

    # 判定四个候选绕序
    CAND = {
        "A (a0,b0,b1)": lambda a0, b0, b1, a1: (a0, b0, b1),
        "B (a0,b1,b0)": lambda a0, b0, b1, a1: (a0, b1, b0),
        "C (a0,a1,b1)": lambda a0, b0, b1, a1: (a0, a1, b1),
        "D (a0,b1,a1)": lambda a0, b0, b1, a1: (a0, b1, a1),
    }

    ring_count = N if closed else N - 1
    results = {}
    for tag, fn in CAND.items():
        ok = 0
        total = 0
        for i in range(ring_count):
            i2 = (i + 1) % N
            for j in range(sides):
                j2 = (j + 1) % sides
                a0 = i * sides + j
                a1 = i * sides + j2
                b0 = i2 * sides + j
                b1 = i2 * sides + j2
                tri = fn(a0, b0, b1, a1)
                v0, v1, v2 = verts[tri[0]], verts[tri[1]], verts[tri[2]]
                nrm = (v1 - v0).cross(v2 - v0)
                if nrm.length < 1e-12:
                    continue
                cen = (v0 + v1 + v2) / 3.0
                # 轴心：用该三角形所属环的中心（近似：取离质心最近的环心）
                outward = (cen - centers[i])
                if outward.length < 1e-12:
                    outward = (cen - centers[i2])
                total += 1
                if nrm.normalized().dot(outward.normalized()) > 0:
                    ok += 1
        results[tag] = (ok, total)

    return results


CASES = [
    ("直管+轴向", [(0, 0, 0), (0, 0, 0.1), (0, 0, 0.2)], False),
    ("直管+X向", [(0, 0, 0), (0.1, 0, 0), (0.2, 0, 0)], False),
    ("闭合环", [(0.3 * math.cos(a), 0.3 * math.sin(a), 0)
                for a in [i * math.pi / 8 for i in range(16)]], True),
]

for tag, pts, closed in CASES:
    print("\n### %s" % tag)
    res = analyse(pts, closed)
    for k, (ok, total) in res.items():
        pct = ok / max(total, 1) * 100
        mark = "  ← 正确" if pct > 99.0 else ""
        print("   %-18s 朝外 %6d/%6d  = %6.2f%%%s" % (k, ok, total, pct, mark))

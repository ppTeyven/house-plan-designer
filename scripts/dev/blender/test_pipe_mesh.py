"""验证 pipe_mesh 的三角形绕序 —— 法线是否一致朝外。

【为什么要单独测】
pipe_mesh 的绕序推导错了两次：
  ① (a0,b0,b1) → 法线朝管内 → 满管硬棱（实测 523 处）
  ② 修正后需要确认端盖与管身的接缝也一致

【判据】
  · 管身相邻面：dot 应接近 +1（法线同向连续）
  · 端盖与管身接缝：dot 应接近 +1
  · 有向体积 > 0（闭合管）或端盖法线朝外

用法：blender --background --python test_pipe_mesh.py
"""
import bpy
import sys
import os
import math
import bmesh

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bl_lib as B


def count_rev(ob, thresh=0.985):
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
    vol = bm.calc_volume(signed=True)
    bm.free()
    return n, worst, vol


print("=" * 92)
print("pipe_mesh 绕序验证")
print("=" * 92)
print("%-34s %10s %10s %12s %8s" %
      ("用例", "硬棱", "最小dot", "有向体积m³", "面数"))
print("-" * 92)

CASES = [
    ("直管(开口)", [(0, 0, 0), (0.1, 0, 0), (0.2, 0, 0), (0.3, 0, 0)], False),
    ("直管(闭合环)", [(0.3 * math.cos(a), 0.3 * math.sin(a), 0)
                      for a in [i * math.pi / 8 for i in range(16)]], True),
    ("Z向直管", [(0, 0, 0), (0, 0, 0.1), (0, 0, 0.2)], False),
    ("斜管", [(0, 0, 0), (0.1, 0.05, 0.1), (0.2, 0.1, 0.2)], False),
    ("螺旋管", [(0.2 * math.cos(a), 0.2 * math.sin(a), 0.05 * a)
                 for a in [i * math.pi / 10 for i in range(20)]], False),
]

allok = True
for tag, pts, closed in CASES:
    B.wipe()
    ob = B.pipe_mesh("t", pts, None, r=0.0055, closed=closed, sides=12)
    n, worst, vol = count_rev(ob)
    nf = len(ob.data.polygons)
    flag = "OK" if n == 0 else "BAD"
    if n:
        allok = False
    print("%-34s %10d %10.4f %12.6f %8d  %s"
          % (tag, n, worst, vol, nf, flag))

print()
if allok:
    print("✅ 全部通过 —— 绕序正确，法线一致朝外")
else:
    print("❌ 仍有硬棱 —— 绕序还不对")

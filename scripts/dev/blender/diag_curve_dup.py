"""追查管件硬棱的【源头】—— 检查曲线路径里是否有零长度/重复点。

【假设】
管件（滚边/针脚）由 Blender 的 curve bevel 转网格得到。
若路径里有【重复点】（相邻两点重合或极近），
bevel 会生成一段【退化管体】：零面积三角形 + 反向重叠面。
这正好对上实测特征：
  · 冲突面全是三角形
  · 顶点平均间距 ~0.2~0.7mm（远小于管半径 5.5mm）
  · 两面法线完全反向（dot = -1.0000）

【检查内容】
对每个 curve 对象：
  ① 相邻点距离分布（有多少 < 0.1mm / < 1mm）
  ② 连续重复点的位置
  ③ Catmull-Rom 重采样后是否产生重复点
     （_catmull_rom 的 ext 端点扩展可能产生零长段）

用法：blender --background --python diag_curve_dup.py
"""
import bpy
import sys
import os
import math

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# ---- 重新走一遍建模流程，拿到【曲线对象】而不是导出的网格 ----
import bl_lib as B

B.wipe()
print("=" * 92)
print("曲线路径重复点检查")
print("=" * 92)
print("%-24s %8s %10s %10s %12s" %
      ("曲线", "点数", "最短段mm", "<0.1mm数", "<1mm数"))
print("-" * 92)

curves = [o for o in bpy.context.scene.objects if o.type == 'CURVE']

# 先做一个最小复现：直接调 _catmull_rom 看它会不会产生重复点
import mathutils
from bl_lib import _catmull_rom

print()
print("--- _catmull_rom 零长段检查（随机路径）---")
import random
rnd = random.Random(7)
bad_total = 0
for trial in range(200):
    n = rnd.randint(3, 20)
    pts = [(rnd.uniform(-1, 1), rnd.uniform(-1, 1), rnd.uniform(-1, 1))
           for _ in range(n)]
    # 制造重复点
    if trial % 3 == 0 and n > 4:
        pts[2] = pts[1]
    out = _catmull_rom(pts, samples_per_seg=10)
    dmin = min((out[i + 1] - out[i]).length for i in range(len(out) - 1))
    if dmin < 1e-5:
        bad_total += 1
print("  200 条随机路径中，产生零长段的：%d 条" % bad_total)

print()
print("--- 实际模型的曲线 ---")
for o in curves:
    pts_all = []
    for sp in o.data.splines:
        if sp.type == 'POLY':
            p = [sp.points[i].co[:3] for i in range(len(sp.points))]
        else:
            p = [(sp.points[i].co.x, sp.points[i].co.y, sp.points[i].co.z)
                 for i in range(len(sp.points))]
        pts_all.extend(p)
    if len(pts_all) < 2:
        continue
    ds = [(mathutils.Vector(pts_all[i + 1]) - mathutils.Vector(pts_all[i])).length
          for i in range(len(pts_all) - 1)]
    dmin = min(ds)
    tiny = sum(1 for d in ds if d < 0.0001)
    small = sum(1 for d in ds if d < 0.001)
    if dmin < 0.002 or tiny or small:
        print("%-24s %8d %10.4f %10d %12d" %
              (o.name, len(pts_all), dmin * 1000, tiny, small))

print()
print("--- 提示 ---")
print("若 _catmull_rom 会产生零长段 → 修它（去重 + 跳过零长）即可根治管件硬棱。")

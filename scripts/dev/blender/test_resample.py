"""单元测试 _resample_by_arclen —— 它到底做了什么？

用法：blender --background --python test_resample.py
"""
import bpy
import sys
import os
import math
import mathutils

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bl_lib as B

print("=" * 88)
print("_resample_by_arclen 单元测试")
print("=" * 88)

# ① 直线 10 点，跨度 1m
P = [mathutils.Vector((i * 0.1, 0, 0)) for i in range(11)]
for seg in (0.5, 0.1, 0.05, 0.02):
    R = B._resample_by_arclen(P, target_seg=seg)
    d = [(R[i + 1] - R[i]).length for i in range(len(R) - 1)]
    print("  直线 target=%.3f → 点数 %3d  实际间距 min %.4f max %.4f"
          % (seg, len(R), min(d), max(d)))

print()
# ② 闭合圆环（首尾重合）
C = [mathutils.Vector((0.3 * math.cos(a), 0.3 * math.sin(a), 0))
     for a in [2 * math.pi * i / 32 for i in range(33)]]
print("  闭合环输入点数 %d" % len(C))
for seg in (0.05, 0.02, 0.01):
    R = B._resample_by_arclen(C, target_seg=seg)
    d = [(R[i + 1] - R[i]).length for i in range(len(R) - 1)]
    closed_gap = (R[-1] - R[0]).length
    print("  闭合环 target=%.3f → 点数 %3d  间距 min %.4f max %.4f  首尾距 %.4f"
          % (seg, len(R), min(d), max(d), closed_gap))

print()
# ③ 圆环弧长
circ = 2 * math.pi * 0.3
print("  圆环周长 %.4f m" % circ)
for seg in (0.05, 0.02, 0.01):
    R = B._resample_by_arclen(C, target_seg=seg)
    print("    target=%.3f → 理论点数 %.0f  实际 %d" % (seg, circ / seg, len(R)))

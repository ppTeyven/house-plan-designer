"""精确定位 shoulder 滚边的取点错误 + 扶手针脚左右不对称。

【已确认的缺陷（来自实测）】
 ① shell_shoulder_pipe_L/R —— 用户说"上方穿过沙发的线"
    实测: x[-1.089..-0.893] y[-0.410..-0.216] z[0.659..0.734]
    → 它悬在扶手顶(0.505)之上 155mm 的空中，横跨在靠背上！
 ② arm_stitch_L 在 x=-0.891(内侧) / arm_stitch_R 在 x=+1.129(外侧)
    → 左右不对称，右边那条浮在壳体外侧（截图里那个小竖条）

本脚本查清 shoulder 的取点到底选了什么。

用法：blender --background --python probe_shoulder.py
"""
import bpy
import sys
import os
import math
import mathutils

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import make_sofa_v18 as MS   # noqa
import sofa_shell as SH

print("=" * 92)
print("① shoulder 取点还原")
print("=" * 92)
PATH = MS.PATH
STATES = MS.STATES
shell_params = MS.shell_params
shell_sects = MS.shell_sects
shell_frames = MS.shell_frames

for tag, s_key in (("L", MS.S_LEFT), ("R", MS.S_RIGHT)):
    best = min(range(len(PATH)), key=lambda i: abs(PATH[i][2] - s_key))
    i = best
    T, zb, zw, zt = shell_params[i]
    _, _, nx, ny = shell_frames[i]
    px, py = PATH[i][0], PATH[i][1]
    print("\n【%s】path index=%d  path s=%.4f  s_key=%.4f" % (tag, i, PATH[i][2], s_key))
    print("   世界位置 (%.3f, %.3f)  断面 T=%.3f zb=%.3f zw=%.3f zt=%.3f"
          % (px, py, T, zb, zw, zt))
    sel = [(a, b) for (a, b) in shell_sects[i] if abs(b - zw) < 0.03]
    print("   断面点总数 %d, 选中(|b-zw|<0.03) %d 个:" % (len(shell_sects[i]), len(sel)))
    for (a, b) in sel:
        print("      a=%+8.4f b=%8.4f  →  世界 (%.3f, %.3f, %.3f)"
              % (a, b, px + nx * a, py + ny * a, b))
    if sel:
        print("   选中点世界坐标 z 范围: %.3f .. %.3f"
              % (min(p[1] for p in sel), max(p[1] for p in sel)))

print()
print("=" * 92)
print("② 斜肩区（路径参数）对应的断面高度")
print("=" * 92)
print("%-5s %-8s %-8s %-22s %-8s %-8s %-8s" % ("i", "s", "world", "xy", "T", "z_wall", "z_top"))
for i in range(len(PATH)):
    s = PATH[i][2]
    if abs(s - MS.S_LEFT) > 0.10:
        continue
    T, zb, zw, zt = shell_params[i]
    print("%-5d %-8.4f %-22s %-8.3f %-8.3f %-8.3f"
          % (i, s, "(%.3f, %.3f)" % (PATH[i][0], PATH[i][1]), T, zw, zt))

print()
print("=" * 92)
print("③ arm_stitch 左右不对称")
print("=" * 92)
for nm in ("arm_stitch_L", "arm_stitch_R"):
    o = bpy.data.objects.get(nm)
    if not o:
        continue
    co = [v.co for v in o.data.vertices]
    print("  %-14s x[%.3f..%.3f]  y[%.3f..%.3f]  z[%.3f..%.3f]"
          % (nm, min(c.x for c in co), max(c.x for c in co),
             min(c.y for c in co), max(c.y for c in co),
             min(c.z for c in co), max(c.z for c in co)))
print("  扶手外表面 x = ±%.3f ；扶手垫中心 x = ±%.3f"
      % (MS.ARM_X + MS.ARM_W / 2, MS.ARM_X))
print("  → L 的针脚在 %.3f(内侧), R 的在 %.3f(外侧) ⇒ 代码 ax+(w/2+..) 未按符号修正"
      % (MS.ARM_X - (MS.ARM_PAD_W / 2 + 0.002), MS.ARM_X + (MS.ARM_PAD_W / 2 + 0.002)))
print("=" * 92)

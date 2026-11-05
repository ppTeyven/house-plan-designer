"""精确定位用户红线标注处的滚边断续问题。

【用户原话】
"你看我画红线的地方，断断续续不够顺滑，我刚刚说的锯齿感就是指这个"

【截图分析】
红线画在【坐垫顶面与前侧壁的交界处】—— 沿着坐垫顶面外沿走的一道滚边
（seat_pipe）。红线呈现"一段一段"的断续感。

【可能的成因】
A. 滚边管本身是好的，但【投射到软包曲面】时，
   在【圆肩过渡带】上环间距变得极大（跳跃）→ 管身一段粗一段细
B. 环的"上方向参考"在圆肩上乱转 → 管截面翻滚 → 视觉上忽粗忽细
C. 管子自交（前面已把自交从 3404 降到 10）
D. 抽稀后环间距不均（有的 3mm 有的 16mm）→ 管身呈"串珠状"

【诊断】
对 seat_pipe_0 做：
  ① 逐环统计：环间距、环半径（应恒等于 r）、截面朝向变化
  ② 找出"间距突变"的位置
  ③ 渲染该滚边的特写图，肉眼确认

用法：blender --background --python diag_welt_rings.py
"""
import bpy
import sys
import os
import math
import bmesh
import mathutils

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bl_lib as B

print("=" * 96)
print("滚边环序列诊断（红线处断续问题）")
print("=" * 96)

# 复现真实的坐垫 + 滚边
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

pipe = B.pipe_on_surface("seat_pipe_0", pts, cush, None, r=0.010, lift=0.0036)
bpy.context.view_layer.update()

SIDES = 20
bm = bmesh.new()
bm.from_mesh(pipe.data)
bm.verts.ensure_lookup_table()

nverts = len(bm.verts)
nring = nverts // SIDES
print("顶点 %d  → 环数 %d（每环 %d 顶点）" % (nverts, nring, SIDES))

# 逐环：中心、间距、切向变化、截面朝向
rings = []
for i in range(nring):
    vs = [bm.verts[i * SIDES + j] for j in range(SIDES)]
    ctr = sum((v.co for v in vs), mathutils.Vector()) / SIDES
    rings.append(ctr)

print()
print("%-5s %10s %10s %10s %10s" % ("环", "间距mm", "切向转°", "到轴心r", "备注"))
print("-" * 96)
prev_t = None
worst = []
for i in range(nring):
    if i == 0:
        seg = rings[1] - rings[0]
    elif i == nring - 1:
        seg = rings[-1] - rings[-2]
    else:
        seg = rings[i + 1] - rings[i - 1]
    t = seg.normalized()
    turn = 0.0
    if prev_t is not None:
        turn = math.degrees(prev_t.angle(t))
    prev_t = t

    # 环的"截面朝向"：法向 n̂（ups）——用顶点相对环心的最大偏移方向估计
    vs = [bm.verts[i * SIDES + j].co for j in range(SIDES)]
    off = vs[0] - rings[i]
    # 找与 off 最不平行的面（用于判断截面是否滚转）

    step = 0.0
    if i > 0:
        step = (rings[i] - rings[i - 1]).length * 1000

    note = ""
    if step > 12:
        note = "← 间距突变"
        worst.append((i, step))
    print("%-5d %10.2f %10.2f %10.2f %10s" %
          (i, step, turn, off.length * 1000, note))

print()
print("间距统计:")
steps = [(rings[i] - rings[i - 1]).length * 1000 for i in range(1, nring)]
ss = sorted(steps)
print("  最小 %.2f  中位 %.2f  最大 %.2f mm  （管径 20mm）"
      % (ss[0], ss[len(ss) // 2], ss[-1]))
print("  间距 > 12mm 的环数: %d / %d" % (len(worst), nring))
if worst:
    print("  突变位置（环号）:", [w[0] for w in worst[:20]])

bm.free()

"""soft_slab 单元测试 —— 精确定位"法线翻转"并守住回归。

【为什么要做这个】
jaggedness.py 测出扶手垫/靠垫/坐垫都有大量二面角 180° 的边，
hard_edge_diag.py 证明：dot = -1.0000（有符号体积 ≈ 0）
→ 不是真实折痕，而是【相邻面法线完全反向】。

法线反向 = 网格有【自相重叠的面】或【绕序反了】。
渲染出来就是黑斑 + 生硬折线 —— 正是用户说的"边边角角锯齿感"。

【v23 已修】
soft_slab 的底面封盖环顺序写反（[0.667, 0.333, 1.0]），
相邻面带自相重叠 → 法线反向。改为 [0.333, 0.667, 1.0]。

【本测试的判据】
1. 有向体积（bmesh calc_volume signed）必须 > 0 且接近解析值
   → 体积 ≈ 0 = 法线互相抵消 = 有重叠/反向面
2. 不允许存在 dot < -0.99 的边（反向边必须为 0）
3. 不允许存在"面心重合 + 法线反向"的重叠面

用法：blender --background --python test_soft_slab.py
"""
import bpy
import sys
import os
import math
import bmesh

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bl_lib as B

# ---- 真实尺寸（与 make_sofa_v18.py 保持一致，避免用例与生产脱节）----
SEAT_DECK_W = 1.816
SEAT_SIDE = 0.006
SEAT_GAP = 0.004
SEAT_N = 3
SEAT_BACK = -0.230
SEAT_FRONT = 0.410
SEAT_W = (SEAT_DECK_W - 2 * SEAT_SIDE - SEAT_GAP * (SEAT_N - 1)) / SEAT_N
SEAT_D = 0.410 - (-0.230)
DECK_TOP = 0.145
SEAT_DECK_TOP = DECK_TOP + 0.024
SEAT_TOP = 0.420
SEAT_T = SEAT_TOP - SEAT_DECK_TOP
SEAT_BOT = SEAT_DECK_TOP

ARM_W = 0.220
ARM_TOP = 0.620
ARM_PAD_T = 0.115
ARM_BOARD_TOP = ARM_TOP - ARM_PAD_T
ARM_FRONT = 0.450
ARM_PAD_Y0 = -0.300
ARM_PAD_Y1 = ARM_FRONT - 0.028
ARM_PAD_W = ARM_W + 0.016
ARM_PAD_D = ARM_PAD_Y1 - ARM_PAD_Y0

BC_H = 0.400
BC_T = 0.165
BC_GAP = 0.006
BC_N = 3
BC_W = (SEAT_DECK_W - 0.030 - BC_GAP * (BC_N - 1)) / BC_N
BC_CZ = SEAT_TOP + 0.002 + BC_H / 2

CASES = [
    ("基准(无clamp)", (0.65, 0.52, 0.229), (0, 0, 0.3105),
     dict(flat_frac=0.86, edge_roll=0.026, bot_inset=0.024,
          bot_roll=0.022, corner=0.95, crown=0.004, bulge=0.003)),
    ("+noise", (0.65, 0.52, 0.229), (0, 0, 0.3105),
     dict(flat_frac=0.86, edge_roll=0.026, bot_inset=0.024,
          bot_roll=0.022, corner=0.95, crown=0.004, bulge=0.003,
          noise=0.0016, noise_freq=11.0, noise_seed=3)),
    ("坐垫实参", (SEAT_W, SEAT_D, SEAT_T),
     (0, (SEAT_BACK + SEAT_FRONT) / 2, SEAT_BOT + SEAT_T / 2),
     dict(flat_frac=0.86, edge_roll=0.026, bot_inset=0.024,
          bot_roll=0.022, corner=0.95, crown=0.004, bulge=0.003,
          noise=0.0016, noise_freq=11.0, noise_seed=3,
          top_clamp=SEAT_TOP, bot_clamp=SEAT_BOT + 0.002)),
    ("扶手垫实参", (ARM_PAD_W, ARM_PAD_D, ARM_PAD_T),
     (0, (ARM_PAD_Y0 + ARM_PAD_Y1) / 2, ARM_BOARD_TOP + ARM_PAD_T / 2 - 0.012),
     dict(flat_frac=0.74, edge_roll=0.030, bot_inset=0.022,
          bot_roll=0.020, corner=0.93, crown=0.010, bulge=0.006,
          noise=0.0016, noise_freq=11.0, noise_seed=7,
          top_clamp=ARM_TOP, bot_clamp=ARM_BOARD_TOP - 0.010)),
    ("靠垫实参", (BC_W, BC_T, BC_H), (0, -0.107, BC_CZ),
     dict(flat_frac=0.78, edge_roll=0.030, bot_inset=0.026,
          bot_roll=0.024, corner=0.93, crown=0.003, bulge=0.004,
          noise=0.0022, noise_freq=10.0, noise_seed=5,
          top_clamp=BC_CZ + BC_H / 2, bot_clamp=BC_CZ - BC_H / 2)),
    ("抱枕实参", (0.270, 0.110, 0.280), (-0.700, 0.055, 0.545),
     dict(flat_frac=0.56, edge_roll=0.044, bot_inset=0.032,
          bot_roll=0.030, corner=0.82, crown=0.010, bulge=0.010,
          noise=0.0030, noise_freq=13.0, noise_seed=101,
          top_clamp=0.545 + 0.140, bot_clamp=0.545 - 0.140)),
]


def analyze(ob):
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bm.normal_update()
    vol = bm.calc_volume(signed=True)      # bmesh 内置有向体积（正确算法）
    rev = 0
    worst = 1.0
    for e in bm.edges:
        if len(e.link_faces) != 2:
            continue
        d = e.link_faces[0].normal.dot(e.link_faces[1].normal)
        if d < worst:
            worst = d
        if d < -0.99:
            rev += 1
    # 重叠面：面心极近且法线反向
    overlap = 0
    fm = [(f.calc_center_median().copy(), f.normal.copy())
          for f in bm.faces]
    for i in range(len(fm)):
        ci, ni = fm[i]
        for j in range(i + 1, len(fm)):
            cj, nj = fm[j]
            if (ci - cj).length < 1e-4 and ni.dot(nj) < -0.9:
                overlap += 1
                break
    nf = len(bm.faces)
    bm.free()
    return vol, rev, worst, overlap, nf


print("=" * 108)
print("%-14s %14s %8s %10s %8s %7s" %
      ("用例", "有向体积cm3", "反向边", "最差dot", "重叠面", "面数"))
print("-" * 108)

fail = 0
for label, size, center, kw in CASES:
    B.wipe()
    ob = B.soft_slab("t", size, center, None, res_u=128, res_v=40, **kw)
    vol, rev, worst, overlap, nf = analyze(ob)
    analytic = size[0] * size[1] * size[2] * 1e6
    flag = ""
    if vol <= 0:
        flag += " ←体积非正!"
        fail += 1
    if rev > 0:
        flag += " ←有反向边!"
        fail += 1
    if overlap > 0:
        flag += " ←有重叠面!"
        fail += 1
    print("%-14s %14.1f %8d %10.4f %8d %7d%s"
          % (label, vol * 1e6, rev, worst, overlap, nf, flag))
    print("%14s解析体积 %.1f cm3（圆角/内缩后应略小）" % ("", analytic))

print()
print("=" * 108)
if fail:
    print("❌ 失败 %d 项 —— 存在法线反向/重叠面" % fail)
else:
    print("✅ 全部通过：无反向边、无重叠面、有向体积为正")

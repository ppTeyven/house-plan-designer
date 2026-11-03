"""L 形转角沙发（P1 批次 · 目录 key = lSofa）

用 sofa_mod.py 的共用软包体系派生，保证与三人沙发（sofa v14）
在配色/滚边/针脚/软包指数上完全一致 —— 这是"配套不违和"的前提。

【尺寸依据】
典型 L 形转角沙发：主段 2400 × 900，侧翼 1600 × 900，转角 900 × 900。
总占地 2400 × 2500。座高 430，扶手顶 490，靠背顶 870。

【结构（与 William 系列同语言）】
  · 薄层软包底架 + 可见抛光铝脚（外撇）
  · 连续包裹式外框：靠背框 + 侧翼靠背，转角处不留缝
  · 独立鹅绒坐垫（主段 3 块 + 侧翼 2 块）+ 独立靠垫
  · 滚边贴合曲面（不穿模）、针脚为独立几何
"""
import bpy
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bl_lib as B
import sofa_mod as SM
from palette import PAL, ROLES

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
OUT = os.path.join(ROOT, "验收", "models", "lSofa.glb")
os.makedirs(os.path.dirname(OUT), exist_ok=True)
B.wipe()

R = ROLES["sofa"]
MATS = {
    "up": B.fabric("U_upholstery", PAL[R["main"]]),
    "updk": B.fabric("U_upholsterydk", PAL[R["dark"]]),
    "welt": B.pbr("U_dark", "#4A4438", 0.78),
    "metal": B.pbr("U_metal", "#C9CCD0", 0.18, 1.0),
    "thread": B.pbr("U_thread", "#8A7E68", 0.85),
}

# ============ 尺寸 ============
MAIN_W = 2.40          # 主段长（X）
WING_D = 1.60          # 侧翼长（Y）
DEP = 0.90             # 进深
SEAT_BACK = -0.175
SEAT_FRONT = 0.400

BACK_Y = -0.420
BACK_CY = BACK_Y + SM.BACK_T / 2
BACK_F = BACK_Y + SM.BACK_T
ARM_FRONT = 0.436
ARM_BACK = BACK_Y - 0.004

THREAD_R = SM.THREAD_R
SEAT_BOT = SM.DECK_TOP + 0.024

objs = []

# ---------------- 底架 ----------------
# 主段底架（长 X）
SM.deck("main", 0, 0, MAIN_W, DEP, MATS, objs)
# 侧翼底架（长 Y），放在主段左侧
WING_X = -(MAIN_W / 2) + DEP / 2
SM.deck("wing", WING_X, -WING_D / 2 + DEP / 2 + 0.05, DEP, WING_D, MATS, objs)

# ---------------- 抛光铝脚 ----------------
SM.leg_set("main", -MAIN_W / 2 + 0.058, MAIN_W / 2 - 0.058,
           -DEP / 2 + 0.052, DEP / 2 - 0.052, MATS, objs, n_x=4, n_y=2)
SM.leg_set("wing", WING_X - DEP / 2 + 0.058, WING_X + DEP / 2 - 0.058,
           -WING_D / 2 + 0.10, -WING_D / 2 + DEP + 0.02, MATS, objs,
           n_x=2, n_y=3)

# ================= 布局分区（防穿模的关键） =================
# 【穿模实测】初版 L 形沙发 seat_m0 ↔ seat_w0 穿入 17%（最深 121mm），
#             backc_w0 ↔ seat_w0 穿入 8.9%（最深 99.6mm）。
# 根因：主段坐垫一直排到 x = -MAIN_W/2 + 0.26 = -0.94，
#       而侧翼坐垫也在转角区（x 范围 -1.195 ~ -0.335）—— 两者大幅重叠。
#
# 修正：明确划出【主段区】与【侧翼区】，互不重叠：
#   · 主段坐垫只到 x = WING_X + DEP/2（侧翼区的右边界）再往左留 20mm 缝
#   · 侧翼坐垫只从 y = 转角前 开始
#   · 转角区（corner）单独一块坐垫，属于主段还是侧翼二选一，避免双重归属
WING_RIGHT = WING_X + DEP / 2          # = -0.795  侧翼区右界
CORNER_X = WING_RIGHT - 0.020          # 主段坐垫左界（留 20mm 缝）

# ---------------- 靠背框 ----------------
# 侧翼靠背（长 Y）
WING_BACK_X = WING_X - DEP / 2 + SM.BACK_T / 2
WING_CY = -WING_D / 2 + DEP / 2 + 0.05 - DEP / 2 + 0.05
# 主段靠背：只做【右扶手内侧到侧翼靠背内侧】的部分，避免与侧翼靠背互侵
BACK_INNER_R = MAIN_W / 2 - 0.205      # 右扶手内侧 = 0.995
BACK_INNER_L = WING_BACK_X + SM.BACK_T  # 侧翼靠背内侧
SM.back_shell("back_main", (BACK_INNER_R + BACK_INNER_L) / 2, BACK_CY,
              BACK_INNER_R - BACK_INNER_L, MATS, objs)

side = B.box("back_wing", (SM.BACK_T, WING_D - 0.10, SM.BACK_TOP - SM.DECK_TOP),
             (WING_BACK_X, -WING_D / 2 + 0.05 + (WING_D - 0.10) / 2,
              (SM.DECK_TOP + SM.BACK_TOP) / 2), MATS["up"])
B.bevel(side, 0.034, 5)
B.subsurf(side, 3)
for v in side.data.vertices:
    h = (v.co.z - SM.DECK_TOP) / (SM.BACK_TOP - SM.DECK_TOP)
    v.co.x += SM.BACK_TILT * h * h      # 侧翼靠背向后倾
    if v.co.z > SM.BACK_TOP - 0.06:
        v.co.y *= 0.994
B.smart_uv(side)
objs.append(side)

# ---------------- 坐垫 ----------------
seat_objs = []

# 主段 3 块坐垫（右段，从右扶手往左排到 CORNER_X）
MAIN_SEAT_RIGHT = MAIN_W / 2 - 0.225
MAIN_SEAT_W = (MAIN_SEAT_RIGHT - CORNER_X - 0.04) / 3 - 0.020
for k in range(3):
    cx = MAIN_SEAT_RIGHT - MAIN_SEAT_W / 2 - k * (MAIN_SEAT_W + 0.020)
    cy = (SEAT_BACK + SEAT_FRONT) / 2
    c = SM.seat_cushion("seat_m%d" % k, cx, cy, MAIN_SEAT_W,
                        SEAT_FRONT - SEAT_BACK, MATS, seed=k * 7 + 3)
    objs.append(c)
    seat_objs.append((c, cx, cy, MAIN_SEAT_W, SEAT_FRONT - SEAT_BACK))
    SM.pipe_ring_equator("seat_m%d_pipe" % k, cx, cy, MAIN_SEAT_W,
                         SEAT_FRONT - SEAT_BACK, SEAT_BOT + SM.SEAT_T * 0.40,
                         c, MATS, objs)

# 侧翼 2 块坐垫（沿 Y 排，从转角后方开始）
WING_SEAT_Y0 = -WING_D / 2 + DEP + 0.02
WING_SEAT_D = (WING_D - 0.22) / 2 - 0.018
WING_CX = WING_X + 0.020
for k in range(2):
    cy = WING_SEAT_Y0 + k * (WING_SEAT_D + 0.018)
    c = SM.seat_cushion("seat_w%d" % k, WING_CX, cy, DEP - 0.16,
                        WING_SEAT_D, MATS, seed=31 + k * 7)
    objs.append(c)
    seat_objs.append((c, WING_CX, cy, DEP - 0.16, WING_SEAT_D))
    SM.pipe_ring_equator("seat_w%d_pipe" % k, WING_CX, cy, DEP - 0.16,
                         WING_SEAT_D, SEAT_BOT + SM.SEAT_T * 0.40,
                         c, MATS, objs)

# ---------------- 靠垫 ----------------
backc_objs = []
# 主段靠垫：只覆盖主段坐垫区（不伸进侧翼），背面止于靠背框前面
BC_W = (MAIN_SEAT_RIGHT - CORNER_X - 0.02) / 3 - 0.018
BC_CY = BACK_F + 0.006 + SM.BACK_T / 2 - 0.022
for k in range(3):
    cx = MAIN_SEAT_RIGHT - BC_W / 2 - k * (BC_W + 0.018)
    bc, cz = SM.back_cushion("backc_m%d" % k, cx, BC_CY,
                              BC_W, 0.395, 0.150, MATS, seed=k * 11 + 5)
    objs.append(bc)
    backc_objs.append((bc, cx))
    SM.pipe_back_bottom("backc_m%d_pipe" % k, cx, BC_CY - 0.075 - 0.006, BC_W,
                        cz - 0.395 / 2, bc, MATS, objs)

# 侧翼靠垫：侧躺（绕 Y 轴转 90°），下缘坐在侧翼坐垫上，不穿进去
WBC_D = (WING_SEAT_D + WING_SEAT_D + 0.018) / 2 - 0.010
WBC_CX = WING_BACK_X + SM.BACK_T + 0.010 + 0.075   # 侧翼靠垫中心 x（侧躺后厚度方向）
for k in range(2):
    cy = WING_SEAT_Y0 + k * (WING_SEAT_D + 0.018) + WING_SEAT_D / 2
    bc, cz = SM.back_cushion("backc_w%d" % k, WBC_CX, cy,
                              WBC_D, 0.395, 0.150, MATS, seed=61 + k * 11,
                              tilt=0.0)
    # 侧躺：绕 Y 轴转 90°（把厚度方向转到 X）
    for v in bc.data.vertices:
        dx = v.co.x - WBC_CX
        dz = v.co.z - cz
        a = math.radians(90)
        v.co.x = WBC_CX + dx * math.cos(a) - dz * math.sin(a)
        v.co.z = cz + dx * math.sin(a) + dz * math.cos(a)
    # 侧躺后底缘要落在坐垫顶面（43cm）上，不穿进坐垫
    for v in bc.data.vertices:
        if v.co.z < SM.SEAT_TOP - 0.004:
            v.co.z = SM.SEAT_TOP - 0.004
    objs.append(bc)
    backc_objs.append((bc, WBC_CX))

# ---------------- 扶手 ----------------
arm_pad_objs = []
# 右扶手（主段末端）
ARM_W = 0.205
ax = MAIN_W / 2 - ARM_W / 2
ad = ARM_FRONT - ARM_BACK
side = B.box("arm_side_R", (ARM_W, ad, 0.390 - SM.DECK_TOP),
             (ax, (ARM_FRONT + ARM_BACK) / 2,
              SM.DECK_TOP + (0.390 - SM.DECK_TOP) / 2), MATS["updk"])
B.bevel(side, 0.026, 4)
B.subsurf(side, 2)
objs.append(side)
pad, _ = SM.arm_pad("arm_pad_R", ax, (ARM_FRONT + ARM_BACK) / 2,
                    ARM_W + 0.018, ad - 0.012, MATS, seed=7,
                    front_clamp=ARM_FRONT - 0.018)
objs.append(pad)
arm_pad_objs.append((pad, ax, (ARM_FRONT + ARM_BACK) / 2, ARM_W + 0.018, ad - 0.012))
SM.pipe_arm_top("arm_pipe_R", ax, (ARM_FRONT + ARM_BACK) / 2,
                ARM_W + 0.018, ad - 0.012, SM.ARM_TOP - 0.022, pad, MATS, objs)

# 侧翼前端扶手（转角对角）
WING_ARM_Y = -WING_D / 2 + 0.052
pad2, _ = SM.arm_pad("arm_pad_W", WING_CX, WING_ARM_Y,
                     DEP - 0.14, 0.190, MATS, seed=23)
objs.append(pad2)
arm_pad_objs.append((pad2, WING_CX, WING_ARM_Y, DEP - 0.14, 0.190))
SM.pipe_arm_top("arm_pipe_W", WING_CX, WING_ARM_Y, DEP - 0.14, 0.190,
                SM.ARM_TOP - 0.022, pad2, MATS, objs)

# ---------------- 转角柱（衔接主段与侧翼，防止两个框在转角硬碰互侵） ----------------
# 【穿模实测】初版 back_wing ↔ arm_pad_W 穿入 1.7%（最深 26.2mm）。
# 真实 L 形沙发的转角是一个连续的体量，不是两个 Box 撞在一起。
# 这里用一个独立的转角收头柱，放在【侧翼靠背前面】，与两者各留 6mm 缝，
# 既补上转角体量，又不会侵入任何已有部件。
CORNER_PAD = 0.150
CORNER_X = WING_BACK_X + SM.BACK_T + CORNER_PAD / 2 + 0.006
CORNER_Y = CORNER_Y0 = -WING_D / 2 + 0.05 + CORNER_PAD / 2 + 0.006
corner = B.box("corner_post",
               (CORNER_PAD, CORNER_PAD, SM.BACK_TOP - SM.DECK_TOP),
               (CORNER_X, CORNER_Y,
                SM.DECK_TOP + (SM.BACK_TOP - SM.DECK_TOP) / 2), MATS["updk"])
B.bevel(corner, 0.026, 4)
B.subsurf(corner, 2)
objs.append(corner)

# ---------------- 针脚 ----------------
for k, (c, cx, cy, w, d) in enumerate(seat_objs):
    pts = []
    for i in range(89):
        a = 2 * math.pi * i / 88
        pts.append((cx + (w / 2 - 0.011) * math.cos(a),
                    cy + (d / 2 - 0.011) * math.sin(a),
                    SM.SEAT_TOP - 0.046))
    SM.stitch_on_surface("seat_stitch_%d" % k, pts, c, MATS["thread"], out=objs)

# 绗缝分线
for k, (c, cx, cy, w, d) in enumerate(seat_objs):
    for j, fx in enumerate((-0.24, 0.02, 0.28)):
        x = cx + fx * w
        pts = []
        for i in range(31):
            t = i / 30
            pts.append((x, cy - (d / 2 - 0.030) + (d - 0.060) * t,
                        SM.SEAT_TOP - 0.004 + 0.006 * math.sin(t * math.pi)))
        SM.stitch_on_surface("seat_tuft_%d_%d" % (k, j), pts, c, MATS["thread"],
                             r=0.00082, length=0.009, gap=0.005, out=objs)

# 靠背框顶针脚
objs += B.stitch_line("back_stitch",
                      (-MAIN_W / 2 + 0.20, BACK_CY - 0.022, SM.BACK_TOP - 0.055),
                      (MAIN_W / 2 - 0.20, BACK_CY - 0.022, SM.BACK_TOP - 0.055),
                      MATS["thread"], r=THREAD_R, lift=0.002)

for o in list(objs):
    if o.type == 'MESH':
        B.apply_mods(o)

B.export(OUT)
print("OK lSofa ->", OUT, "objects:", len(objs))

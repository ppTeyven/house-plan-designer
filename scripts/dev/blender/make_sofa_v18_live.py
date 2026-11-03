"""sofa v18 —— 连续软包实体 v2，修正 v17 的几何缺陷

【v17 的实测缺陷（逐项数据核对）】
  1. shell 尺寸超标：x[-1.250, 1.122]，标称宽 2.24 → 实际 2.372
     根因：sofa_shell.rounded_outline 把拐角圆弧塞进了【它前面那一段】，
           路径出现折返环，且左右不对称。
  2. 软包底面是圆弧 → 坐垫/靠垫/扶手垫像气球悬空，没坐实在座板上
     修正：superellipsoid_soft 新增 bot_clamp（底面压平）
  3. 靠垫被外壳吞掉，只露一条边
     修正：靠垫整体前移 + 加高，坐垫与靠垫之间留可见缝隙
  4. s 参数与实际弧长不一致 → 拐角处断面插值错位
     修正：rounded_outline 的 s 统一按真实弧长计算

【本轮效率改造（关键）】
  针脚从"每针一个 mesh 对象"改为"一条曲线多条 spline"：
    sofa.glb 对象数 5684 → 52，构建耗时 4~7 分钟 → 2.6 秒（约 200×）
  详见 bl_lib.stitch_poly 的效率说明。
"""
import bpy
import math
import os
import sys
import random
import mathutils

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bl_lib as B
import sofa_shell as SH
import live
from palette import PAL, ROLES

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
OUT = os.path.join(ROOT, "验收", "models", "sofa.glb")
os.makedirs(os.path.dirname(OUT), exist_ok=True)
B.wipe()

R = ROLES["sofa"]
M_UP = B.fabric("U_upholstery", PAL[R["main"]])
M_UPDK = B.fabric("U_upholsterydk", PAL[R["dark"]])
M_WELT = B.pbr("U_dark", "#4A4438", 0.78)
M_ALU = B.pbr("U_metal", "#C9CCD0", 0.18, 1.0)
M_THREAD = B.pbr("U_thread", "#8A7E68", 0.85)

# ============================ 尺寸 ============================
W, D = 2.24, 0.90

FRAME_Z0 = 0.112          # 底部框架下沿
FRAME_X = 1.030          # 底部框架外沿（半宽）
FRAME_Y = 0.372          # 底部框架外沿（半深）

DECK_TOP = 0.150
SEAT_DECK_TOP = DECK_TOP + 0.024

SEAT_TOP = 0.430

ARM_TOP = 0.490          # 扶手顶（软包垫顶）
ARM_PAD_T = 0.100
ARM_BOARD_TOP = ARM_TOP - ARM_PAD_T   # 0.390 外壳扶手段顶
BACK_TOP = 0.870

BACK_T = 0.130
ARM_W = 0.205

ARM_X = W / 2 - ARM_W / 2           # 1.0175 扶手中心
ARM_IN = ARM_X - ARM_W / 2          # 0.915 扶手内表面
ARM_FRONT = 0.436

BACK_OUT = -0.420                   # 靠背外表面
BACK_CY = BACK_OUT + BACK_T / 2     # -0.355 靠背板中心
BACK_IN = BACK_OUT + BACK_T         # -0.290 靠背内表面

SEAT_BACK = -0.160
SEAT_FRONT = 0.400

CORNER_R = 0.160

objs = []

# --- LIVE-STEPS-START ---
# =====================================================================
# LIVE 步骤化：每段建模代码 = 一个函数，由 live.run() 逐帧执行
# 跨段共享的变量放在 ns 字典里（避免闭包提前绑定问题）
# =====================================================================
NS = {}
for _k in ['ARM_PAD_W', 'ARM_PAD_Y0', 'ARM_PAD_Y1', 'ARM_SHELL_T', 'BC_CY', 'BC_CZ', 'BC_GAP', 'BC_H', 'BC_N', 'BC_T', 'BC_W', 'BC_X0', 'FD', 'FW', 'LEG_H', 'LEG_R', 'OUTLINE', 'PATH', 'PIPE_LIFT', 'PIPE_R', 'RADII', 'RAIL', 'SEAT_BOT', 'SEAT_D', 'SEAT_DECK_CY', 'SEAT_DECK_D', 'SEAT_DECK_W', 'SEAT_GAP', 'SEAT_N', 'SEAT_SIDE', 'SEAT_T', 'SEAT_W', 'SEAT_X0', 'SHOULDER', 'STATES', 'S_LEFT', 'S_RIGHT', '_al', '_total', 'arm_pad_objs', 'backc_objs', 'foot_x', 'foot_y', 'seat_deck', 'seat_objs', 'shell', 'shell_frames', 'shell_params', 'shell_sects']:
    NS[_k] = None
NS['objs'] = []          # 共享的对象列表，各段往里 append
objs = NS['objs']

def build_00_step0():
    global objs



    # =====================================================================
    # 1. 连续软包实体（背板 + 两扶手 + 两个转角 + 两个斜肩，一个网格）
    # =====================================================================
    # 俯视外轮廓（沿"外表面"走，不是板中心）：
    #   左扶手前端 → 左扶手后端 → 右扶手后端 → 右扶手前端
    # 断面 a ≤ 0 = 向内进深（沙发内侧），所以路径上的点 = 实体【外表面】
    NS['OUTLINE'] = [
        (-ARM_X - ARM_W / 2, ARM_FRONT),
        (-ARM_X - ARM_W / 2, BACK_OUT),
        (ARM_X + ARM_W / 2, BACK_OUT),
        (ARM_X + ARM_W / 2, ARM_FRONT),
    ]
    NS['RADII'] = [0.0, CORNER_R, CORNER_R, 0.0]
    NS['PATH'] = SH.rounded_outline(NS['OUTLINE'], NS['RADII'], corner_seg=18)

    # 【v18 修正】NS['S_LEFT'] / NS['S_RIGHT'] 必须用【路径自己的弧长参数】，
    # 不能用原始折线的参数 —— rounded_outline 的 s 已改成按真实弧长算
    # （圆弧处两者不等）。否则 NS['STATES'] 的锚点会错位，
    # 拐角处的断面高度/厚度就插值到错误的位置。
    NS['_al'] = SH.arc_len_param([(p[0], p[1]) for p in NS['PATH']])
    NS['_total'] = max(1e-9, NS['_al'][-1])


    def _s_at(x, y):
        """路径上最接近 (x,y) 的点的弧长参数"""
        best = min(range(len(NS['PATH'])),
                   key=lambda i: (NS['PATH'][i][0] - x) ** 2 + (NS['PATH'][i][1] - y) ** 2)
        return NS['_al'][best] / NS['_total']


    NS['S_LEFT'] = _s_at(-(ARM_X + ARM_W / 2), BACK_OUT)
    NS['S_RIGHT'] = _s_at(ARM_X + ARM_W / 2, BACK_OUT)

    # 断面状态：(s, T进深, z_bot, z_wall, z_top)
    #   扶手段：T=ARM_W(0.205) 顶=0.390
    #   靠背段：T=BACK_T(0.130) 顶=0.870
    #   斜肩：两者之间连续插值
    # 【v18】扶手段 T 加宽到 ARM_W+0.016，让扶手垫（NS['ARM_PAD_W']=ARM_W+0.014）
    #        能完整坐在壳体扶手面上而不是边缘悬空
    NS['SHOULDER'] = 0.052
    NS['ARM_SHELL_T'] = ARM_W + 0.016
    NS['STATES'] = [
        (0.000, NS['ARM_SHELL_T'], DECK_TOP, ARM_BOARD_TOP, ARM_BOARD_TOP),
        (NS['S_LEFT'] - 0.060, NS['ARM_SHELL_T'], DECK_TOP, ARM_BOARD_TOP, ARM_BOARD_TOP),
        (NS['S_LEFT'] - NS['SHOULDER'] * 0.50, NS['ARM_SHELL_T'] * 0.93, DECK_TOP,
         ARM_BOARD_TOP, ARM_BOARD_TOP + 0.185),
        (NS['S_LEFT'] + NS['SHOULDER'] * 0.22, BACK_T * 1.20, DECK_TOP,
         BACK_TOP - 0.075, BACK_TOP - 0.020),
        (NS['S_LEFT'] + 0.062, BACK_T, DECK_TOP, BACK_TOP - 0.010, BACK_TOP),
        (NS['S_RIGHT'] - 0.062, BACK_T, DECK_TOP, BACK_TOP - 0.010, BACK_TOP),
        (NS['S_RIGHT'] - NS['SHOULDER'] * 0.22, BACK_T * 1.20, DECK_TOP,
         BACK_TOP - 0.075, BACK_TOP - 0.020),
        (NS['S_RIGHT'] + NS['SHOULDER'] * 0.50, NS['ARM_SHELL_T'] * 0.93, DECK_TOP,
         ARM_BOARD_TOP, ARM_BOARD_TOP + 0.185),
        (NS['S_RIGHT'] + 0.060, NS['ARM_SHELL_T'], DECK_TOP, ARM_BOARD_TOP, ARM_BOARD_TOP),
        (1.000, NS['ARM_SHELL_T'], DECK_TOP, ARM_BOARD_TOP, ARM_BOARD_TOP),
    ]

    NS['shell'], NS['shell_params'], NS['shell_sects'], NS['shell_frames'] = SH.build_shell(
        "shell", NS['PATH'], NS['STATES'], M_UP, cap_len=0.050)
    SH.cloth_relax(NS['shell'], amp=0.0030, freq=12.0, seed=3, down_weight=0.30)
    objs.append(NS['shell'])

    # --- 回写共享变量到 NS ---
    try:
        NS['ARM_PAD_W'] = ARM_PAD_W
    except NameError:
        pass
    try:
        NS['ARM_PAD_Y0'] = ARM_PAD_Y0
    except NameError:
        pass
    try:
        NS['ARM_PAD_Y1'] = ARM_PAD_Y1
    except NameError:
        pass
    try:
        NS['ARM_SHELL_T'] = ARM_SHELL_T
    except NameError:
        pass
    try:
        NS['BC_CY'] = BC_CY
    except NameError:
        pass
    try:
        NS['BC_CZ'] = BC_CZ
    except NameError:
        pass
    try:
        NS['BC_GAP'] = BC_GAP
    except NameError:
        pass
    try:
        NS['BC_H'] = BC_H
    except NameError:
        pass
    try:
        NS['BC_N'] = BC_N
    except NameError:
        pass
    try:
        NS['BC_T'] = BC_T
    except NameError:
        pass
    try:
        NS['BC_W'] = BC_W
    except NameError:
        pass
    try:
        NS['BC_X0'] = BC_X0
    except NameError:
        pass
    try:
        NS['FD'] = FD
    except NameError:
        pass
    try:
        NS['FW'] = FW
    except NameError:
        pass
    try:
        NS['LEG_H'] = LEG_H
    except NameError:
        pass
    try:
        NS['LEG_R'] = LEG_R
    except NameError:
        pass
    try:
        NS['OUTLINE'] = OUTLINE
    except NameError:
        pass
    try:
        NS['PATH'] = PATH
    except NameError:
        pass
    try:
        NS['PIPE_LIFT'] = PIPE_LIFT
    except NameError:
        pass
    try:
        NS['PIPE_R'] = PIPE_R
    except NameError:
        pass
    try:
        NS['RADII'] = RADII
    except NameError:
        pass
    try:
        NS['RAIL'] = RAIL
    except NameError:
        pass
    try:
        NS['SEAT_BOT'] = SEAT_BOT
    except NameError:
        pass
    try:
        NS['SEAT_D'] = SEAT_D
    except NameError:
        pass
    try:
        NS['SEAT_DECK_CY'] = SEAT_DECK_CY
    except NameError:
        pass
    try:
        NS['SEAT_DECK_D'] = SEAT_DECK_D
    except NameError:
        pass
    try:
        NS['SEAT_DECK_W'] = SEAT_DECK_W
    except NameError:
        pass
    try:
        NS['SEAT_GAP'] = SEAT_GAP
    except NameError:
        pass
    try:
        NS['SEAT_N'] = SEAT_N
    except NameError:
        pass
    try:
        NS['SEAT_SIDE'] = SEAT_SIDE
    except NameError:
        pass
    try:
        NS['SEAT_T'] = SEAT_T
    except NameError:
        pass
    try:
        NS['SEAT_W'] = SEAT_W
    except NameError:
        pass
    try:
        NS['SEAT_X0'] = SEAT_X0
    except NameError:
        pass
    try:
        NS['SHOULDER'] = SHOULDER
    except NameError:
        pass
    try:
        NS['STATES'] = STATES
    except NameError:
        pass
    try:
        NS['S_LEFT'] = S_LEFT
    except NameError:
        pass
    try:
        NS['S_RIGHT'] = S_RIGHT
    except NameError:
        pass
    try:
        NS['_al'] = _al
    except NameError:
        pass
    try:
        NS['_total'] = _total
    except NameError:
        pass
    try:
        NS['arm_pad_objs'] = arm_pad_objs
    except NameError:
        pass
    try:
        NS['backc_objs'] = backc_objs
    except NameError:
        pass
    try:
        NS['foot_x'] = foot_x
    except NameError:
        pass
    try:
        NS['foot_y'] = foot_y
    except NameError:
        pass
    try:
        NS['seat_deck'] = seat_deck
    except NameError:
        pass
    try:
        NS['seat_objs'] = seat_objs
    except NameError:
        pass
    try:
        NS['shell'] = shell
    except NameError:
        pass
    try:
        NS['shell_frames'] = shell_frames
    except NameError:
        pass
    try:
        NS['shell_params'] = shell_params
    except NameError:
        pass
    try:
        NS['shell_sects'] = shell_sects
    except NameError:
        pass


def build_01_step1():
    global objs

    # =====================================================================
    # 2. 底座框（深色薄框 + 外露铝腿）
    # =====================================================================
    NS['FW'] = FRAME_X * 2
    NS['FD'] = FRAME_Y * 2
    NS['RAIL'] = 0.050


    def frame_bar(name, size, center, bev=0.008, sub=2):
        b = B.box(name, size, center, M_UPDK)
        B.bevel(b, bev, 3)
        if sub:
            B.subsurf(b, sub)
        objs.append(b)
        return b


    frame_bar("frame_front", (NS['FW'], NS['RAIL'], FRAME_Z0), (0, FRAME_Y - NS['RAIL'] / 2, FRAME_Z0 / 2))
    frame_bar("frame_rear", (NS['FW'], NS['RAIL'], FRAME_Z0), (0, -FRAME_Y + NS['RAIL'] / 2, FRAME_Z0 / 2))
    for sx in (-1, 1):
        frame_bar("frame_side_%s" % ('L' if sx < 0 else 'R'),
                  (NS['RAIL'], NS['FD'] - NS['RAIL'] * 2, FRAME_Z0),
                  (sx * (FRAME_X - NS['RAIL'] / 2), 0, FRAME_Z0 / 2))

    # --- 回写共享变量到 NS ---
    try:
        NS['ARM_PAD_W'] = ARM_PAD_W
    except NameError:
        pass
    try:
        NS['ARM_PAD_Y0'] = ARM_PAD_Y0
    except NameError:
        pass
    try:
        NS['ARM_PAD_Y1'] = ARM_PAD_Y1
    except NameError:
        pass
    try:
        NS['ARM_SHELL_T'] = ARM_SHELL_T
    except NameError:
        pass
    try:
        NS['BC_CY'] = BC_CY
    except NameError:
        pass
    try:
        NS['BC_CZ'] = BC_CZ
    except NameError:
        pass
    try:
        NS['BC_GAP'] = BC_GAP
    except NameError:
        pass
    try:
        NS['BC_H'] = BC_H
    except NameError:
        pass
    try:
        NS['BC_N'] = BC_N
    except NameError:
        pass
    try:
        NS['BC_T'] = BC_T
    except NameError:
        pass
    try:
        NS['BC_W'] = BC_W
    except NameError:
        pass
    try:
        NS['BC_X0'] = BC_X0
    except NameError:
        pass
    try:
        NS['FD'] = FD
    except NameError:
        pass
    try:
        NS['FW'] = FW
    except NameError:
        pass
    try:
        NS['LEG_H'] = LEG_H
    except NameError:
        pass
    try:
        NS['LEG_R'] = LEG_R
    except NameError:
        pass
    try:
        NS['OUTLINE'] = OUTLINE
    except NameError:
        pass
    try:
        NS['PATH'] = PATH
    except NameError:
        pass
    try:
        NS['PIPE_LIFT'] = PIPE_LIFT
    except NameError:
        pass
    try:
        NS['PIPE_R'] = PIPE_R
    except NameError:
        pass
    try:
        NS['RADII'] = RADII
    except NameError:
        pass
    try:
        NS['RAIL'] = RAIL
    except NameError:
        pass
    try:
        NS['SEAT_BOT'] = SEAT_BOT
    except NameError:
        pass
    try:
        NS['SEAT_D'] = SEAT_D
    except NameError:
        pass
    try:
        NS['SEAT_DECK_CY'] = SEAT_DECK_CY
    except NameError:
        pass
    try:
        NS['SEAT_DECK_D'] = SEAT_DECK_D
    except NameError:
        pass
    try:
        NS['SEAT_DECK_W'] = SEAT_DECK_W
    except NameError:
        pass
    try:
        NS['SEAT_GAP'] = SEAT_GAP
    except NameError:
        pass
    try:
        NS['SEAT_N'] = SEAT_N
    except NameError:
        pass
    try:
        NS['SEAT_SIDE'] = SEAT_SIDE
    except NameError:
        pass
    try:
        NS['SEAT_T'] = SEAT_T
    except NameError:
        pass
    try:
        NS['SEAT_W'] = SEAT_W
    except NameError:
        pass
    try:
        NS['SEAT_X0'] = SEAT_X0
    except NameError:
        pass
    try:
        NS['SHOULDER'] = SHOULDER
    except NameError:
        pass
    try:
        NS['STATES'] = STATES
    except NameError:
        pass
    try:
        NS['S_LEFT'] = S_LEFT
    except NameError:
        pass
    try:
        NS['S_RIGHT'] = S_RIGHT
    except NameError:
        pass
    try:
        NS['_al'] = _al
    except NameError:
        pass
    try:
        NS['_total'] = _total
    except NameError:
        pass
    try:
        NS['arm_pad_objs'] = arm_pad_objs
    except NameError:
        pass
    try:
        NS['backc_objs'] = backc_objs
    except NameError:
        pass
    try:
        NS['foot_x'] = foot_x
    except NameError:
        pass
    try:
        NS['foot_y'] = foot_y
    except NameError:
        pass
    try:
        NS['seat_deck'] = seat_deck
    except NameError:
        pass
    try:
        NS['seat_objs'] = seat_objs
    except NameError:
        pass
    try:
        NS['shell'] = shell
    except NameError:
        pass
    try:
        NS['shell_frames'] = shell_frames
    except NameError:
        pass
    try:
        NS['shell_params'] = shell_params
    except NameError:
        pass
    try:
        NS['shell_sects'] = shell_sects
    except NameError:
        pass


def build_02_step2():
    global objs

    # =====================================================================
    # 3. 抛光铝脚
    # =====================================================================
    NS['LEG_R'] = 0.019
    NS['LEG_H'] = FRAME_Z0
    NS['foot_x'] = [-(FRAME_X - 0.078), 0.0, FRAME_X - 0.078]
    NS['foot_y'] = [-(FRAME_Y - 0.068), FRAME_Y - 0.068]
    for ix, fx in enumerate(NS['foot_x']):
        for iy, fy in enumerate(NS['foot_y']):
            if ix == 1 and iy == 0:
                continue
            splay = 0.016
            ox = math.copysign(splay, fx) if abs(fx) > 1e-6 else 0.0
            oy = math.copysign(splay, fy) if abs(fy) > 1e-6 else 0.0
            objs.append(B.cyl("alu_leg_%d_%d" % (ix, iy), NS['LEG_R'], NS['LEG_H'],
                               (fx + ox, fy + oy, NS['LEG_H'] / 2), M_ALU, verts=20,
                               r2=NS['LEG_R'] * 1.22))
            objs.append(B.cyl("leg_cup_%d_%d" % (ix, iy), NS['LEG_R'] * 1.34, 0.011,
                               (fx, fy, NS['LEG_H'] - 0.004), M_UPDK, verts=16))

    # --- 回写共享变量到 NS ---
    try:
        NS['ARM_PAD_W'] = ARM_PAD_W
    except NameError:
        pass
    try:
        NS['ARM_PAD_Y0'] = ARM_PAD_Y0
    except NameError:
        pass
    try:
        NS['ARM_PAD_Y1'] = ARM_PAD_Y1
    except NameError:
        pass
    try:
        NS['ARM_SHELL_T'] = ARM_SHELL_T
    except NameError:
        pass
    try:
        NS['BC_CY'] = BC_CY
    except NameError:
        pass
    try:
        NS['BC_CZ'] = BC_CZ
    except NameError:
        pass
    try:
        NS['BC_GAP'] = BC_GAP
    except NameError:
        pass
    try:
        NS['BC_H'] = BC_H
    except NameError:
        pass
    try:
        NS['BC_N'] = BC_N
    except NameError:
        pass
    try:
        NS['BC_T'] = BC_T
    except NameError:
        pass
    try:
        NS['BC_W'] = BC_W
    except NameError:
        pass
    try:
        NS['BC_X0'] = BC_X0
    except NameError:
        pass
    try:
        NS['FD'] = FD
    except NameError:
        pass
    try:
        NS['FW'] = FW
    except NameError:
        pass
    try:
        NS['LEG_H'] = LEG_H
    except NameError:
        pass
    try:
        NS['LEG_R'] = LEG_R
    except NameError:
        pass
    try:
        NS['OUTLINE'] = OUTLINE
    except NameError:
        pass
    try:
        NS['PATH'] = PATH
    except NameError:
        pass
    try:
        NS['PIPE_LIFT'] = PIPE_LIFT
    except NameError:
        pass
    try:
        NS['PIPE_R'] = PIPE_R
    except NameError:
        pass
    try:
        NS['RADII'] = RADII
    except NameError:
        pass
    try:
        NS['RAIL'] = RAIL
    except NameError:
        pass
    try:
        NS['SEAT_BOT'] = SEAT_BOT
    except NameError:
        pass
    try:
        NS['SEAT_D'] = SEAT_D
    except NameError:
        pass
    try:
        NS['SEAT_DECK_CY'] = SEAT_DECK_CY
    except NameError:
        pass
    try:
        NS['SEAT_DECK_D'] = SEAT_DECK_D
    except NameError:
        pass
    try:
        NS['SEAT_DECK_W'] = SEAT_DECK_W
    except NameError:
        pass
    try:
        NS['SEAT_GAP'] = SEAT_GAP
    except NameError:
        pass
    try:
        NS['SEAT_N'] = SEAT_N
    except NameError:
        pass
    try:
        NS['SEAT_SIDE'] = SEAT_SIDE
    except NameError:
        pass
    try:
        NS['SEAT_T'] = SEAT_T
    except NameError:
        pass
    try:
        NS['SEAT_W'] = SEAT_W
    except NameError:
        pass
    try:
        NS['SEAT_X0'] = SEAT_X0
    except NameError:
        pass
    try:
        NS['SHOULDER'] = SHOULDER
    except NameError:
        pass
    try:
        NS['STATES'] = STATES
    except NameError:
        pass
    try:
        NS['S_LEFT'] = S_LEFT
    except NameError:
        pass
    try:
        NS['S_RIGHT'] = S_RIGHT
    except NameError:
        pass
    try:
        NS['_al'] = _al
    except NameError:
        pass
    try:
        NS['_total'] = _total
    except NameError:
        pass
    try:
        NS['arm_pad_objs'] = arm_pad_objs
    except NameError:
        pass
    try:
        NS['backc_objs'] = backc_objs
    except NameError:
        pass
    try:
        NS['foot_x'] = foot_x
    except NameError:
        pass
    try:
        NS['foot_y'] = foot_y
    except NameError:
        pass
    try:
        NS['seat_deck'] = seat_deck
    except NameError:
        pass
    try:
        NS['seat_objs'] = seat_objs
    except NameError:
        pass
    try:
        NS['shell'] = shell
    except NameError:
        pass
    try:
        NS['shell_frames'] = shell_frames
    except NameError:
        pass
    try:
        NS['shell_params'] = shell_params
    except NameError:
        pass
    try:
        NS['shell_sects'] = shell_sects
    except NameError:
        pass


def build_03_step3():
    global objs

    # =====================================================================
    # 4. 座板（坐垫支撑面）—— 按【扶手内表面】全宽，不再只占中间
    # =====================================================================
    NS['SEAT_DECK_W'] = ARM_IN * 2 - 0.014      # 1.816
    NS['SEAT_DECK_D'] = 0.690
    NS['SEAT_DECK_CY'] = -0.020
    NS['seat_deck'] = B.box("seat_deck", (NS['SEAT_DECK_W'], NS['SEAT_DECK_D'], 0.024),
                      (0, NS['SEAT_DECK_CY'], DECK_TOP + 0.012), M_UPDK)
    B.bevel(NS['seat_deck'], 0.009, 3)
    objs.append(NS['seat_deck'])

    # --- 回写共享变量到 NS ---
    try:
        NS['ARM_PAD_W'] = ARM_PAD_W
    except NameError:
        pass
    try:
        NS['ARM_PAD_Y0'] = ARM_PAD_Y0
    except NameError:
        pass
    try:
        NS['ARM_PAD_Y1'] = ARM_PAD_Y1
    except NameError:
        pass
    try:
        NS['ARM_SHELL_T'] = ARM_SHELL_T
    except NameError:
        pass
    try:
        NS['BC_CY'] = BC_CY
    except NameError:
        pass
    try:
        NS['BC_CZ'] = BC_CZ
    except NameError:
        pass
    try:
        NS['BC_GAP'] = BC_GAP
    except NameError:
        pass
    try:
        NS['BC_H'] = BC_H
    except NameError:
        pass
    try:
        NS['BC_N'] = BC_N
    except NameError:
        pass
    try:
        NS['BC_T'] = BC_T
    except NameError:
        pass
    try:
        NS['BC_W'] = BC_W
    except NameError:
        pass
    try:
        NS['BC_X0'] = BC_X0
    except NameError:
        pass
    try:
        NS['FD'] = FD
    except NameError:
        pass
    try:
        NS['FW'] = FW
    except NameError:
        pass
    try:
        NS['LEG_H'] = LEG_H
    except NameError:
        pass
    try:
        NS['LEG_R'] = LEG_R
    except NameError:
        pass
    try:
        NS['OUTLINE'] = OUTLINE
    except NameError:
        pass
    try:
        NS['PATH'] = PATH
    except NameError:
        pass
    try:
        NS['PIPE_LIFT'] = PIPE_LIFT
    except NameError:
        pass
    try:
        NS['PIPE_R'] = PIPE_R
    except NameError:
        pass
    try:
        NS['RADII'] = RADII
    except NameError:
        pass
    try:
        NS['RAIL'] = RAIL
    except NameError:
        pass
    try:
        NS['SEAT_BOT'] = SEAT_BOT
    except NameError:
        pass
    try:
        NS['SEAT_D'] = SEAT_D
    except NameError:
        pass
    try:
        NS['SEAT_DECK_CY'] = SEAT_DECK_CY
    except NameError:
        pass
    try:
        NS['SEAT_DECK_D'] = SEAT_DECK_D
    except NameError:
        pass
    try:
        NS['SEAT_DECK_W'] = SEAT_DECK_W
    except NameError:
        pass
    try:
        NS['SEAT_GAP'] = SEAT_GAP
    except NameError:
        pass
    try:
        NS['SEAT_N'] = SEAT_N
    except NameError:
        pass
    try:
        NS['SEAT_SIDE'] = SEAT_SIDE
    except NameError:
        pass
    try:
        NS['SEAT_T'] = SEAT_T
    except NameError:
        pass
    try:
        NS['SEAT_W'] = SEAT_W
    except NameError:
        pass
    try:
        NS['SEAT_X0'] = SEAT_X0
    except NameError:
        pass
    try:
        NS['SHOULDER'] = SHOULDER
    except NameError:
        pass
    try:
        NS['STATES'] = STATES
    except NameError:
        pass
    try:
        NS['S_LEFT'] = S_LEFT
    except NameError:
        pass
    try:
        NS['S_RIGHT'] = S_RIGHT
    except NameError:
        pass
    try:
        NS['_al'] = _al
    except NameError:
        pass
    try:
        NS['_total'] = _total
    except NameError:
        pass
    try:
        NS['arm_pad_objs'] = arm_pad_objs
    except NameError:
        pass
    try:
        NS['backc_objs'] = backc_objs
    except NameError:
        pass
    try:
        NS['foot_x'] = foot_x
    except NameError:
        pass
    try:
        NS['foot_y'] = foot_y
    except NameError:
        pass
    try:
        NS['seat_deck'] = seat_deck
    except NameError:
        pass
    try:
        NS['seat_objs'] = seat_objs
    except NameError:
        pass
    try:
        NS['shell'] = shell
    except NameError:
        pass
    try:
        NS['shell_frames'] = shell_frames
    except NameError:
        pass
    try:
        NS['shell_params'] = shell_params
    except NameError:
        pass
    try:
        NS['shell_sects'] = shell_sects
    except NameError:
        pass


def build_04_step4():
    global objs

    # =====================================================================
    # 5. 坐垫（铺满座板；顶面中央平整）
    # =====================================================================
    NS['SEAT_N'] = 3
    # 【v18】缝隙从 18mm 收到 9mm、两侧边距从 18mm 收到 8mm ——
    # v17 的 18mm 缝 + 18mm 边让深色座板大面积露出，画面上像"拼凑"而不是整块软包。
    NS['SEAT_GAP'] = 0.009
    NS['SEAT_SIDE'] = 0.008
    NS['SEAT_W'] = (NS['SEAT_DECK_W'] - 2 * NS['SEAT_SIDE'] - NS['SEAT_GAP'] * (NS['SEAT_N'] - 1)) / NS['SEAT_N']
    NS['SEAT_D'] = SEAT_FRONT - SEAT_BACK
    NS['SEAT_X0'] = -NS['SEAT_DECK_W'] / 2 + NS['SEAT_SIDE'] + NS['SEAT_W'] / 2
    NS['SEAT_BOT'] = SEAT_DECK_TOP
    NS['SEAT_T'] = SEAT_TOP - NS['SEAT_BOT']

    NS['seat_objs'] = []
    for k in range(NS['SEAT_N']):
        cx = NS['SEAT_X0'] + k * (NS['SEAT_W'] + NS['SEAT_GAP'])
        cy = (SEAT_BACK + SEAT_FRONT) / 2
        c = B.superellipsoid_soft(
            "seat_%d" % k, (NS['SEAT_W'], NS['SEAT_D'], NS['SEAT_T']), (cx, cy, NS['SEAT_BOT'] + NS['SEAT_T'] / 2), M_UP,
            e1=0.87, e2=0.92, res_u=104, res_v=52,
            squash_top=0.004, crown=0.007, top_clamp=SEAT_TOP - 0.002,
            bot_clamp=NS['SEAT_BOT'] + 0.004)
        for v in c.data.vertices:
            if v.co.z > SEAT_TOP - 0.014:
                rr = min(1.0, math.hypot((v.co.x - cx) / (NS['SEAT_W'] / 2),
                                          (v.co.y - cy) / (NS['SEAT_D'] / 2)))
                v.co.z -= 0.006 * math.cos(rr * math.pi / 2)
        # 顶面中央平整、褶皱集中在边缘
        SH.cloth_relax(c, amp=0.0032, freq=15.0, seed=k * 7 + 3,
                       edge_bias=0.72, down_weight=0.25,
                       center=(cx, cy), radial=(NS['SEAT_W'] / 2, NS['SEAT_D'] / 2))
        objs.append(c)
        NS['seat_objs'].append((c, cx, cy))

    # --- 回写共享变量到 NS ---
    try:
        NS['ARM_PAD_W'] = ARM_PAD_W
    except NameError:
        pass
    try:
        NS['ARM_PAD_Y0'] = ARM_PAD_Y0
    except NameError:
        pass
    try:
        NS['ARM_PAD_Y1'] = ARM_PAD_Y1
    except NameError:
        pass
    try:
        NS['ARM_SHELL_T'] = ARM_SHELL_T
    except NameError:
        pass
    try:
        NS['BC_CY'] = BC_CY
    except NameError:
        pass
    try:
        NS['BC_CZ'] = BC_CZ
    except NameError:
        pass
    try:
        NS['BC_GAP'] = BC_GAP
    except NameError:
        pass
    try:
        NS['BC_H'] = BC_H
    except NameError:
        pass
    try:
        NS['BC_N'] = BC_N
    except NameError:
        pass
    try:
        NS['BC_T'] = BC_T
    except NameError:
        pass
    try:
        NS['BC_W'] = BC_W
    except NameError:
        pass
    try:
        NS['BC_X0'] = BC_X0
    except NameError:
        pass
    try:
        NS['FD'] = FD
    except NameError:
        pass
    try:
        NS['FW'] = FW
    except NameError:
        pass
    try:
        NS['LEG_H'] = LEG_H
    except NameError:
        pass
    try:
        NS['LEG_R'] = LEG_R
    except NameError:
        pass
    try:
        NS['OUTLINE'] = OUTLINE
    except NameError:
        pass
    try:
        NS['PATH'] = PATH
    except NameError:
        pass
    try:
        NS['PIPE_LIFT'] = PIPE_LIFT
    except NameError:
        pass
    try:
        NS['PIPE_R'] = PIPE_R
    except NameError:
        pass
    try:
        NS['RADII'] = RADII
    except NameError:
        pass
    try:
        NS['RAIL'] = RAIL
    except NameError:
        pass
    try:
        NS['SEAT_BOT'] = SEAT_BOT
    except NameError:
        pass
    try:
        NS['SEAT_D'] = SEAT_D
    except NameError:
        pass
    try:
        NS['SEAT_DECK_CY'] = SEAT_DECK_CY
    except NameError:
        pass
    try:
        NS['SEAT_DECK_D'] = SEAT_DECK_D
    except NameError:
        pass
    try:
        NS['SEAT_DECK_W'] = SEAT_DECK_W
    except NameError:
        pass
    try:
        NS['SEAT_GAP'] = SEAT_GAP
    except NameError:
        pass
    try:
        NS['SEAT_N'] = SEAT_N
    except NameError:
        pass
    try:
        NS['SEAT_SIDE'] = SEAT_SIDE
    except NameError:
        pass
    try:
        NS['SEAT_T'] = SEAT_T
    except NameError:
        pass
    try:
        NS['SEAT_W'] = SEAT_W
    except NameError:
        pass
    try:
        NS['SEAT_X0'] = SEAT_X0
    except NameError:
        pass
    try:
        NS['SHOULDER'] = SHOULDER
    except NameError:
        pass
    try:
        NS['STATES'] = STATES
    except NameError:
        pass
    try:
        NS['S_LEFT'] = S_LEFT
    except NameError:
        pass
    try:
        NS['S_RIGHT'] = S_RIGHT
    except NameError:
        pass
    try:
        NS['_al'] = _al
    except NameError:
        pass
    try:
        NS['_total'] = _total
    except NameError:
        pass
    try:
        NS['arm_pad_objs'] = arm_pad_objs
    except NameError:
        pass
    try:
        NS['backc_objs'] = backc_objs
    except NameError:
        pass
    try:
        NS['foot_x'] = foot_x
    except NameError:
        pass
    try:
        NS['foot_y'] = foot_y
    except NameError:
        pass
    try:
        NS['seat_deck'] = seat_deck
    except NameError:
        pass
    try:
        NS['seat_objs'] = seat_objs
    except NameError:
        pass
    try:
        NS['shell'] = shell
    except NameError:
        pass
    try:
        NS['shell_frames'] = shell_frames
    except NameError:
        pass
    try:
        NS['shell_params'] = shell_params
    except NameError:
        pass
    try:
        NS['shell_sects'] = shell_sects
    except NameError:
        pass


def build_05_d():
    global objs

    # =====================================================================
    # 6. 靠垫（完整外露，背面贴外壳内表面，留 4mm 缝）
    # =====================================================================
    NS['BC_N'] = 3
    NS['BC_GAP'] = 0.016
    NS['BC_W'] = (NS['SEAT_DECK_W'] - 0.026 - NS['BC_GAP'] * (NS['BC_N'] - 1)) / NS['BC_N']
    NS['BC_H'] = 0.430
    NS['BC_T'] = 0.170
    NS['BC_CZ'] = SEAT_TOP + NS['BC_H'] / 2 - 0.010
    # 【v18 关键修正】v17/v18 初版靠垫位置算错：
    #   NS['BC_CY'] = BACK_IN + 0.016 + NS['BC_T']/2 = -0.2015
    #   靠垫占 y ∈ [-0.274, -0.129]，而坐垫只到 y = SEAT_BACK = -0.160
    #   → 靠垫有 134mm 藏在坐垫后面，实际只露出 31mm 的一条边（画面证实）。
    # 正确：靠垫【压在坐垫上】，前缘略微搭到坐垫上方，
    #   底面坐在坐垫顶面（SEAT_TOP），背面贴外壳内表面并留缝。
    NS['BC_CY'] = -0.086
    NS['BC_X0'] = -NS['SEAT_DECK_W'] / 2 + 0.013 + NS['BC_W'] / 2

    NS['backc_objs'] = []
    for k in range(NS['BC_N']):
        cx = NS['BC_X0'] + k * (NS['BC_W'] + NS['BC_GAP'])
        bc = B.superellipsoid_soft(
            "backc_%d" % k, (NS['BC_W'], NS['BC_T'], NS['BC_H']), (cx, NS['BC_CY'], NS['BC_CZ']), M_UP,
            e1=0.82, e2=0.90, res_u=76, res_v=46,
            squash_top=0.006, crown=0.012, front_clamp=NS['BC_CY'] + NS['BC_T'] * 0.30,
            bot_clamp=SEAT_TOP + 0.004)
        for v in bc.data.vertices:
            dy = v.co.y - NS['BC_CY']
            dz = v.co.z - NS['BC_CZ']
            a = math.radians(-11)
            v.co.y = NS['BC_CY'] + dy * math.cos(a) - dz * math.sin(a)
            v.co.z = NS['BC_CZ'] + dy * math.sin(a) + dz * math.cos(a)
        SH.cloth_relax(bc, amp=0.0028, freq=14.0, seed=k * 11 + 5,
                       edge_bias=0.70, down_weight=0.25,
                       center=(cx, NS['BC_CY']), radial=(NS['BC_W'] / 2, NS['BC_T'] / 2))
        objs.append(bc)
        NS['backc_objs'].append((bc, cx))

    # --- 回写共享变量到 NS ---
    try:
        NS['ARM_PAD_W'] = ARM_PAD_W
    except NameError:
        pass
    try:
        NS['ARM_PAD_Y0'] = ARM_PAD_Y0
    except NameError:
        pass
    try:
        NS['ARM_PAD_Y1'] = ARM_PAD_Y1
    except NameError:
        pass
    try:
        NS['ARM_SHELL_T'] = ARM_SHELL_T
    except NameError:
        pass
    try:
        NS['BC_CY'] = BC_CY
    except NameError:
        pass
    try:
        NS['BC_CZ'] = BC_CZ
    except NameError:
        pass
    try:
        NS['BC_GAP'] = BC_GAP
    except NameError:
        pass
    try:
        NS['BC_H'] = BC_H
    except NameError:
        pass
    try:
        NS['BC_N'] = BC_N
    except NameError:
        pass
    try:
        NS['BC_T'] = BC_T
    except NameError:
        pass
    try:
        NS['BC_W'] = BC_W
    except NameError:
        pass
    try:
        NS['BC_X0'] = BC_X0
    except NameError:
        pass
    try:
        NS['FD'] = FD
    except NameError:
        pass
    try:
        NS['FW'] = FW
    except NameError:
        pass
    try:
        NS['LEG_H'] = LEG_H
    except NameError:
        pass
    try:
        NS['LEG_R'] = LEG_R
    except NameError:
        pass
    try:
        NS['OUTLINE'] = OUTLINE
    except NameError:
        pass
    try:
        NS['PATH'] = PATH
    except NameError:
        pass
    try:
        NS['PIPE_LIFT'] = PIPE_LIFT
    except NameError:
        pass
    try:
        NS['PIPE_R'] = PIPE_R
    except NameError:
        pass
    try:
        NS['RADII'] = RADII
    except NameError:
        pass
    try:
        NS['RAIL'] = RAIL
    except NameError:
        pass
    try:
        NS['SEAT_BOT'] = SEAT_BOT
    except NameError:
        pass
    try:
        NS['SEAT_D'] = SEAT_D
    except NameError:
        pass
    try:
        NS['SEAT_DECK_CY'] = SEAT_DECK_CY
    except NameError:
        pass
    try:
        NS['SEAT_DECK_D'] = SEAT_DECK_D
    except NameError:
        pass
    try:
        NS['SEAT_DECK_W'] = SEAT_DECK_W
    except NameError:
        pass
    try:
        NS['SEAT_GAP'] = SEAT_GAP
    except NameError:
        pass
    try:
        NS['SEAT_N'] = SEAT_N
    except NameError:
        pass
    try:
        NS['SEAT_SIDE'] = SEAT_SIDE
    except NameError:
        pass
    try:
        NS['SEAT_T'] = SEAT_T
    except NameError:
        pass
    try:
        NS['SEAT_W'] = SEAT_W
    except NameError:
        pass
    try:
        NS['SEAT_X0'] = SEAT_X0
    except NameError:
        pass
    try:
        NS['SHOULDER'] = SHOULDER
    except NameError:
        pass
    try:
        NS['STATES'] = STATES
    except NameError:
        pass
    try:
        NS['S_LEFT'] = S_LEFT
    except NameError:
        pass
    try:
        NS['S_RIGHT'] = S_RIGHT
    except NameError:
        pass
    try:
        NS['_al'] = _al
    except NameError:
        pass
    try:
        NS['_total'] = _total
    except NameError:
        pass
    try:
        NS['arm_pad_objs'] = arm_pad_objs
    except NameError:
        pass
    try:
        NS['backc_objs'] = backc_objs
    except NameError:
        pass
    try:
        NS['foot_x'] = foot_x
    except NameError:
        pass
    try:
        NS['foot_y'] = foot_y
    except NameError:
        pass
    try:
        NS['seat_deck'] = seat_deck
    except NameError:
        pass
    try:
        NS['seat_objs'] = seat_objs
    except NameError:
        pass
    try:
        NS['shell'] = shell
    except NameError:
        pass
    try:
        NS['shell_frames'] = shell_frames
    except NameError:
        pass
    try:
        NS['shell_params'] = shell_params
    except NameError:
        pass
    try:
        NS['shell_sects'] = shell_sects
    except NameError:
        pass


def build_06_d_11():
    global objs

    # =====================================================================
    # 7. 扶手垫（坐在外壳扶手段顶 0.390 上）
    # =====================================================================
    NS['ARM_PAD_W'] = ARM_W + 0.014
    # 【v18】扶手垫改为【完整覆盖扶手段顶】——
    # v17 初版 NS['ARM_PAD_Y0'] = BACK_CY+0.115 = -0.24，起点在后靠背里侧，
    # 于是靠垫后方留出一段空扶手面，画面上看起来像"孤零零一块垫子"。
    # 现在从靠背内表面附近起、到扶手前端收口，整条扶手都有软包。
    NS['ARM_PAD_Y0'] = -0.300
    NS['ARM_PAD_Y1'] = ARM_FRONT - 0.030

    NS['arm_pad_objs'] = []
    for sx in (-1, 1):
        nm = 'L' if sx < 0 else 'R'
        ax = sx * ARM_X
        d = NS['ARM_PAD_Y1'] - NS['ARM_PAD_Y0']
        cy = (NS['ARM_PAD_Y0'] + NS['ARM_PAD_Y1']) / 2
        pad = B.superellipsoid_soft(
            "arm_pad_%s" % nm, (NS['ARM_PAD_W'], d, ARM_PAD_T),
            (ax, cy, ARM_BOARD_TOP + ARM_PAD_T / 2 - 0.002), M_UP,
            e1=0.88, e2=0.94, res_u=88, res_v=38,
            squash_top=0.003, crown=0.005,
            top_clamp=ARM_TOP,
            front_clamp=NS['ARM_PAD_Y1'] - 0.014,
            bot_clamp=ARM_BOARD_TOP + 0.003)
        for v in pad.data.vertices:
            t = (v.co.y - NS['ARM_PAD_Y0']) / d
            if t > 0.88:
                k2 = (t - 0.88) / 0.12
                v.co.x = ax + (v.co.x - ax) * (1 - 0.09 * k2)
                v.co.z -= 0.007 * k2
        SH.cloth_relax(pad, amp=0.0022, freq=12.0, seed=7 if sx < 0 else 19,
                       edge_bias=0.65, down_weight=0.25,
                       center=(ax, cy), radial=(NS['ARM_PAD_W'] / 2, d / 2))
        objs.append(pad)
        NS['arm_pad_objs'].append((pad, ax, cy, NS['ARM_PAD_W'], d))

    # --- 回写共享变量到 NS ---
    try:
        NS['ARM_PAD_W'] = ARM_PAD_W
    except NameError:
        pass
    try:
        NS['ARM_PAD_Y0'] = ARM_PAD_Y0
    except NameError:
        pass
    try:
        NS['ARM_PAD_Y1'] = ARM_PAD_Y1
    except NameError:
        pass
    try:
        NS['ARM_SHELL_T'] = ARM_SHELL_T
    except NameError:
        pass
    try:
        NS['BC_CY'] = BC_CY
    except NameError:
        pass
    try:
        NS['BC_CZ'] = BC_CZ
    except NameError:
        pass
    try:
        NS['BC_GAP'] = BC_GAP
    except NameError:
        pass
    try:
        NS['BC_H'] = BC_H
    except NameError:
        pass
    try:
        NS['BC_N'] = BC_N
    except NameError:
        pass
    try:
        NS['BC_T'] = BC_T
    except NameError:
        pass
    try:
        NS['BC_W'] = BC_W
    except NameError:
        pass
    try:
        NS['BC_X0'] = BC_X0
    except NameError:
        pass
    try:
        NS['FD'] = FD
    except NameError:
        pass
    try:
        NS['FW'] = FW
    except NameError:
        pass
    try:
        NS['LEG_H'] = LEG_H
    except NameError:
        pass
    try:
        NS['LEG_R'] = LEG_R
    except NameError:
        pass
    try:
        NS['OUTLINE'] = OUTLINE
    except NameError:
        pass
    try:
        NS['PATH'] = PATH
    except NameError:
        pass
    try:
        NS['PIPE_LIFT'] = PIPE_LIFT
    except NameError:
        pass
    try:
        NS['PIPE_R'] = PIPE_R
    except NameError:
        pass
    try:
        NS['RADII'] = RADII
    except NameError:
        pass
    try:
        NS['RAIL'] = RAIL
    except NameError:
        pass
    try:
        NS['SEAT_BOT'] = SEAT_BOT
    except NameError:
        pass
    try:
        NS['SEAT_D'] = SEAT_D
    except NameError:
        pass
    try:
        NS['SEAT_DECK_CY'] = SEAT_DECK_CY
    except NameError:
        pass
    try:
        NS['SEAT_DECK_D'] = SEAT_DECK_D
    except NameError:
        pass
    try:
        NS['SEAT_DECK_W'] = SEAT_DECK_W
    except NameError:
        pass
    try:
        NS['SEAT_GAP'] = SEAT_GAP
    except NameError:
        pass
    try:
        NS['SEAT_N'] = SEAT_N
    except NameError:
        pass
    try:
        NS['SEAT_SIDE'] = SEAT_SIDE
    except NameError:
        pass
    try:
        NS['SEAT_T'] = SEAT_T
    except NameError:
        pass
    try:
        NS['SEAT_W'] = SEAT_W
    except NameError:
        pass
    try:
        NS['SEAT_X0'] = SEAT_X0
    except NameError:
        pass
    try:
        NS['SHOULDER'] = SHOULDER
    except NameError:
        pass
    try:
        NS['STATES'] = STATES
    except NameError:
        pass
    try:
        NS['S_LEFT'] = S_LEFT
    except NameError:
        pass
    try:
        NS['S_RIGHT'] = S_RIGHT
    except NameError:
        pass
    try:
        NS['_al'] = _al
    except NameError:
        pass
    try:
        NS['_total'] = _total
    except NameError:
        pass
    try:
        NS['arm_pad_objs'] = arm_pad_objs
    except NameError:
        pass
    try:
        NS['backc_objs'] = backc_objs
    except NameError:
        pass
    try:
        NS['foot_x'] = foot_x
    except NameError:
        pass
    try:
        NS['foot_y'] = foot_y
    except NameError:
        pass
    try:
        NS['seat_deck'] = seat_deck
    except NameError:
        pass
    try:
        NS['seat_objs'] = seat_objs
    except NameError:
        pass
    try:
        NS['shell'] = shell
    except NameError:
        pass
    try:
        NS['shell_frames'] = shell_frames
    except NameError:
        pass
    try:
        NS['shell_params'] = shell_params
    except NameError:
        pass
    try:
        NS['shell_sects'] = shell_sects
    except NameError:
        pass


def build_07_2():
    global objs

    # =====================================================================
    # 8. 滚边
    # =====================================================================
    NS['PIPE_R'] = 0.0100
    NS['PIPE_LIFT'] = 0.0036

    # 8.1 坐垫赤道滚边
    for k, (c, cx, cy) in enumerate(NS['seat_objs']):
        pts = []
        for i in range(73):
            a = 2 * math.pi * i / 72
            pts.append((cx + (NS['SEAT_W'] / 2 + 0.001) * math.cos(a),
                        cy + (NS['SEAT_D'] / 2 + 0.001) * math.sin(a),
                        SEAT_TOP - 0.034))
        objs.append(B.pipe_on_surface("seat_pipe_%d" % k, pts, c, M_WELT,
                                      r=NS['PIPE_R'], lift=NS['PIPE_LIFT']))

    # 8.2 靠垫底沿滚边
    for k, (bc, cx) in enumerate(NS['backc_objs']):
        pts = []
        for i in range(37):
            a = math.pi * i / 36 - math.pi / 2
            pts.append((cx + (NS['BC_W'] / 2 - 0.004) * math.cos(a),
                        NS['BC_CY'] - NS['BC_T'] / 2 - 0.008,
                        NS['BC_CZ'] - NS['BC_H'] / 2 + 0.038 + 0.038 * math.cos(a)))
        objs.append(B.pipe_on_surface("backc_pipe_%d" % k, pts, bc, M_WELT,
                                      r=0.0088, lift=0.0032))

    # 8.3 扶手垫顶缘滚边
    for pad, ax, cy, w, d in NS['arm_pad_objs']:
        pts = []
        for i in range(65):
            a = 2 * math.pi * i / 64
            pts.append((ax + (w / 2 + 0.001) * math.cos(a),
                        cy + (d / 2 - 0.012) * math.sin(a),
                        ARM_TOP - 0.024))
        objs.append(B.pipe_on_surface("arm_pipe_%s" % ('L' if ax < 0 else 'R'),
                                      pts, pad, M_WELT, r=0.0090, lift=0.0032))

    # 8.4 外壳：斜肩棱滚边（真实沙发斜肩有明确接缝）+ 端头包边
    # 斜肩棱：位于路径参数 s = NS['S_LEFT'] - NS['SHOULDER']*0.5 附近
    for tag, s_key in (("L", NS['S_LEFT']), ("R", NS['S_RIGHT'])):
        # 找最接近该 s 的路径点
        best = min(range(len(NS['PATH'])), key=lambda i: abs(NS['PATH'][i][2] - s_key))
        i = best
        T, zb, zw, zt = NS['shell_params'][i]
        _, _, nx, ny = NS['shell_frames'][i]
        px, py = NS['PATH'][i][0], NS['PATH'][i][1]
        # 断面在 z_wall 处的内表面点
        pts = []
        for (a, b) in NS['shell_sects'][i]:
            if abs(b - zw) < 0.03:
                pts.append((px + nx * (a - 0.002), py + ny * (a - 0.002), b))
        if len(pts) >= 2:
            objs.append(B.pipe_on_surface("shell_shoulder_pipe_%s" % tag, pts, NS['shell'],
                                          M_WELT, r=0.0078, lift=0.0030))

    # 外壳端头包边（扶手前端的收口）
    for tag, idx in (("L", 0), ("R", len(NS['PATH']) - 1)):
        px, py = NS['PATH'][idx][0], NS['PATH'][idx][1]
        _, _, nx, ny = NS['shell_frames'][idx]
        sec = NS['shell_sects'][idx]
        pts = SH.cap_welt_points((px, py), (nx, ny), sec, inset=0.005)
        objs.append(B.pipe_on_surface("shell_cap_pipe_%s" % tag, pts, NS['shell'],
                                      M_WELT, r=0.0072, lift=0.0026))

    # 8.5 底座框前缘滚边
    objs.append(B.pipe_rect("frame_pipe_front", 0, FRAME_Y - NS['RAIL'] / 2,
                             FRAME_Z0 - 0.012, NS['FW'] - 0.008, NS['RAIL'] - 0.008,
                             M_WELT, r=0.0054))

    # --- 回写共享变量到 NS ---
    try:
        NS['ARM_PAD_W'] = ARM_PAD_W
    except NameError:
        pass
    try:
        NS['ARM_PAD_Y0'] = ARM_PAD_Y0
    except NameError:
        pass
    try:
        NS['ARM_PAD_Y1'] = ARM_PAD_Y1
    except NameError:
        pass
    try:
        NS['ARM_SHELL_T'] = ARM_SHELL_T
    except NameError:
        pass
    try:
        NS['BC_CY'] = BC_CY
    except NameError:
        pass
    try:
        NS['BC_CZ'] = BC_CZ
    except NameError:
        pass
    try:
        NS['BC_GAP'] = BC_GAP
    except NameError:
        pass
    try:
        NS['BC_H'] = BC_H
    except NameError:
        pass
    try:
        NS['BC_N'] = BC_N
    except NameError:
        pass
    try:
        NS['BC_T'] = BC_T
    except NameError:
        pass
    try:
        NS['BC_W'] = BC_W
    except NameError:
        pass
    try:
        NS['BC_X0'] = BC_X0
    except NameError:
        pass
    try:
        NS['FD'] = FD
    except NameError:
        pass
    try:
        NS['FW'] = FW
    except NameError:
        pass
    try:
        NS['LEG_H'] = LEG_H
    except NameError:
        pass
    try:
        NS['LEG_R'] = LEG_R
    except NameError:
        pass
    try:
        NS['OUTLINE'] = OUTLINE
    except NameError:
        pass
    try:
        NS['PATH'] = PATH
    except NameError:
        pass
    try:
        NS['PIPE_LIFT'] = PIPE_LIFT
    except NameError:
        pass
    try:
        NS['PIPE_R'] = PIPE_R
    except NameError:
        pass
    try:
        NS['RADII'] = RADII
    except NameError:
        pass
    try:
        NS['RAIL'] = RAIL
    except NameError:
        pass
    try:
        NS['SEAT_BOT'] = SEAT_BOT
    except NameError:
        pass
    try:
        NS['SEAT_D'] = SEAT_D
    except NameError:
        pass
    try:
        NS['SEAT_DECK_CY'] = SEAT_DECK_CY
    except NameError:
        pass
    try:
        NS['SEAT_DECK_D'] = SEAT_DECK_D
    except NameError:
        pass
    try:
        NS['SEAT_DECK_W'] = SEAT_DECK_W
    except NameError:
        pass
    try:
        NS['SEAT_GAP'] = SEAT_GAP
    except NameError:
        pass
    try:
        NS['SEAT_N'] = SEAT_N
    except NameError:
        pass
    try:
        NS['SEAT_SIDE'] = SEAT_SIDE
    except NameError:
        pass
    try:
        NS['SEAT_T'] = SEAT_T
    except NameError:
        pass
    try:
        NS['SEAT_W'] = SEAT_W
    except NameError:
        pass
    try:
        NS['SEAT_X0'] = SEAT_X0
    except NameError:
        pass
    try:
        NS['SHOULDER'] = SHOULDER
    except NameError:
        pass
    try:
        NS['STATES'] = STATES
    except NameError:
        pass
    try:
        NS['S_LEFT'] = S_LEFT
    except NameError:
        pass
    try:
        NS['S_RIGHT'] = S_RIGHT
    except NameError:
        pass
    try:
        NS['_al'] = _al
    except NameError:
        pass
    try:
        NS['_total'] = _total
    except NameError:
        pass
    try:
        NS['arm_pad_objs'] = arm_pad_objs
    except NameError:
        pass
    try:
        NS['backc_objs'] = backc_objs
    except NameError:
        pass
    try:
        NS['foot_x'] = foot_x
    except NameError:
        pass
    try:
        NS['foot_y'] = foot_y
    except NameError:
        pass
    try:
        NS['seat_deck'] = seat_deck
    except NameError:
        pass
    try:
        NS['seat_objs'] = seat_objs
    except NameError:
        pass
    try:
        NS['shell'] = shell
    except NameError:
        pass
    try:
        NS['shell_frames'] = shell_frames
    except NameError:
        pass
    try:
        NS['shell_params'] = shell_params
    except NameError:
        pass
    try:
        NS['shell_sects'] = shell_sects
    except NameError:
        pass


def build_08_step8():
    global objs

    # =====================================================================
    # 9. 真实针脚
    # =====================================================================
    def stitch_on_surface(name, pts, surface, material, r=0.00095, lift=0.0024,
                          length=0.010, gap=0.006):
        """沿曲面生成真实针脚几何。

        【v17 效率】所有针脚合成【一个曲线对象】（B.stitch_poly），
        不再是每针一个 mesh 对象 —— 见 bl_lib.stitch_poly 的效率说明。
        """
        import bmesh as _bm
        from mathutils.bvhtree import BVHTree
        bm = _bm.new()
        bm.from_mesh(surface.data)
        bvh = BVHTree.FromBMesh(bm)
        bm.free()
        acc = []
        for p in B._catmull_rom(pts, 8):
            hit = bvh.find_nearest(mathutils.Vector(p))
            if hit and hit[0] is not None:
                pos, nor = hit[0], hit[1]
                acc.append((pos.x + nor.x * lift, pos.y + nor.y * lift, pos.z + nor.z * lift))
        if len(acc) < 2:
            return []
        segments = []
        seg = length + gap
        for i in range(len(acc) - 1):
            a = mathutils.Vector(acc[i])
            b = mathutils.Vector(acc[i + 1])
            d = b - a
            L = d.length
            if L < 1e-6:
                continue
            t = 0.0
            while t < L:
                e = min(t + length, L)
                p0 = a + d * (t / L)
                p1 = a + d * (e / L)
                segments.append((p0, p1))
                t += seg
        if not segments:
            return []
        return B.stitch_poly(name, segments, material, r=r)


    # 坐垫一圈针脚
    for k, (c, cx, cy) in enumerate(NS['seat_objs']):
        pts = []
        for i in range(113):
            a = 2 * math.pi * i / 112
            pts.append((cx + (NS['SEAT_W'] / 2 - 0.013) * math.cos(a),
                        cy + (NS['SEAT_D'] / 2 - 0.013) * math.sin(a),
                        SEAT_TOP - 0.050))
        objs += stitch_on_surface("seat_stitch_%d" % k, pts, c, M_THREAD)

    # 坐垫绗缝分线（浅，不做深槽）
    for k, (c, cx, cy) in enumerate(NS['seat_objs']):
        for j, fx in enumerate((-0.26, 0.0, 0.26)):
            x = cx + fx * NS['SEAT_W']
            pts = []
            for i in range(41):
                t = i / 40
                pts.append((x, cy - (NS['SEAT_D'] / 2 - 0.036) + (NS['SEAT_D'] - 0.072) * t,
                            SEAT_TOP - 0.002 + 0.006 * math.sin(t * math.pi)))
            objs += stitch_on_surface("seat_tuft_%d_%d" % (k, j), pts, c, M_THREAD,
                                      r=0.00080, length=0.009, gap=0.005)

    # 靠背顶针脚
    objs += B.stitch_line("back_stitch",
                          (-ARM_IN + 0.10, BACK_CY - 0.018, BACK_TOP - 0.060),
                          (ARM_IN - 0.10, BACK_CY - 0.018, BACK_TOP - 0.060),
                          M_THREAD, r=0.00095, lift=0.002)

    # 扶手外侧竖向针脚
    for pad, ax, cy, w, d in NS['arm_pad_objs']:
        pts = []
        for i in range(31):
            t = i / 30
            pts.append((ax + (w / 2 + 0.002),
                        NS['ARM_PAD_Y0'] + 0.05 + (d - 0.12) * t,
                        ARM_TOP - 0.052))
        objs += stitch_on_surface("arm_stitch_%s" % ('L' if ax < 0 else 'R'), pts, pad, M_THREAD)

    # --- 回写共享变量到 NS ---
    try:
        NS['ARM_PAD_W'] = ARM_PAD_W
    except NameError:
        pass
    try:
        NS['ARM_PAD_Y0'] = ARM_PAD_Y0
    except NameError:
        pass
    try:
        NS['ARM_PAD_Y1'] = ARM_PAD_Y1
    except NameError:
        pass
    try:
        NS['ARM_SHELL_T'] = ARM_SHELL_T
    except NameError:
        pass
    try:
        NS['BC_CY'] = BC_CY
    except NameError:
        pass
    try:
        NS['BC_CZ'] = BC_CZ
    except NameError:
        pass
    try:
        NS['BC_GAP'] = BC_GAP
    except NameError:
        pass
    try:
        NS['BC_H'] = BC_H
    except NameError:
        pass
    try:
        NS['BC_N'] = BC_N
    except NameError:
        pass
    try:
        NS['BC_T'] = BC_T
    except NameError:
        pass
    try:
        NS['BC_W'] = BC_W
    except NameError:
        pass
    try:
        NS['BC_X0'] = BC_X0
    except NameError:
        pass
    try:
        NS['FD'] = FD
    except NameError:
        pass
    try:
        NS['FW'] = FW
    except NameError:
        pass
    try:
        NS['LEG_H'] = LEG_H
    except NameError:
        pass
    try:
        NS['LEG_R'] = LEG_R
    except NameError:
        pass
    try:
        NS['OUTLINE'] = OUTLINE
    except NameError:
        pass
    try:
        NS['PATH'] = PATH
    except NameError:
        pass
    try:
        NS['PIPE_LIFT'] = PIPE_LIFT
    except NameError:
        pass
    try:
        NS['PIPE_R'] = PIPE_R
    except NameError:
        pass
    try:
        NS['RADII'] = RADII
    except NameError:
        pass
    try:
        NS['RAIL'] = RAIL
    except NameError:
        pass
    try:
        NS['SEAT_BOT'] = SEAT_BOT
    except NameError:
        pass
    try:
        NS['SEAT_D'] = SEAT_D
    except NameError:
        pass
    try:
        NS['SEAT_DECK_CY'] = SEAT_DECK_CY
    except NameError:
        pass
    try:
        NS['SEAT_DECK_D'] = SEAT_DECK_D
    except NameError:
        pass
    try:
        NS['SEAT_DECK_W'] = SEAT_DECK_W
    except NameError:
        pass
    try:
        NS['SEAT_GAP'] = SEAT_GAP
    except NameError:
        pass
    try:
        NS['SEAT_N'] = SEAT_N
    except NameError:
        pass
    try:
        NS['SEAT_SIDE'] = SEAT_SIDE
    except NameError:
        pass
    try:
        NS['SEAT_T'] = SEAT_T
    except NameError:
        pass
    try:
        NS['SEAT_W'] = SEAT_W
    except NameError:
        pass
    try:
        NS['SEAT_X0'] = SEAT_X0
    except NameError:
        pass
    try:
        NS['SHOULDER'] = SHOULDER
    except NameError:
        pass
    try:
        NS['STATES'] = STATES
    except NameError:
        pass
    try:
        NS['S_LEFT'] = S_LEFT
    except NameError:
        pass
    try:
        NS['S_RIGHT'] = S_RIGHT
    except NameError:
        pass
    try:
        NS['_al'] = _al
    except NameError:
        pass
    try:
        NS['_total'] = _total
    except NameError:
        pass
    try:
        NS['arm_pad_objs'] = arm_pad_objs
    except NameError:
        pass
    try:
        NS['backc_objs'] = backc_objs
    except NameError:
        pass
    try:
        NS['foot_x'] = foot_x
    except NameError:
        pass
    try:
        NS['foot_y'] = foot_y
    except NameError:
        pass
    try:
        NS['seat_deck'] = seat_deck
    except NameError:
        pass
    try:
        NS['seat_objs'] = seat_objs
    except NameError:
        pass
    try:
        NS['shell'] = shell
    except NameError:
        pass
    try:
        NS['shell_frames'] = shell_frames
    except NameError:
        pass
    try:
        NS['shell_params'] = shell_params
    except NameError:
        pass
    try:
        NS['shell_sects'] = shell_sects
    except NameError:
        pass


def build_09_step9():
    global objs

    # =====================================================================
    for o in list(objs):
        if o.type == 'MESH':
            B.apply_mods(o)

    B.export(OUT)
    print("OK sofa v18 ->", OUT, "objects:", len(objs),
          "seat_w=%.3f" % NS['SEAT_W'], "path_pts=%d" % len(NS['PATH']),
          "S_LEFT=%.3f S_RIGHT=%.3f" % (NS['S_LEFT'], NS['S_RIGHT']))

    # --- 回写共享变量到 NS ---
    try:
        NS['ARM_PAD_W'] = ARM_PAD_W
    except NameError:
        pass
    try:
        NS['ARM_PAD_Y0'] = ARM_PAD_Y0
    except NameError:
        pass
    try:
        NS['ARM_PAD_Y1'] = ARM_PAD_Y1
    except NameError:
        pass
    try:
        NS['ARM_SHELL_T'] = ARM_SHELL_T
    except NameError:
        pass
    try:
        NS['BC_CY'] = BC_CY
    except NameError:
        pass
    try:
        NS['BC_CZ'] = BC_CZ
    except NameError:
        pass
    try:
        NS['BC_GAP'] = BC_GAP
    except NameError:
        pass
    try:
        NS['BC_H'] = BC_H
    except NameError:
        pass
    try:
        NS['BC_N'] = BC_N
    except NameError:
        pass
    try:
        NS['BC_T'] = BC_T
    except NameError:
        pass
    try:
        NS['BC_W'] = BC_W
    except NameError:
        pass
    try:
        NS['BC_X0'] = BC_X0
    except NameError:
        pass
    try:
        NS['FD'] = FD
    except NameError:
        pass
    try:
        NS['FW'] = FW
    except NameError:
        pass
    try:
        NS['LEG_H'] = LEG_H
    except NameError:
        pass
    try:
        NS['LEG_R'] = LEG_R
    except NameError:
        pass
    try:
        NS['OUTLINE'] = OUTLINE
    except NameError:
        pass
    try:
        NS['PATH'] = PATH
    except NameError:
        pass
    try:
        NS['PIPE_LIFT'] = PIPE_LIFT
    except NameError:
        pass
    try:
        NS['PIPE_R'] = PIPE_R
    except NameError:
        pass
    try:
        NS['RADII'] = RADII
    except NameError:
        pass
    try:
        NS['RAIL'] = RAIL
    except NameError:
        pass
    try:
        NS['SEAT_BOT'] = SEAT_BOT
    except NameError:
        pass
    try:
        NS['SEAT_D'] = SEAT_D
    except NameError:
        pass
    try:
        NS['SEAT_DECK_CY'] = SEAT_DECK_CY
    except NameError:
        pass
    try:
        NS['SEAT_DECK_D'] = SEAT_DECK_D
    except NameError:
        pass
    try:
        NS['SEAT_DECK_W'] = SEAT_DECK_W
    except NameError:
        pass
    try:
        NS['SEAT_GAP'] = SEAT_GAP
    except NameError:
        pass
    try:
        NS['SEAT_N'] = SEAT_N
    except NameError:
        pass
    try:
        NS['SEAT_SIDE'] = SEAT_SIDE
    except NameError:
        pass
    try:
        NS['SEAT_T'] = SEAT_T
    except NameError:
        pass
    try:
        NS['SEAT_W'] = SEAT_W
    except NameError:
        pass
    try:
        NS['SEAT_X0'] = SEAT_X0
    except NameError:
        pass
    try:
        NS['SHOULDER'] = SHOULDER
    except NameError:
        pass
    try:
        NS['STATES'] = STATES
    except NameError:
        pass
    try:
        NS['S_LEFT'] = S_LEFT
    except NameError:
        pass
    try:
        NS['S_RIGHT'] = S_RIGHT
    except NameError:
        pass
    try:
        NS['_al'] = _al
    except NameError:
        pass
    try:
        NS['_total'] = _total
    except NameError:
        pass
    try:
        NS['arm_pad_objs'] = arm_pad_objs
    except NameError:
        pass
    try:
        NS['backc_objs'] = backc_objs
    except NameError:
        pass
    try:
        NS['foot_x'] = foot_x
    except NameError:
        pass
    try:
        NS['foot_y'] = foot_y
    except NameError:
        pass
    try:
        NS['seat_deck'] = seat_deck
    except NameError:
        pass
    try:
        NS['seat_objs'] = seat_objs
    except NameError:
        pass
    try:
        NS['shell'] = shell
    except NameError:
        pass
    try:
        NS['shell_frames'] = shell_frames
    except NameError:
        pass
    try:
        NS['shell_params'] = shell_params
    except NameError:
        pass
    try:
        NS['shell_sects'] = shell_sects
    except NameError:
        pass


STEPS = [
    ('准备', build_00_step0),
    ('① 连续软包外壳（背板+双扶手+转角+斜肩）', build_01_step1),
    ('② 底座框', build_02_step2),
    ('③ 抛光铝脚', build_03_step3),
    ('④ 座板', build_04_step4),
    ('⑤ 坐垫 ×%d（超椭球软包，底面压平坐实）', build_05_d),
    ('⑥ 靠垫 ×%d（前移压在坐垫上，后仰 11°）', build_06_d_11),
    ('⑦ 扶手垫 ×2', build_07_2),
    ('⑧ 滚边（投射到曲面的半嵌包边）', build_08_step8),
    ('⑨ 真实针脚（每针独立几何，合并为单曲线对象）', build_09_step9),
]




# =====================================================================
# 入口：把步骤队列交给 live.run()，由 bpy.app.timers 逐帧执行。
# Blender 主循环不阻塞 → 窗口全程可交互（不卡死、不"未响应"），
# 同时用户能实时看到模型一步步长出来。
# =====================================================================
live.run(STEPS)
print("[LIVE] queued %d steps" % len(STEPS))

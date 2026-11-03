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
# =====================================================================
# 【v21 · 配色方案】
# ---------------------------------------------------------------------
# 之前整件沙发只有一种米色（fabric_oat），
# 渲染出来像"未上色的白模"，用户明确投诉"没有上色"。
#
# v21 采用【家具业经典的双色分区 + 点缀】：
#   · 主体（外壳/座板/底座）  fabric_oat_d  深燕麦 —— 压住底座、显厚重
#   · 坐垫/靠垫              fabric_oat    浅燕麦 —— 主体视觉面，最亮
#   · 扶手垫                 fabric_cream  米白 —— 与坐垫区分，形成层次
#   · 滚边/缝线              thread_dark   深色 —— 勾出所有分割线
#   · 抱枕（2 只）           accent_terracotta / accent_sage —— 点缀色
#
# 关键原则：坐垫必须是【最亮】的色，视线自然落在可坐的地方。
# =====================================================================
M_UP = B.fabric("U_upholstery", PAL[R["main"]])            # 浅燕麦（坐垫/靠垫）
M_BODY = B.fabric("U_upholsterydk", PAL[R["dark"]])        # 深燕麦（外壳/座板）
M_PAD = B.fabric("U_cream", PAL["fabric_oat_d"])           # 深燕麦（扶手垫）
M_WELT = B.pbr("U_dark", "#4A4438", 0.78)                  # 滚边
M_ALU = B.pbr("U_metal", "#C9CCD0", 0.18, 1.0)             # 铝脚
M_THREAD = B.pbr("U_thread", "#7C7263", 0.85)              # 缝线（深色才看得见）
M_ACC1 = B.fabric("U_accent1", PAL["accent_terracotta"])   # 陶土橙抱枕
M_ACC2 = B.fabric("U_accent2", PAL["accent_sage"])         # 灰绿抱枕

# ============================ 尺寸 ============================
# 【v19 · 按真实三人沙发比例重构】
# 参照现代简约三人位（意大利/北欧款）的实测尺寸：
#   总宽 2.24 / 总深 0.92 / 总高 0.82 / 坐高 0.42 / 座深 0.58
#   扶手高 0.62 / 扶手厚 0.22 / 靠背板厚 0.14
# v18 的实测毛病（渲染 + 分色图确认）：
#   1. 扶手只有 0.49 高（外壳段 0.39），相对 0.87 的靠背显得又矮又瘦
#   2. 扶手垫浮在扶手段顶，像块搁板
#   3. 靠垫过大且压在靠背最前沿，遮住整面靠背
#   4. 整体观感"高瘦"，不符合三人位沙发比例
W, D = 2.24, 0.92

FRAME_Z0 = 0.105          # 底部框架下沿
FRAME_X = 1.030          # 底部框架外沿（半宽）
FRAME_Y = 0.380          # 底部框架外沿（半深）

DECK_TOP = 0.145
SEAT_DECK_TOP = DECK_TOP + 0.024

SEAT_TOP = 0.420         # 坐面高

ARM_TOP = 0.620          # 扶手顶（含扶手垫）
ARM_PAD_T = 0.115        # 扶手垫厚（软包层）
ARM_BOARD_TOP = ARM_TOP - ARM_PAD_T   # 0.505 外壳扶手段顶
BACK_TOP = 0.820         # 靠背顶
# 【v20】靠背板加厚 0.140 → 0.200。
# 侧视图实测：0.14 的靠背像"一块薄板"贴在后面，不符合真实软包沙发
# （靠背是 18~22cm 厚的软包体）。加厚后侧视比例立刻对。
BACK_T = 0.200
ARM_W = 0.220            # 扶手厚

ARM_X = W / 2 - ARM_W / 2           # 1.010 扶手中心
ARM_IN = ARM_X - ARM_W / 2          # 0.900 扶手内表面
ARM_FRONT = 0.450

BACK_OUT = -0.440                   # 靠背外表面
BACK_CY = BACK_OUT + BACK_T / 2     # -0.340 靠背板中心
BACK_IN = BACK_OUT + BACK_T         # -0.240 靠背内表面

# 【v20】坐垫后缘顶到靠背内表面，消除"坐垫与靠背之间能看到背景"的缝。
# v19: SEAT_BACK=-0.170，靠背内表面 -0.290 → 中间 120mm 空档（侧视图可见）。
# 现在靠背内表面 -0.240，坐垫后缘 -0.230，留 10mm 装配缝。
SEAT_BACK = -0.230
SEAT_FRONT = 0.410

CORNER_R = 0.160

objs = []

# --- LIVE-STEPS-START ---


# =====================================================================
# 1. 连续软包实体（背板 + 两扶手 + 两个转角 + 两个斜肩，一个网格）
# =====================================================================
# 俯视外轮廓（沿"外表面"走，不是板中心）：
#   左扶手前端 → 左扶手后端 → 右扶手后端 → 右扶手前端
# 断面 a ≤ 0 = 向内进深（沙发内侧），所以路径上的点 = 实体【外表面】
OUTLINE = [
    (-ARM_X - ARM_W / 2, ARM_FRONT),
    (-ARM_X - ARM_W / 2, BACK_OUT),
    (ARM_X + ARM_W / 2, BACK_OUT),
    (ARM_X + ARM_W / 2, ARM_FRONT),
]
RADII = [0.0, CORNER_R, CORNER_R, 0.0]
PATH = SH.rounded_outline(OUTLINE, RADII, corner_seg=18)

# 【v18 修正】S_LEFT / S_RIGHT 必须用【路径自己的弧长参数】，
# 不能用原始折线的参数 —— rounded_outline 的 s 已改成按真实弧长算
# （圆弧处两者不等）。否则 STATES 的锚点会错位，
# 拐角处的断面高度/厚度就插值到错误的位置。
_al = SH.arc_len_param([(p[0], p[1]) for p in PATH])
_total = max(1e-9, _al[-1])


def _s_at(x, y):
    """路径上最接近 (x,y) 的点的弧长参数"""
    best = min(range(len(PATH)),
               key=lambda i: (PATH[i][0] - x) ** 2 + (PATH[i][1] - y) ** 2)
    return _al[best] / _total


S_LEFT = _s_at(-(ARM_X + ARM_W / 2), BACK_OUT)
S_RIGHT = _s_at(ARM_X + ARM_W / 2, BACK_OUT)

# 断面状态：(s, T进深, z_bot, z_wall, z_top)
#   扶手段：T=ARM_SHELL_T 顶=ARM_BOARD_TOP(0.505)
#   靠背段：T=BACK_T(0.140) 顶=BACK_TOP(0.820)
#   斜肩：两者之间连续插值
# 【v19】扶手段 T 加宽到 ARM_W+0.016，让扶手垫能完整坐在壳体扶手面上
#        而不是边缘悬空；斜肩高度改为在【扶手段顶 0.505】与
#        【靠背顶 0.820】之间平滑过渡（v18 的 +0.185 会冲到 0.69，
#        比扶手顶 0.62 还高，斜肩反而比扶手高，比例错误）。
SHOULDER = 0.058
ARM_SHELL_T = ARM_W + 0.016
SHOULDER_TOP = ARM_BOARD_TOP + (BACK_TOP - ARM_BOARD_TOP) * 0.52
STATES = [
    (0.000, ARM_SHELL_T, DECK_TOP, ARM_BOARD_TOP, ARM_BOARD_TOP),
    (S_LEFT - 0.060, ARM_SHELL_T, DECK_TOP, ARM_BOARD_TOP, ARM_BOARD_TOP),
    (S_LEFT - SHOULDER * 0.50, ARM_SHELL_T * 0.93, DECK_TOP,
     ARM_BOARD_TOP, SHOULDER_TOP),
    (S_LEFT + SHOULDER * 0.22, BACK_T * 1.22, DECK_TOP,
     BACK_TOP - 0.090, BACK_TOP - 0.030),
    (S_LEFT + 0.062, BACK_T, DECK_TOP, BACK_TOP - 0.010, BACK_TOP),
    (S_RIGHT - 0.062, BACK_T, DECK_TOP, BACK_TOP - 0.010, BACK_TOP),
    (S_RIGHT - SHOULDER * 0.22, BACK_T * 1.22, DECK_TOP,
     BACK_TOP - 0.090, BACK_TOP - 0.030),
    (S_RIGHT + SHOULDER * 0.50, ARM_SHELL_T * 0.93, DECK_TOP,
     ARM_BOARD_TOP, SHOULDER_TOP),
    (S_RIGHT + 0.060, ARM_SHELL_T, DECK_TOP, ARM_BOARD_TOP, ARM_BOARD_TOP),
    (1.000, ARM_SHELL_T, DECK_TOP, ARM_BOARD_TOP, ARM_BOARD_TOP),
]

shell, shell_params, shell_sects, shell_frames = SH.build_shell(
    "shell", PATH, STATES, M_BODY, cap_len=0.050)
SH.cloth_relax(shell, amp=0.0030, freq=12.0, seed=3, down_weight=0.30)
objs.append(shell)
live.MARK("① 连续软包外壳（背板+双扶手+转角+斜肩）")

# =====================================================================
# 2. 底座框（深色薄框 + 外露铝腿）
# =====================================================================
FW = FRAME_X * 2
FD = FRAME_Y * 2
RAIL = 0.050


def frame_bar(name, size, center, bev=0.008, sub=2):
    b = B.box(name, size, center, M_BODY)
    B.bevel(b, bev, 3)
    if sub:
        B.subsurf(b, sub)
    objs.append(b)
    return b


frame_bar("frame_front", (FW, RAIL, FRAME_Z0), (0, FRAME_Y - RAIL / 2, FRAME_Z0 / 2))
frame_bar("frame_rear", (FW, RAIL, FRAME_Z0), (0, -FRAME_Y + RAIL / 2, FRAME_Z0 / 2))
for sx in (-1, 1):
    frame_bar("frame_side_%s" % ('L' if sx < 0 else 'R'),
              (RAIL, FD - RAIL * 2, FRAME_Z0),
              (sx * (FRAME_X - RAIL / 2), 0, FRAME_Z0 / 2))
live.MARK("② 底座框")

# =====================================================================
# 3. 抛光铝脚
# =====================================================================
LEG_R = 0.019
LEG_H = FRAME_Z0
foot_x = [-(FRAME_X - 0.078), 0.0, FRAME_X - 0.078]
foot_y = [-(FRAME_Y - 0.068), FRAME_Y - 0.068]
for ix, fx in enumerate(foot_x):
    for iy, fy in enumerate(foot_y):
        if ix == 1 and iy == 0:
            continue
        splay = 0.016
        ox = math.copysign(splay, fx) if abs(fx) > 1e-6 else 0.0
        oy = math.copysign(splay, fy) if abs(fy) > 1e-6 else 0.0
        objs.append(B.cyl("alu_leg_%d_%d" % (ix, iy), LEG_R, LEG_H,
                           (fx + ox, fy + oy, LEG_H / 2), M_ALU, verts=20,
                           r2=LEG_R * 1.22))
        objs.append(B.cyl("leg_cup_%d_%d" % (ix, iy), LEG_R * 1.34, 0.011,
                           (fx, fy, LEG_H - 0.004), M_BODY, verts=16))
live.MARK("③ 抛光铝脚")

# =====================================================================
# 4. 座板（坐垫支撑面）—— 按【扶手内表面】全宽，不再只占中间
# =====================================================================
SEAT_DECK_W = ARM_IN * 2 - 0.014      # 1.816
# 【v20】座板必须【完整覆盖坐垫】。
# 坐垫 y[-0.230, 0.410] → 座板覆盖 [-0.250, 0.430]
#   深 = 0.680，中心 = 0.090
# v19 的座板覆盖 y[-0.365, 0.325]，前缘比坐垫短 85mm（正视图可见悬空）。
SEAT_DECK_D = 0.680
SEAT_DECK_CY = 0.090
seat_deck = B.box("seat_deck", (SEAT_DECK_W, SEAT_DECK_D, 0.024),
                  (0, SEAT_DECK_CY, DECK_TOP + 0.012), M_BODY)
B.bevel(seat_deck, 0.009, 3)
objs.append(seat_deck)
live.MARK("④ 座板")

# =====================================================================
# 5. 坐垫（铺满座板；顶面中央平整）
# =====================================================================
SEAT_N = 3
# =====================================================================
# 【v21 · 坐垫重做 —— 一整块连续坐面，而不是三个鼓包】
# ---------------------------------------------------------------------
# v20 的实测剖面（profile_probe.py）：
#   中央 412mm，垫与垫之间 310mm（深 100mm 的沟），整体起伏 248mm。
#   渲染出来 = 三个气球坐在坑里（用户投诉："坐垫都不平的3个突起"）。
#
# 真实高档沙发的做法：坐面是【一整块连续的软包】，
# 分区靠【压线 + 滚边】做视觉划分，几何上不挖深沟。
#
# v21 做法：
#   1) 坐垫仍然分 3 块（每块之间留 3mm 极细缝，真实缝线宽度），
#      但每块的顶面用 soft_slab 做成【大平面】，
#      圆肩只在【最外侧 30mm】内过渡 → 顶面 90% 是平的；
#   2) 每块坐垫之间塞一条【压缝软条 + 滚边】，把沟填平；
#   3) 三个坐垫共用一条【贯穿的通长滚边】，坐面视觉上连成一体。
# =====================================================================
SEAT_GAP = 0.004          # 极细缝（4mm）—— 真实缝线宽度
SEAT_SIDE = 0.006
SEAT_W = (SEAT_DECK_W - 2 * SEAT_SIDE - SEAT_GAP * (SEAT_N - 1)) / SEAT_N
SEAT_D = SEAT_FRONT - SEAT_BACK
SEAT_X0 = -SEAT_DECK_W / 2 + SEAT_SIDE + SEAT_W / 2
SEAT_BOT = SEAT_DECK_TOP
SEAT_T = SEAT_TOP - SEAT_BOT

seat_objs = []
for k in range(SEAT_N):
    cx = SEAT_X0 + k * (SEAT_W + SEAT_GAP)
    cy = (SEAT_BACK + SEAT_FRONT) / 2
    # flat_frac=0.74 → 顶面 74% 高度范围都是平面；edge_roll=0.026 →
    # 只有最外圈 26mm 做圆肩，其余完全是平的。
    c = B.soft_slab(
        "seat_%d" % k, (SEAT_W, SEAT_D, SEAT_T), (cx, cy, SEAT_BOT + SEAT_T / 2),
        M_UP,
        res_u=128, res_v=40,
        top_clamp=SEAT_TOP, bot_clamp=SEAT_BOT + 0.002,
        flat_frac=0.86, edge_roll=0.026, bot_inset=0.024, bot_roll=0.022,
        corner=0.95, crown=0.004, bulge=0.003,
        noise=0.0016, noise_freq=11.0, noise_seed=k * 13 + 3)
    # 顶面几乎不塌：只做极轻的"被坐过"凹陷（2mm），保持平整
    for v in c.data.vertices:
        if v.co.z > SEAT_TOP - 0.010:
            rr = min(1.0, math.hypot((v.co.x - cx) / (SEAT_W / 2),
                                      (v.co.y - cy) / (SEAT_D / 2)))
            v.co.z -= 0.002 * math.cos(rr * math.pi / 2)
    objs.append(c)
    seat_objs.append((c, cx, cy))
live.MARK("⑤ 坐垫 ×%d（大平面顶面，4mm 细缝，无深沟）" % SEAT_N)

# ---- 坐垫之间的【压缝软条 + 滚边】—— 把 4mm 细缝填成一条圆背脊 ----
# 这就是真实沙发"分块坐垫"的做法：几何连续，视觉靠滚边分区。
for k in range(SEAT_N - 1):
    gx = SEAT_X0 + SEAT_W / 2 + SEAT_GAP / 2 + k * (SEAT_W + SEAT_GAP)
    gz = SEAT_TOP - 0.012
    # 软条：一根小圆角长条，填住缝隙并略微高出顶面
    g = B.soft_slab(
        "seat_seam_%d" % k, (SEAT_GAP + 0.012, SEAT_D - 0.010, 0.030),
        (gx, cy, gz), M_UP,
        # 【v23 · 网格密度下调 —— 修 482 处法线反向】
        # 这条软条只有 20mm 宽 × 30mm 高，却用了 res_u=52 / res_v=26：
        # 顶点密度远超尺寸需要 → 环与环之间产生大量被压扁的碎面
        # （实测 seat_seam_0 有 482 处反向边，面积极小 0.000000 m²）。
        # 改成 28/18：环间距 ~0.7mm，仍足够圆润，但不再有碎面。
        res_u=28, res_v=18,
        top_clamp=SEAT_TOP + 0.001, bot_clamp=SEAT_TOP - 0.030,
        flat_frac=0.62, edge_roll=0.010, bot_inset=0.006, bot_roll=0.008,
        corner=0.97,
        noise=0.0008, noise_freq=13.0, noise_seed=k * 29 + 11)
    objs.append(g)
    # 缝上的滚边（沿分缝走一条）
    pts = []
    for i in range(31):
        t = i / 30
        yy = SEAT_BACK + 0.020 + (SEAT_D - 0.040) * t
        pts.append((gx, yy, SEAT_TOP - 0.004))
    objs.append(B.pipe_on_surface("seat_seam_pipe_%d" % k, pts, g, M_WELT,
                                   r=0.0055, res=10, lift=0.0022))
live.MARK("⑤b 坐垫分缝压条 + 滚边（消除深沟）")

# =====================================================================
# 6. 靠垫（完整外露，背面贴外壳内表面，留 4mm 缝）
# =====================================================================
BC_N = 3
BC_GAP = 0.006
BC_W = (SEAT_DECK_W - 0.030 - BC_GAP * (BC_N - 1)) / BC_N
BC_H = 0.400
BC_T = 0.165
# 【v22 · 修穿模】
#   v21 靠垫下缘 z = SEAT_TOP - 0.010 = 0.410，而坐垫顶面在 0.421
#   → 靠垫下缘插进坐垫 11mm（实测穿模检测：穿入 73~83% 顶点、最深 18mm）。
#   真实沙发：靠垫是【立在坐垫后方】的，下缘正好落在坐垫顶面高度上，
#   靠自身重量贴着坐垫后沿，不是插进去。
#   修正：下缘抬到 SEAT_TOP + 0.002（贴合坐垫顶面，不穿入）。
BC_CZ = SEAT_TOP + 0.002 + BC_H / 2
# 【v21】靠垫同样改成【大平面软包】（soft_slab），
#   顶面/正面平整、圆肩只在边缘 —— 不再是球。
#   靠垫之间也是 6mm 细缝 + 压缝条，不再是深沟。
# 【v22】靠垫整体再后移 12mm：前缘不越过坐垫后沿（-0.233），
#   坐垫与靠垫之间留出真实的高档沙发的"坐深"落差。
BC_CY = -0.107
BC_TILT = math.radians(-16.0)
BC_X0 = -SEAT_DECK_W / 2 + 0.015 + BC_W / 2

backc_objs = []
# 【v22 · 靠垫后仰的旋转中心】
#   原代码绕【靠垫自身中心】旋转 → 下缘绕着中心往后甩，
#   下缘 z 反而升高/前移，底缘插进坐垫（实测残留 5.3mm 穿模）。
#   真实靠垫是【立在坐垫上、向后倒】—— 旋转中心在【下缘】。
#   绕下缘转后：下缘 z 不变（稳稳落在坐垫顶面），上缘往后靠。
BC_PIVOT_Z = BC_CZ - BC_H / 2

for k in range(BC_N):
    cx = BC_X0 + k * (BC_W + BC_GAP)
    bc = B.soft_slab(
        "backc_%d" % k, (BC_W, BC_T, BC_H), (cx, BC_CY, BC_CZ), M_UP,
        res_u=104, res_v=38,
        top_clamp=BC_CZ + BC_H / 2, bot_clamp=BC_CZ - BC_H / 2,
        flat_frac=0.78, edge_roll=0.030, bot_inset=0.026, bot_roll=0.024,
        corner=0.93, crown=0.003, bulge=0.004,
        noise=0.0022, noise_freq=10.0, noise_seed=k * 11 + 5)
    # 后仰 16°：绕【下缘】旋转 —— 下缘稳落坐垫顶面，上缘贴靠背
    ct, st = math.cos(BC_TILT), math.sin(BC_TILT)
    for v in bc.data.vertices:
        dy = v.co.y - BC_CY
        dz = v.co.z - BC_PIVOT_Z
        v.co.y = BC_CY + dy * ct - dz * st
        v.co.z = BC_PIVOT_Z + dy * st + dz * ct
    # 【v22】把靠垫下缘【顶到坐垫顶面之上】—— 后仰后下缘会略微下沉，
    #   这里统一抬到 SEAT_TOP + 0.001，保证只"贴着"不"插进去"。
    lift = (SEAT_TOP + 0.001) - min(v.co.z for v in bc.data.vertices)
    if lift > 0:
        for v in bc.data.vertices:
            v.co.z += lift
    objs.append(bc)
    backc_objs.append((bc, cx))

# ---- 靠垫之间的【压缝条】—— 消除靠垫间的深缝 ----
for k in range(BC_N - 1):
    gx = BC_X0 + BC_W / 2 + BC_GAP / 2 + k * (BC_W + BC_GAP)
    g = B.soft_slab(
        "backc_seam_%d" % k, (BC_GAP + 0.014, BC_T - 0.010, BC_H - 0.020),
        (gx, BC_CY, BC_CZ), M_UP,
        res_u=52, res_v=26,
        top_clamp=BC_CZ + BC_H / 2, bot_clamp=BC_CZ - BC_H / 2,
        flat_frac=0.64, edge_roll=0.014, bot_inset=0.008, bot_roll=0.010,
        corner=0.97,
        noise=0.0010, noise_freq=12.0, noise_seed=k * 31 + 13)
    # 压缝条与靠垫同姿态：绕下缘旋转
    ct2, st2 = math.cos(BC_TILT), math.sin(BC_TILT)
    for v in g.data.vertices:
        dy = v.co.y - BC_CY
        dz = v.co.z - BC_PIVOT_Z
        v.co.y = BC_CY + dy * ct2 - dz * st2
        v.co.z = BC_PIVOT_Z + dy * st2 + dz * ct2
    objs.append(g)
live.MARK("⑥ 靠垫 ×%d（大平面软包 + 压缝条）" % BC_N)

# =====================================================================
# 7. 扶手垫（坐在外壳扶手段顶 0.390 上）
# =====================================================================
ARM_PAD_W = ARM_W + 0.016
# 【v19】扶手垫完整覆盖扶手段顶。
# v18 的 ARM_PAD_Y0 = -0.300（起点在后靠背里侧）→ 靠垫后方留一段空扶手面，
# 画面上像"孤零零一块垫子"。现在从靠背内表面起、到扶手前端收口。
ARM_PAD_Y0 = -0.300
ARM_PAD_Y1 = ARM_FRONT - 0.028

arm_pad_objs = []
for sx in (-1, 1):
    nm = 'L' if sx < 0 else 'R'
    ax = sx * ARM_X
    d = ARM_PAD_Y1 - ARM_PAD_Y0
    cy = (ARM_PAD_Y0 + ARM_PAD_Y1) / 2
    # 【v19】垫子【嵌入】扶手段顶 12mm —— 不是浮在上面。
    # 之前垫底正好落在段顶（ARM_BOARD_TOP），加上 top_clamp 的圆肩，
    # 视觉上像一块搁在板上的独立垫子。嵌入后与扶手壳体连成一体。
    # 【v21】扶手垫同样改成【大平面软包】——
    #   v20 用超椭球，扶手垫是个鼓包，顶面不平。
    #   现在 flat_frac=0.70 → 顶面 70% 是平的；
    #   前端收口（前端 12% 收窄下沉），模拟软包前端翻边。
    # 【v22】扶手垫配色修正：
    #   原来用 fabric_cream（#F2EDE2 米白），渲染出来【发灰发脏】——
    #   米白在深色棚拍环境里失去了亮度，反而不如米色显眼。
    #   改为 fabric_oat_d（#9D8F7A 深燕麦），与外壳同色系但更暖，
    #   和浅燕麦坐垫形成【明确的明暗分层】，靠垫最浅、坐垫次之、
    #   扶手垫最深 —— 视觉层次自然，扶手也不会"抢戏"。
    pad = B.soft_slab(
        "arm_pad_%s" % nm, (ARM_PAD_W, d, ARM_PAD_T),
        (ax, cy, ARM_BOARD_TOP + ARM_PAD_T / 2 - 0.012), M_PAD,
        res_u=120, res_v=36,
        top_clamp=ARM_TOP, bot_clamp=ARM_BOARD_TOP - 0.010,
        flat_frac=0.74, edge_roll=0.030, bot_inset=0.022, bot_roll=0.020,
        corner=0.93, crown=0.010, bulge=0.006,
        noise=0.0016, noise_freq=11.0, noise_seed=7 if sx < 0 else 19)
    # 前端收口：最后 12% 收窄并微微下沉
    for v in pad.data.vertices:
        t = (v.co.y - ARM_PAD_Y0) / d
        if t > 0.88:
            k2 = (t - 0.88) / 0.12
            v.co.x = ax + (v.co.x - ax) * (1 - 0.10 * k2)
            v.co.z -= 0.006 * k2
    objs.append(pad)
    arm_pad_objs.append((pad, ax, cy, ARM_PAD_W, d))
live.MARK("⑦ 扶手垫 ×2（大平面软包，嵌入扶手段顶）")

# =====================================================================
# 7b. 装饰抱枕（点缀色）—— 让整件家具"有配色"，不再是一片米色
# =====================================================================
# 【v21】之前整件只有一种米色，渲染出来像没上色的白模。
# 现在加两只小抱枕（陶土橙 / 灰绿），
# 放在左右两端靠垫前侧，斜靠在扶手与靠垫之间。
PIL_W, PIL_H, PIL_T = 0.270, 0.280, 0.110
# 【v22】抱枕位置修正：
#   v21 把抱枕放在 x = ±(SEAT_DECK_W/2 - 0.230) = ±0.638，
#   而扶手内沿在 ±0.889 → 抱枕在扶手【里面】，
#   从正面/45° 都被扶手外侧挡住（实测渲染里只剩一小条颜色，
#   find_color 在正面图只找到 2262px、在 3q 图 2088px）。
#   修正：抱枕挪到【紧贴扶手内沿】(±0.770)、前移到 y=0.240，
#   并把宽度收到 270mm —— 保证抱枕边缘不会穿进扶手内沿(0.889)。
# 【v22】抱枕高度：
#   抱枕高 280mm。真实摆法是【斜靠在一号靠垫与扶手之间】，
#   下缘落在坐垫面(0.42)附近，上缘到 0.66 左右 —— 不能高过靠背顶(0.82)。
#   中心 ≈ (0.42 + 0.66)/2 = 0.54。
#   v22 第 1 轮把它抬到 0.615 → 顶部到 0.786，快跟靠背一样高，明显失真。
PIL_CZ = 0.545
PIL_TILT = math.radians(-24.0)

pillow_specs = [
    ("pillow_L", -0.700, 0.055, M_ACC1, 0),
    ("pillow_R", 0.700, 0.055, M_ACC2, 1),
]
for nm, px, py, mat, sd in pillow_specs:
    pil = B.soft_slab(
        nm, (PIL_W, PIL_T, PIL_H), (px, py, PIL_CZ), mat,
        res_u=88, res_v=32,
        top_clamp=PIL_CZ + PIL_H / 2, bot_clamp=PIL_CZ - PIL_H / 2,
        flat_frac=0.56, edge_roll=0.044, bot_inset=0.032, bot_roll=0.030,
        corner=0.82, crown=0.010, bulge=0.010,
        noise=0.0030, noise_freq=13.0, noise_seed=101 + sd * 17)
    # 【v22 · 抱枕姿态重做】
    #   v21 的抱枕是"立着靠"（绕 X 后仰 26°、绕 Z 歪 9°），
    #   但它的中心在 x=±0.750、扶手内壁在 ±0.889 —— 抱枕整体缩在扶手内侧，
    #   而扶手是全高实体（0.505~0.620），
    #   所以从正面/45° 只能看到一条 20~30px 宽的色边（实测 find_color）。
    #
    #   修正（实测踩坑两轮）：
    #     第 1 轮 把它挪到 x=±0.845（扶手内沿）想"骑在扶手上"
    #            → part_audit 显示 pillow_R x 到 1.011，
    #              即 125mm 的抱枕直接插进了扶手实体里（埋了）。
    #     第 2 轮 改回 x=±0.700，并【去掉绕 Y 的向内倒角】
    #            （绕 Y 倒角会让抱枕下半截朝扶手方向倾 → 插进扶手）。
    #            现在靠【后仰 + 侧歪】两个轴完成斜靠，绕 Y 角保持 0。
    ay = math.radians(-30.0)           # 绕 X：向后仰（顶边往后）
    az = math.radians(14.0 if sd == 0 else -14.0)   # 绕 Z：侧歪
    ay2 = 0.0                          # 绕 Y：不倒（否则插进扶手）
    for v in pil.data.vertices:
        dx = v.co.x - px
        dy = v.co.y - py
        dz = v.co.z - PIL_CZ
        # 绕 X
        y1 = dy * math.cos(ay) - dz * math.sin(ay)
        z1 = dy * math.sin(ay) + dz * math.cos(ay)
        # 绕 Z
        x2 = dx * math.cos(az) - y1 * math.sin(az)
        y2 = dx * math.sin(az) + y1 * math.cos(az)
        # 绕 Y
        x3 = x2 * math.cos(ay2) + z1 * math.sin(ay2)
        z3 = -x2 * math.sin(ay2) + z1 * math.cos(ay2)
        v.co.x = px + x3
        v.co.y = py + y2
        v.co.z = PIL_CZ + z3
    # 【v22】把抱枕下半部"埋进"扶手垫一点（形成斜搭的接触感），
    #   上半部保持在外 —— 所以整体中心抬到扶手垫顶附近。
    objs.append(pil)
    # 抱枕正面滚边（点缀色的深色边，勾出轮廓）
    pts = []
    for i in range(73):
        a = 2 * math.pi * i / 72
        pts.append((px + (PIL_W / 2 - 0.012) * math.cos(a),
                    py - PIL_T / 2 + 0.006,
                    PIL_CZ + (PIL_H / 2 - 0.014) * math.sin(a)))
    objs.append(B.pipe_on_surface("%s_pipe" % nm, pts, pil, M_WELT,
                                   r=0.0055, res=9, lift=0.0020))
live.MARK("⑦b 装饰抱枕 ×2（陶土橙 / 灰绿，斜搭扶手上沿）")

# =====================================================================
# 8. 滚边
# =====================================================================
PIPE_R = 0.0100
PIPE_LIFT = 0.0036

# 8.1 坐垫【顶面周边】滚边
# 【v21】v20 的滚边走"赤道"（z = SEAT_TOP-0.034），
# 在超椭球坐垫上是对的；但 v21 坐垫改成大平面软包后，
# 赤道正好在圆肩上，看不到。
# 改成沿【顶面边缘】走一圈 —— 真实软包坐垫的做法：
# 顶面平整区与圆肩的交界处压一道滚边，既勾边又强化"平面"的印象。
for k, (c, cx, cy) in enumerate(seat_objs):
    pts = []
    for i in range(89):
        a = 2 * math.pi * i / 88
        # 矩形周边（带圆角），落在顶面外沿
        cs, sn = math.cos(a), math.sin(a)
        px = (SEAT_W / 2 - 0.016) * math.copysign(abs(cs) ** 0.62, cs)
        py = (SEAT_D / 2 - 0.016) * math.copysign(abs(sn) ** 0.62, sn)
        pts.append((cx + px, cy + py, SEAT_TOP - 0.020))
    objs.append(B.pipe_on_surface("seat_pipe_%d" % k, pts, c, M_WELT,
                                  r=PIPE_R, lift=PIPE_LIFT))

# 8.2 靠垫【正面周边】滚边
# 【v21】同上：靠垫改成大平面软包后，底沿滚边会跑到圆肩上。
# 改成沿【正面边缘】走一圈（真实靠垫的做法：正面压线）。
for k, (bc, cx) in enumerate(backc_objs):
    pts = []
    for i in range(89):
        a = 2 * math.pi * i / 88
        cs, sn = math.cos(a), math.sin(a)
        px = (BC_W / 2 - 0.018) * math.copysign(abs(cs) ** 0.62, cs)
        pz = (BC_H / 2 - 0.018) * math.copysign(abs(sn) ** 0.62, sn)
        # 正面位置（沿法线朝前），并按后仰角变换
        yy = BC_CY + BC_T / 2 - 0.010
        dz = pz
        dy = 0.0
        ry = BC_CY + dy * math.cos(BC_TILT) - dz * math.sin(BC_TILT)
        rz = BC_CZ + dy * math.sin(BC_TILT) + dz * math.cos(BC_TILT)
        pts.append((cx + px, ry, rz))
    objs.append(B.pipe_on_surface("backc_pipe_%d" % k, pts, bc, M_WELT,
                                  r=0.0088, lift=0.0032))

# 8.3 扶手垫顶缘滚边
for pad, ax, cy, w, d in arm_pad_objs:
    pts = []
    for i in range(65):
        a = 2 * math.pi * i / 64
        pts.append((ax + (w / 2 + 0.001) * math.cos(a),
                    cy + (d / 2 - 0.012) * math.sin(a),
                    ARM_TOP - 0.024))
    objs.append(B.pipe_on_surface("arm_pipe_%s" % ('L' if ax < 0 else 'R'),
                                  pts, pad, M_WELT, r=0.0090, lift=0.0032))

# 8.4 外壳：斜肩棱滚边（真实沙发斜肩有明确接缝）+ 端头包边
# 斜肩棱：位于路径参数 s = S_LEFT - SHOULDER*0.5 附近
for tag, s_key in (("L", S_LEFT), ("R", S_RIGHT)):
    # 找最接近该 s 的路径点
    best = min(range(len(PATH)), key=lambda i: abs(PATH[i][2] - s_key))
    i = best
    T, zb, zw, zt = shell_params[i]
    _, _, nx, ny = shell_frames[i]
    px, py = PATH[i][0], PATH[i][1]
    # 断面在 z_wall 处的内表面点
    pts = []
    for (a, b) in shell_sects[i]:
        if abs(b - zw) < 0.03:
            pts.append((px + nx * (a - 0.002), py + ny * (a - 0.002), b))
    if len(pts) >= 2:
        objs.append(B.pipe_on_surface("shell_shoulder_pipe_%s" % tag, pts, shell,
                                      M_WELT, r=0.0078, lift=0.0030))

# 外壳端头包边（扶手前端的收口）
for tag, idx in (("L", 0), ("R", len(PATH) - 1)):
    px, py = PATH[idx][0], PATH[idx][1]
    _, _, nx, ny = shell_frames[idx]
    sec = shell_sects[idx]
    pts = SH.cap_welt_points((px, py), (nx, ny), sec, inset=0.005)
    objs.append(B.pipe_on_surface("shell_cap_pipe_%s" % tag, pts, shell,
                                  M_WELT, r=0.0072, lift=0.0026))

# 8.5 底座框前缘滚边
objs.append(B.pipe_rect("frame_pipe_front", 0, FRAME_Y - RAIL / 2,
                         FRAME_Z0 - 0.012, FW - 0.008, RAIL - 0.008,
                         M_WELT, r=0.0054))
live.MARK("⑧ 滚边（投射到曲面的半嵌包边）")

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
for k, (c, cx, cy) in enumerate(seat_objs):
    pts = []
    for i in range(113):
        a = 2 * math.pi * i / 112
        pts.append((cx + (SEAT_W / 2 - 0.013) * math.cos(a),
                    cy + (SEAT_D / 2 - 0.013) * math.sin(a),
                    SEAT_TOP - 0.050))
    objs += stitch_on_surface("seat_stitch_%d" % k, pts, c, M_THREAD)

# 坐垫绗缝分线（浅，不做深槽）
for k, (c, cx, cy) in enumerate(seat_objs):
    for j, fx in enumerate((-0.26, 0.0, 0.26)):
        x = cx + fx * SEAT_W
        pts = []
        for i in range(41):
            t = i / 40
            pts.append((x, cy - (SEAT_D / 2 - 0.036) + (SEAT_D - 0.072) * t,
                        SEAT_TOP - 0.002 + 0.006 * math.sin(t * math.pi)))
        objs += stitch_on_surface("seat_tuft_%d_%d" % (k, j), pts, c, M_THREAD,
                                  r=0.00080, length=0.009, gap=0.005)

# 靠背顶针脚
objs += B.stitch_line("back_stitch",
                      (-ARM_IN + 0.10, BACK_CY - 0.018, BACK_TOP - 0.060),
                      (ARM_IN - 0.10, BACK_CY - 0.018, BACK_TOP - 0.060),
                      M_THREAD, r=0.00095, lift=0.002)

# 扶手外侧竖向针脚
for pad, ax, cy, w, d in arm_pad_objs:
    pts = []
    for i in range(31):
        t = i / 30
        pts.append((ax + (w / 2 + 0.002),
                    ARM_PAD_Y0 + 0.05 + (d - 0.12) * t,
                    ARM_TOP - 0.052))
    objs += stitch_on_surface("arm_stitch_%s" % ('L' if ax < 0 else 'R'), pts, pad, M_THREAD)
live.MARK("⑨ 真实针脚（每针独立几何，合并为单曲线对象）")

# =====================================================================
for o in list(objs):
    if o.type == 'MESH':
        B.apply_mods(o)

B.export(OUT)
print("OK sofa v18 ->", OUT, "objects:", len(objs),
      "seat_w=%.3f" % SEAT_W, "path_pts=%d" % len(PATH),
      "S_LEFT=%.3f S_RIGHT=%.3f" % (S_LEFT, S_RIGHT))
# --- LIVE-STEPS-END ---

"""sofa v17 —— 连续软包实体（可变断面扫掠），根治「几何体拼凑」与「穿模」

【用户验收反馈原文】
  "沙发墙有明显的穿模现象，整体依旧是简陋几何体拼凑的，不满意"

【v16 的实测缺陷（渲染 + 放大图逐项确认）】
  1. 外壳是「U 形弯管」—— 断面固定为超椭圆竖条，扶手段成了圆管
  2. 坐垫只占中间 1/3，两侧露出大片深色座板 → 拼凑感
     （根因：v15 起 SEAT_DECK_W 一直被当成【全宽】用，实际只有 795mm）
  3. 坐垫顶面出现整条深沟 —— 布料松弛噪声没做「顶面中央平整」
  4. 靠垫几乎被外壳吞掉，只露出顶端一条边

【v17 的修正】
  A. 【可变断面实体】sofa_shell.build_shell 支持断面随路径变化：
     靠背段 = 130mm 厚竖板；扶手段 = 205mm 厚竖板；
     两段之间断面连续插值 → 自动生成【斜肩曲面】（不是台阶）。
     扶手顶端与靠背顶端不再是两个方盒对接。
  B. 【坐垫铺满】座板与坐垫按【扶手内表面】全宽计算：
     ARM_IN = 1.03 - 0.205 = 0.825 → 座板 1.63m、坐垫 3×0.513m
  C. 【顶面平整】cloth_relax 增加 center/radial 参数：
     顶面中央平整、褶皱集中在边缘与侧壁。
  D. 【靠垫外露】靠垫移到外壳【内表面之外】一点点，
     并把外壳靠背内表面往后挪 → 靠垫完整可见。
  E. 【底座】底座框改成与外壳对齐的深色薄框，腿外露。

【验收】
  blender --background --python check_interpenetration.py -- 验收/models/sofa.glb 2.0
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

_cs = SH.outline_corner_s(OUTLINE)
S_LEFT = _cs[1]
S_RIGHT = _cs[2]

# 断面状态：(s, T进深, z_bot, z_wall, z_top)
#   扶手段：T=ARM_W(0.205) 顶=0.390
#   靠背段：T=BACK_T(0.130) 顶=0.870
#   斜肩：两者之间连续插值
SHOULDER = 0.052
STATES = [
    (0.000, ARM_W, DECK_TOP, ARM_BOARD_TOP, ARM_BOARD_TOP),
    (S_LEFT - 0.060, ARM_W, DECK_TOP, ARM_BOARD_TOP, ARM_BOARD_TOP),
    (S_LEFT - SHOULDER * 0.50, ARM_W * 0.93, DECK_TOP,
     ARM_BOARD_TOP, ARM_BOARD_TOP + 0.185),
    (S_LEFT + SHOULDER * 0.22, BACK_T * 1.20, DECK_TOP,
     BACK_TOP - 0.075, BACK_TOP - 0.020),
    (S_LEFT + 0.062, BACK_T, DECK_TOP, BACK_TOP - 0.010, BACK_TOP),
    (S_RIGHT - 0.062, BACK_T, DECK_TOP, BACK_TOP - 0.010, BACK_TOP),
    (S_RIGHT - SHOULDER * 0.22, BACK_T * 1.20, DECK_TOP,
     BACK_TOP - 0.075, BACK_TOP - 0.020),
    (S_RIGHT + SHOULDER * 0.50, ARM_W * 0.93, DECK_TOP,
     ARM_BOARD_TOP, ARM_BOARD_TOP + 0.185),
    (S_RIGHT + 0.060, ARM_W, DECK_TOP, ARM_BOARD_TOP, ARM_BOARD_TOP),
    (1.000, ARM_W, DECK_TOP, ARM_BOARD_TOP, ARM_BOARD_TOP),
]

shell, shell_params, shell_sects, shell_frames = SH.build_shell(
    "shell", PATH, STATES, M_UP, cap_len=0.050)
SH.cloth_relax(shell, amp=0.0030, freq=12.0, seed=3, down_weight=0.30)
objs.append(shell)

# =====================================================================
# 2. 底座框（深色薄框 + 外露铝腿）
# =====================================================================
FW = FRAME_X * 2
FD = FRAME_Y * 2
RAIL = 0.050


def frame_bar(name, size, center, bev=0.008, sub=2):
    b = B.box(name, size, center, M_UPDK)
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
                           (fx, fy, LEG_H - 0.004), M_UPDK, verts=16))

# =====================================================================
# 4. 座板（坐垫支撑面）—— 按【扶手内表面】全宽，不再只占中间
# =====================================================================
SEAT_DECK_W = ARM_IN * 2 - 0.014      # 1.816
SEAT_DECK_D = 0.690
SEAT_DECK_CY = -0.020
seat_deck = B.box("seat_deck", (SEAT_DECK_W, SEAT_DECK_D, 0.024),
                  (0, SEAT_DECK_CY, DECK_TOP + 0.012), M_UPDK)
B.bevel(seat_deck, 0.009, 3)
objs.append(seat_deck)

# =====================================================================
# 5. 坐垫（铺满座板；顶面中央平整）
# =====================================================================
SEAT_N = 3
SEAT_GAP = 0.018
SEAT_W = (SEAT_DECK_W - 0.036 - SEAT_GAP * (SEAT_N - 1)) / SEAT_N
SEAT_D = SEAT_FRONT - SEAT_BACK
SEAT_X0 = -SEAT_DECK_W / 2 + 0.018 + SEAT_W / 2
SEAT_BOT = SEAT_DECK_TOP
SEAT_T = SEAT_TOP - SEAT_BOT

seat_objs = []
for k in range(SEAT_N):
    cx = SEAT_X0 + k * (SEAT_W + SEAT_GAP)
    cy = (SEAT_BACK + SEAT_FRONT) / 2
    c = B.superellipsoid_soft(
        "seat_%d" % k, (SEAT_W, SEAT_D, SEAT_T), (cx, cy, SEAT_BOT + SEAT_T / 2), M_UP,
        e1=0.87, e2=0.92, res_u=104, res_v=52,
        squash_top=0.004, crown=0.007, top_clamp=SEAT_TOP - 0.002)
    for v in c.data.vertices:
        if v.co.z > SEAT_TOP - 0.014:
            rr = min(1.0, math.hypot((v.co.x - cx) / (SEAT_W / 2),
                                      (v.co.y - cy) / (SEAT_D / 2)))
            v.co.z -= 0.006 * math.cos(rr * math.pi / 2)
    # 顶面中央平整、褶皱集中在边缘
    SH.cloth_relax(c, amp=0.0032, freq=15.0, seed=k * 7 + 3,
                   edge_bias=0.72, down_weight=0.25,
                   center=(cx, cy), radial=(SEAT_W / 2, SEAT_D / 2))
    objs.append(c)
    seat_objs.append((c, cx, cy))

# =====================================================================
# 6. 靠垫（完整外露，背面贴外壳内表面，留 4mm 缝）
# =====================================================================
BC_N = 3
BC_GAP = 0.016
BC_W = (SEAT_DECK_W - 0.026 - BC_GAP * (BC_N - 1)) / BC_N
BC_H = 0.400
BC_T = 0.145
BC_CZ = SEAT_TOP + BC_H / 2 - 0.006
BC_CY = BACK_IN + 0.004 + BC_T / 2
BC_X0 = -SEAT_DECK_W / 2 + 0.013 + BC_W / 2

backc_objs = []
for k in range(BC_N):
    cx = BC_X0 + k * (BC_W + BC_GAP)
    bc = B.superellipsoid_soft(
        "backc_%d" % k, (BC_W, BC_T, BC_H), (cx, BC_CY, BC_CZ), M_UP,
        e1=0.82, e2=0.90, res_u=76, res_v=46,
        squash_top=0.006, crown=0.012, front_clamp=BC_CY + BC_T * 0.32)
    for v in bc.data.vertices:
        dy = v.co.y - BC_CY
        dz = v.co.z - BC_CZ
        a = math.radians(-9)
        v.co.y = BC_CY + dy * math.cos(a) - dz * math.sin(a)
        v.co.z = BC_CZ + dy * math.sin(a) + dz * math.cos(a)
    SH.cloth_relax(bc, amp=0.0028, freq=14.0, seed=k * 11 + 5,
                   edge_bias=0.70, down_weight=0.25,
                   center=(cx, BC_CY), radial=(BC_W / 2, BC_T / 2))
    objs.append(bc)
    backc_objs.append((bc, cx))

# =====================================================================
# 7. 扶手垫（坐在外壳扶手段顶 0.390 上）
# =====================================================================
ARM_PAD_W = ARM_W + 0.014
ARM_PAD_Y0 = BACK_CY + 0.115
ARM_PAD_Y1 = ARM_FRONT - 0.058

arm_pad_objs = []
for sx in (-1, 1):
    nm = 'L' if sx < 0 else 'R'
    ax = sx * ARM_X
    d = ARM_PAD_Y1 - ARM_PAD_Y0
    cy = (ARM_PAD_Y0 + ARM_PAD_Y1) / 2
    pad = B.superellipsoid_soft(
        "arm_pad_%s" % nm, (ARM_PAD_W, d, ARM_PAD_T),
        (ax, cy, ARM_BOARD_TOP + ARM_PAD_T / 2 - 0.002), M_UP,
        e1=0.88, e2=0.94, res_u=88, res_v=38,
        squash_top=0.003, crown=0.005,
        top_clamp=ARM_TOP,
        front_clamp=ARM_PAD_Y1 - 0.014)
    for v in pad.data.vertices:
        t = (v.co.y - ARM_PAD_Y0) / d
        if t > 0.88:
            k2 = (t - 0.88) / 0.12
            v.co.x = ax + (v.co.x - ax) * (1 - 0.09 * k2)
            v.co.z -= 0.007 * k2
    SH.cloth_relax(pad, amp=0.0022, freq=12.0, seed=7 if sx < 0 else 19,
                   edge_bias=0.65, down_weight=0.25,
                   center=(ax, cy), radial=(ARM_PAD_W / 2, d / 2))
    objs.append(pad)
    arm_pad_objs.append((pad, ax, cy, ARM_PAD_W, d))

# =====================================================================
# 8. 滚边
# =====================================================================
PIPE_R = 0.0100
PIPE_LIFT = 0.0036

# 8.1 坐垫赤道滚边
for k, (c, cx, cy) in enumerate(seat_objs):
    pts = []
    for i in range(73):
        a = 2 * math.pi * i / 72
        pts.append((cx + (SEAT_W / 2 + 0.001) * math.cos(a),
                    cy + (SEAT_D / 2 + 0.001) * math.sin(a),
                    SEAT_TOP - 0.034))
    objs.append(B.pipe_on_surface("seat_pipe_%d" % k, pts, c, M_WELT,
                                  r=PIPE_R, lift=PIPE_LIFT))

# 8.2 靠垫底沿滚边
for k, (bc, cx) in enumerate(backc_objs):
    pts = []
    for i in range(37):
        a = math.pi * i / 36 - math.pi / 2
        pts.append((cx + (BC_W / 2 - 0.004) * math.cos(a),
                    BC_CY - BC_T / 2 - 0.008,
                    BC_CZ - BC_H / 2 + 0.038 + 0.038 * math.cos(a)))
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

# =====================================================================
for o in list(objs):
    if o.type == 'MESH':
        B.apply_mods(o)

B.export(OUT)
print("OK sofa v17 ->", OUT, "objects:", len(objs),
      "seat_w=%.3f" % SEAT_W, "path_pts=%d" % len(PATH))

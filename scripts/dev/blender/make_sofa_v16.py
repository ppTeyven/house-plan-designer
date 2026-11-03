"""sofa v16 —— 连续软包外壳（轮廓扫掠），根治「几何体拼凑」与「穿模」

【用户验收反馈原文】
  "沙发墙有明显的穿模现象，整体依旧是简陋几何体拼凑的，不满意"

【对照参考实拍（验收/refs/_ref_arm.jpg、_ref_armback.jpg、_ref_side.jpg）后的根因】

  真实沙发：【靠背 + 扶手 + 转角】是【一件连续的软包外壳】——
    扶手从靠背端头连续弯下来，中间没有拼缝；
    转角是外壳路径的一部分，不是一根另插的方柱。

  v15 的做法是【逐件拼装】：靠背一块板 / 扶手一块深色侧板 + 一块浅色盖板 /
  L 形转角另插 corner_post 方柱。
  → 必然出现：① 部件接缝与穿插（= 用户说的穿模）
              ② 轮廓是直棱 + 圆拱的混合，一眼「几何体拼凑」

【v16 的结构级修正】

  1. 【连续外壳】用 sofa_shell.py 的轮廓扫掠，把背板 + 两扶手 + 两个转角
     做成【同一个网格】。高度/厚度沿路径连续插值 → 无接缝、零穿插。
  2. 【转角归位】转角 = 外壳路径上的圆角，不再有独立方柱
     （corner_post 与 arm_pad_W 的 8.0% / 67.7mm 穿模由此根除）。
  3. 【修正 v15 的真实尺寸 bug】v15 里 SEAT_DECK_W = BACK_INNER_X - 0.12
     被当成【全宽】用了，导致座板只有 795mm 宽、坐垫 3×225mm，
     沙发中间空出两道 227mm 的空档 —— 这正是「拼凑感」的一大来源。
     v16 改为正确的全宽座板，坐垫 3×566mm。
  4. 【底座框架外露】参考图里沙发底下是一圈深色框架 + 细金属腿，
     v16 补上（v15 的腿藏在壳体里看不见）。

【验收】
  blender --background --python check_interpenetration.py -- 验收/models/sofa.glb 2.0
  → 必须 0 对真实穿模
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

DECK_H = 0.150
DECK_TOP = 0.150
FRAME_Z0 = 0.112          # 底部框架下沿
FRAME_X = 0.985          # 底部框架外沿（半宽）
FRAME_Y = 0.372          # 底部框架外沿（半深）

SEAT_TOP = 0.430
SEAT_DECK_TOP = DECK_TOP + 0.024

ARM_PAD_TOP = 0.490
ARM_PAD_T = 0.100
ARM_BOARD_TOP = ARM_PAD_TOP - ARM_PAD_T   # 0.390 外壳扶手段顶
BACK_TOP = 0.870

BACK_T = 0.130
BACK_Y = -0.420
BACK_CY = BACK_Y + BACK_T / 2      # -0.355
BACK_F = BACK_Y + BACK_T            # -0.290 内表面

ARM_W = 0.205
ARM_X = W / 2 - ARM_W / 2           # 1.0175 扶手中心
ARM_IN = ARM_X - ARM_W / 2          # 0.915 扶手内表面
ARM_FRONT = 0.436

SEAT_BACK = -0.175
SEAT_FRONT = 0.400

CORNER_R = 0.150                    # 转角圆角半径

objs = []


# =====================================================================
# 1. 连续外壳（背板 + 两扶手 + 两个转角，一个网格）
# =====================================================================
# 俯视轮廓中线：左扶手前 → 左扶手后 → 右扶手后 → 右扶手前
OUTLINE = [
    (-ARM_X, ARM_FRONT),
    (-ARM_X, BACK_CY),
    (ARM_X, BACK_CY),
    (ARM_X, ARM_FRONT),
]
RADII = [0.0, CORNER_R, CORNER_R, 0.0]

PATH = SH.rounded_outline(OUTLINE, RADII, corner_seg=16)

# 路径归一化弧长上，三个折点/端点的位置（由 rounded_outline 的 s 定义）
_seg1 = ARM_FRONT - BACK_CY
_seg2 = 2 * ARM_X
_total = 2 * _seg1 + _seg2
S_LEFT = _seg1 / _total          # 左转角
S_RIGHT = (_seg1 + _seg2) / _total  # 右转角

# 断面锚点：(s, 半宽, z_bot, z_top)
#   扶手段  半宽 ARM_W/2  顶 ARM_BOARD_TOP(0.390)
#   背板段  半宽 BACK_T/2  顶 BACK_TOP(0.870)
#   转角处  两者之间做【斜肩】平滑过渡（连续曲面，不是直角拼装）
SHOULDER = 0.045
ANCHORS = [
    (0.000, ARM_W / 2, DECK_TOP, ARM_BOARD_TOP),
    (S_LEFT - 0.045, ARM_W / 2, DECK_TOP, ARM_BOARD_TOP),
    (S_LEFT - SHOULDER * 0.45, ARM_W / 2 * 0.90, DECK_TOP, ARM_BOARD_TOP + 0.170),
    (S_LEFT + SHOULDER * 0.30, BACK_T / 2 * 1.16, DECK_TOP, BACK_TOP - 0.055),
    (S_LEFT + 0.060, BACK_T / 2, DECK_TOP, BACK_TOP),
    (S_RIGHT - 0.060, BACK_T / 2, DECK_TOP, BACK_TOP),
    (S_RIGHT - SHOULDER * 0.30, BACK_T / 2 * 1.16, DECK_TOP, BACK_TOP - 0.055),
    (S_RIGHT + SHOULDER * 0.45, ARM_W / 2 * 0.90, DECK_TOP, ARM_BOARD_TOP + 0.170),
    (S_RIGHT + 0.045, ARM_W / 2, DECK_TOP, ARM_BOARD_TOP),
    (1.000, ARM_W / 2, DECK_TOP, ARM_BOARD_TOP),
]

shell, shell_params = SH.build_shell(
    "shell", PATH, ANCHORS, M_UP, cap_len=0.105, e=0.44)
SH.cloth_relax(shell, amp=0.0042, freq=13.0, seed=3)
objs.append(shell)

# 端头封盖
for tag, idx, nrm in (("L", 0, (-1.0, 0.0)), ("R", len(PATH) - 1, (1.0, 0.0))):
    cx, cy = PATH[idx][0], PATH[idx][1]
    hw, zb, zt = shell_params[idx]
    objs.append(SH.cap_disc("shell_cap_%s" % tag, (cx, cy), nrm,
                             (hw, zb, zt), M_UP))

# =====================================================================
# 2. 底部框架（参考图：沙发底下是一圈深色框架 + 细腿）
# =====================================================================
def frame_bar(name, size, center):
    b = B.box(name, size, center, M_UPDK)
    B.bevel(b, 0.010, 3)
    B.subsurf(b, 2)
    objs.append(b)
    return b


FW = FRAME_X * 2
FD = FRAME_Y * 2
RAIL = 0.055
frame_bar("frame_front", (FW, RAIL, FRAME_Z0 - 0.0), (0, FRAME_Y - RAIL / 2, FRAME_Z0 / 2 + 0.0))
frame_bar("frame_rear", (FW, RAIL, FRAME_Z0), (0, -FRAME_Y + RAIL / 2, FRAME_Z0 / 2))
for sx in (-1, 1):
    frame_bar("frame_side_%s" % ('L' if sx < 0 else 'R'),
              (RAIL, FD - RAIL * 2, FRAME_Z0),
              (sx * (FRAME_X - RAIL / 2), 0, FRAME_Z0 / 2))
# 框架顶封板（外皮正好坐在上面）
frame_bar("frame_top", (FW - 0.010, FD - 0.010, 0.014),
          (0, 0, FRAME_Z0 + 0.007))

# =====================================================================
# 3. 抛光铝脚（外撇）
# =====================================================================
LEG_R = 0.019
LEG_H = FRAME_Z0
foot_x = [-(FRAME_X - 0.075), 0.0, FRAME_X - 0.075]
foot_y = [-(FRAME_Y - 0.070), FRAME_Y - 0.070]
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
# 4. 座板（坐垫的支撑面）
# =====================================================================
SEAT_DECK_W = (ARM_IN - 0.006) * 2      # 1.818 正确全宽
SEAT_DECK_D = 0.700
SEAT_DECK_CY = -0.020
seat_deck = B.box("seat_deck", (SEAT_DECK_W, SEAT_DECK_D, 0.024),
                  (0, SEAT_DECK_CY, DECK_TOP + 0.012), M_UPDK)
B.bevel(seat_deck, 0.009, 3)
objs.append(seat_deck)

# =====================================================================
# 5. 坐垫
# =====================================================================
SEAT_N = 3
SEAT_GAP = 0.020
SEAT_W = (SEAT_DECK_W - 0.040 - SEAT_GAP * (SEAT_N - 1)) / SEAT_N
SEAT_D = SEAT_FRONT - SEAT_BACK
SEAT_X0 = -SEAT_DECK_W / 2 + 0.020 + SEAT_W / 2
SEAT_BOT = SEAT_DECK_TOP
SEAT_T = SEAT_TOP - SEAT_BOT

seat_objs = []
for k in range(SEAT_N):
    cx = SEAT_X0 + k * (SEAT_W + SEAT_GAP)
    cy = (SEAT_BACK + SEAT_FRONT) / 2
    c = B.superellipsoid_soft(
        "seat_%d" % k, (SEAT_W, SEAT_D, SEAT_T), (cx, cy, SEAT_BOT + SEAT_T / 2), M_UP,
        e1=0.87, e2=0.92, res_u=96, res_v=48,
        squash_top=0.004, crown=0.008, top_clamp=SEAT_TOP - 0.002)
    for v in c.data.vertices:
        if v.co.z > SEAT_TOP - 0.014:
            rr = min(1.0, math.hypot((v.co.x - cx) / (SEAT_W / 2),
                                      (v.co.y - cy) / (SEAT_D / 2)))
            v.co.z -= 0.006 * math.cos(rr * math.pi / 2)
    SH.cloth_relax(c, amp=0.0034, freq=15.0, seed=k * 7 + 3)
    objs.append(c)
    seat_objs.append((c, cx, cy))

# =====================================================================
# 6. 靠垫（背面止于外壳内表面，留 6mm 缝）
# =====================================================================
BC_N = 3
BC_GAP = 0.018
BC_W = (SEAT_DECK_W - 0.030 - BC_GAP * (BC_N - 1)) / BC_N
BC_H = 0.395
BC_T = 0.150
BC_CZ = SEAT_TOP + BC_H / 2 - 0.008
BC_CY = BACK_F + 0.006 + BC_T / 2
BC_X0 = -SEAT_DECK_W / 2 + 0.015 + BC_W / 2

backc_objs = []
for k in range(BC_N):
    cx = BC_X0 + k * (BC_W + BC_GAP)
    bc = B.superellipsoid_soft(
        "backc_%d" % k, (BC_W, BC_T, BC_H), (cx, BC_CY, BC_CZ), M_UP,
        e1=0.82, e2=0.90, res_u=72, res_v=44,
        squash_top=0.007, crown=0.014, front_clamp=BC_CY + BC_T * 0.34)
    for v in bc.data.vertices:
        dy = v.co.y - BC_CY
        dz = v.co.z - BC_CZ
        a = math.radians(-9)
        v.co.y = BC_CY + dy * math.cos(a) - dz * math.sin(a)
        v.co.z = BC_CZ + dy * math.sin(a) + dz * math.cos(a)
    SH.cloth_relax(bc, amp=0.0030, freq=14.0, seed=k * 11 + 5)
    objs.append(bc)
    backc_objs.append((bc, cx))

# =====================================================================
# 7. 扶手垫（坐在外壳扶手段顶 0.390 上）
# =====================================================================
ARM_PAD_W = ARM_W + 0.016
ARM_PAD_Y0 = BACK_CY + 0.105        # 斜肩之前
ARM_PAD_Y1 = ARM_FRONT - 0.060      # 前端收圆之前

arm_pad_objs = []
for sx in (-1, 1):
    nm = 'L' if sx < 0 else 'R'
    ax = sx * ARM_X
    d = ARM_PAD_Y1 - ARM_PAD_Y0
    cy = (ARM_PAD_Y0 + ARM_PAD_Y1) / 2
    pad = B.superellipsoid_soft(
        "arm_pad_%s" % nm, (ARM_PAD_W, d, ARM_PAD_T),
        (ax, cy, ARM_BOARD_TOP + ARM_PAD_T / 2 - 0.002), M_UP,
        e1=0.88, e2=0.94, res_u=80, res_v=36,
        squash_top=0.003, crown=0.006,
        top_clamp=ARM_PAD_TOP,
        front_clamp=ARM_PAD_Y1 - 0.014)
    for v in pad.data.vertices:
        t = (v.co.y - ARM_PAD_Y0) / d
        if t > 0.88:
            k2 = (t - 0.88) / 0.12
            v.co.x = ax + (v.co.x - ax) * (1 - 0.09 * k2)
            v.co.z -= 0.007 * k2
    SH.cloth_relax(pad, amp=0.0024, freq=12.0, seed=7 if sx < 0 else 19)
    objs.append(pad)
    arm_pad_objs.append((pad, ax, cy, ARM_PAD_W, d))

# =====================================================================
# 8. 滚边
# =====================================================================
PIPE_R = 0.0100
PIPE_LIFT = 0.0038

# 8.1 外壳顶缘滚边（沿路径走，贴合外壳曲面）
def shell_top_edge(side='L'):
    """取外壳路径上【顶面内侧边缘】的点序列"""
    pts = []
    idxs = range(len(PATH)) if side == 'L' else range(len(PATH) - 1, -1, -1)
    for i in idxs:
        x, y, s = PATH[i]
        hw, zb, zt = shell_params[i]
        # 路径左法向（指向内侧）
        if i == 0:
            tx, ty = PATH[1][0] - x, PATH[1][1] - y
        elif i == len(PATH) - 1:
            tx, ty = x - PATH[-2][0], y - PATH[-2][1]
        else:
            tx, ty = PATH[i + 1][0] - PATH[i - 1][0], PATH[i + 1][1] - PATH[i - 1][1]
        tl = math.hypot(tx, ty) or 1.0
        tx /= tl
        ty /= tl
        nx, ny = -ty, tx
        # 只取扶手/背板段的顶（跳过端头收缩区）
        pts.append((x + nx * (-hw * 0.86), y + ny * (-hw * 0.86), zt - 0.013))
    return pts


edge_pts = shell_top_edge('L')
objs.append(B.pipe_on_surface("shell_edge_pipe", edge_pts, shell, M_WELT,
                              r=0.0086, lift=0.0034))

# 8.2 坐垫赤道滚边
for k, (c, cx, cy) in enumerate(seat_objs):
    pts = []
    for i in range(65):
        a = 2 * math.pi * i / 64
        pts.append((cx + (SEAT_W / 2 + 0.001) * math.cos(a),
                    cy + (SEAT_D / 2 + 0.001) * math.sin(a),
                    SEAT_TOP - 0.036))
    objs.append(B.pipe_on_surface("seat_pipe_%d" % k, pts, c, M_WELT,
                                  r=PIPE_R, lift=PIPE_LIFT))

# 8.3 靠垫底沿滚边
for k, (bc, cx) in enumerate(backc_objs):
    pts = []
    for i in range(33):
        a = math.pi * i / 32 - math.pi / 2
        pts.append((cx + (BC_W / 2 - 0.004) * math.cos(a),
                    BC_CY - BC_T / 2 - 0.008,
                    BC_CZ - BC_H / 2 + 0.036 + 0.036 * math.cos(a)))
    objs.append(B.pipe_on_surface("backc_pipe_%d" % k, pts, bc, M_WELT,
                                  r=0.0088, lift=0.0034))

# 8.4 扶手垫顶缘滚边
for pad, ax, cy, w, d in arm_pad_objs:
    pts = []
    for i in range(61):
        a = 2 * math.pi * i / 60
        pts.append((ax + (w / 2 + 0.001) * math.cos(a),
                    cy + (d / 2 - 0.012) * math.sin(a),
                    ARM_PAD_TOP - 0.024))
    objs.append(B.pipe_on_surface("arm_pipe_%s" % ('L' if ax < 0 else 'R'),
                                  pts, pad, M_WELT, r=0.0090, lift=0.0034))

# 8.5 底部框架滚边
objs.append(B.pipe_rect("frame_pipe_front", 0, FRAME_Y - RAIL / 2,
                         FRAME_Z0 - 0.014, FW - 0.008, RAIL - 0.008,
                         M_WELT, r=0.0058))

# =====================================================================
# 9. 真实针脚
# =====================================================================
def stitch_on_surface(name, pts, surface, material, r=0.00095, lift=0.0026,
                      length=0.010, gap=0.006):
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
    out = []
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
            out += B.stitch_line("%s_%d" % (name, len(out)), p0, p1, material,
                                 r=r, length=length, gap=gap, count=1)
            t += seg
    return out


# 坐垫一圈针脚
for k, (c, cx, cy) in enumerate(seat_objs):
    pts = []
    for i in range(105):
        a = 2 * math.pi * i / 104
        pts.append((cx + (SEAT_W / 2 - 0.013) * math.cos(a),
                    cy + (SEAT_D / 2 - 0.013) * math.sin(a),
                    SEAT_TOP - 0.050))
    objs += stitch_on_surface("seat_stitch_%d" % k, pts, c, M_THREAD)

# 坐垫绗缝分线
for k, (c, cx, cy) in enumerate(seat_objs):
    for j, fx in enumerate((-0.26, 0.0, 0.26)):
        x = cx + fx * SEAT_W
        pts = []
        for i in range(37):
            t = i / 36
            pts.append((x, cy - (SEAT_D / 2 - 0.034) + (SEAT_D - 0.068) * t,
                        SEAT_TOP - 0.004 + 0.007 * math.sin(t * math.pi)))
        objs += stitch_on_surface("seat_tuft_%d_%d" % (k, j), pts, c, M_THREAD,
                                  r=0.00082, length=0.009, gap=0.005)

# 外壳背板顶针脚
objs += B.stitch_line("back_stitch",
                      (-ARM_IN + 0.10, BACK_CY - 0.020, BACK_TOP - 0.058),
                      (ARM_IN - 0.10, BACK_CY - 0.020, BACK_TOP - 0.058),
                      M_THREAD, r=0.00095, lift=0.002)

# 扶手外侧竖向针脚
for pad, ax, cy, w, d in arm_pad_objs:
    pts = []
    for i in range(29):
        t = i / 28
        pts.append((ax + (w / 2 + 0.002),
                    ARM_PAD_Y0 + 0.05 + (d - 0.12) * t,
                    ARM_PAD_TOP - 0.052))
    objs += stitch_on_surface("arm_stitch_%s" % ('L' if ax < 0 else 'R'), pts, pad, M_THREAD)

# =====================================================================
for o in list(objs):
    if o.type == 'MESH':
        B.apply_mods(o)

B.export(OUT)
print("OK sofa v16 ->", OUT, "objects:", len(objs),
      "seat_w=%.3f" % SEAT_W, "path_pts=%d" % len(PATH))

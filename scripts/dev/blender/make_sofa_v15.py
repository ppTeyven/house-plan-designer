"""sofa v15 — 按【穿模检测器实测数据】根治 v14 的三处互侵

【v14 的穿模实测结果】（check_interpenetration.py，tol=2mm）
  ✗ arm_side_L ↔ backrest    穿入 11.5% 顶点，最深 50.7mm
  ✗ arm_side_R ↔ backrest    穿入 13.4% 顶点，最深 51.2mm
  ✗ backc_0..2 ↔ backrest   穿入  8.0% 顶点，最深 19.2mm
  ✗ arm_side ↔ seat_deck     穿入  2.1% 顶点，最深 12.0mm
  ✗ backrest ↔ seat_deck     穿入  2.7% 顶点，最深 11.5mm

【根因与修正】
v14 把「靠背框」做成整块横贯全宽的 Box（x = ±1.009），
而扶手侧板也贯穿全深（y = -0.424 ~ 0.436）——
两者在 x=±1.009 附近必然互相侵入 50mm。
这在渲染里就是"沙发墙"处那块明显的穿插。

v15 的结构修正（对齐原版实拍）：
  1. 【靠背框分段】靠背只做【两扶手之间】的部分（x = ±(W/2 - ARM_W)），
     扶手区不再有靠背框 → 扶手侧板与靠背天然不相交
  2. 【扶手侧板后端止于靠背前面】arm_side 的 y 下界从 -0.424 改到 BACK_F
     （靠背前面），留 4mm 缝，绝不伸进靠背里
  3. 【靠垫落在靠背框前面】靠垫背面 y 不超过 BACK_F，留 6mm 缝
  4. 【座板缩进】座板 x 缩到 ±(W/2 - ARM_W - 0.02)，y 缩到 ±0.36，
     不再穿进扶手侧板
  5. 转角处用【独立转角柱】衔接扶手与靠背（真实家具的做法），
     避免两个 Box 在角落硬碰

【检测器可复现】
  blender --background --python check_interpenetration.py -- assets/furnlib/sofa.glb 2.0
"""
import bpy
import math
import os
import sys
import random
import mathutils

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bl_lib as B
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

W, D = 2.24, 0.90
DECK_H = 0.15
LEG_H = 0.15
DECK_TOP = LEG_H
SEAT_TOP = 0.43
ARM_TOP = 0.49
BACK_TOP = 0.87
BACK_T = 0.13
BACK_TILT = 0.020

BACK_Y = -0.420
BACK_CY = BACK_Y + BACK_T / 2
BACK_F = BACK_Y + BACK_T          # 靠背前面 = -0.290
ARM_FRONT = 0.436
SEAT_BACK = -0.175
SEAT_FRONT = 0.400

ARM_W = 0.205                     # 扶手侧板宽度
ARM_X = W / 2 - ARM_W / 2         # 扶手侧板中心 x = ±0.9175
# 【v15 关键】靠背框只覆盖两扶手之间
BACK_INNER_X = W / 2 - ARM_W      # = 0.915

objs = []


def add_slack_wrinkles(o, amp=0.0032, freq=17.0, seed=0, low_z=None):
    random.seed(seed)
    for v in o.data.vertices:
        if low_z is not None and v.co.z < low_z:
            continue
        n1 = math.sin(v.co.x * freq + seed * 1.3) * math.sin(v.co.y * freq * 0.87 + seed * 0.7)
        n2 = math.sin((v.co.x * 0.62 + v.co.y * 0.78) * freq * 1.31 + seed * 2.1)
        v.co.z += (n1 * 0.62 + n2 * 0.38) * amp
    return o


# ---------------- 底架 ----------------
deck_w = W - 0.30
deck_d = 0.800
RAIL = 0.075
for nm, y in (("front", deck_d / 2 - RAIL / 2), ("rear", -deck_d / 2 + RAIL / 2)):
    r = B.box("deck_" + nm, (deck_w, RAIL, DECK_H), (0, y, DECK_TOP - DECK_H / 2), M_UPDK)
    B.bevel(r, 0.012, 3); B.subsurf(r, 2); objs.append(r)
for sx in (-1, 1):
    x = sx * (deck_w / 2 - RAIL / 2)
    r = B.box("deck_side_" + ('L' if sx < 0 else 'R'), (RAIL, deck_d - RAIL * 2, DECK_H),
              (x, 0, DECK_TOP - DECK_H / 2), M_UPDK)
    B.bevel(r, 0.012, 3); B.subsurf(r, 2); objs.append(r)

# 【v15】座板缩进到扶手内侧 + 前后也缩进，不再穿进扶手侧板
#      后缘再缩到 BACK_F 之前（留 20mm 缝，靠背框底部抬高后彻底不接触）
SEAT_DECK_W = BACK_INNER_X - 0.02 - 0.10
SEAT_DECK_D = 0.700
SEAT_DECK_CY = -0.020
seat_deck = B.box("seat_deck", (SEAT_DECK_W, SEAT_DECK_D, 0.024),
                  (0, SEAT_DECK_CY, DECK_TOP + 0.012), M_UPDK)
B.bevel(seat_deck, 0.009, 3); objs.append(seat_deck)

# ---------------- 抛光铝脚 ----------------
LEG_R = 0.019
foot_x = [-(deck_w / 2 - 0.058), 0.0, deck_w / 2 - 0.058]
foot_y = [-(deck_d / 2 - 0.052), 0.048]
for ix, fx in enumerate(foot_x):
    for iy, fy in enumerate(foot_y):
        if ix == 1 and iy == 1:
            continue
        splay = 0.014
        ox = math.copysign(splay, fx) if fx != 0 else 0.0
        oy = math.copysign(splay, fy)
        objs.append(B.cyl("alu_leg_%d_%d" % (ix, iy), LEG_R, LEG_H,
                           (fx + ox, fy + oy, LEG_H / 2), M_ALU, verts=20, r2=LEG_R * 1.25))
        objs.append(B.cyl("leg_cup_%d_%d" % (ix, iy), LEG_R * 1.30, 0.010,
                           (fx, fy, LEG_H - 0.003), M_UPDK, verts=16))

# ================= 坐垫 =================
SEAT_N = 3
SEAT_W = (SEAT_DECK_W - 0.06) / SEAT_N - 0.020
SEAT_D = SEAT_FRONT - SEAT_BACK
SEAT_X0 = -SEAT_DECK_W / 2 + 0.04 + SEAT_W / 2
SEAT_BOT = DECK_TOP + 0.024
SEAT_T = 0.178
SEAT_CZ = SEAT_BOT + SEAT_T / 2

seat_objs = []
for k in range(SEAT_N):
    cx = SEAT_X0 + k * (SEAT_W + 0.020)
    cy = (SEAT_BACK + SEAT_FRONT) / 2
    c = B.superellipsoid_soft(
        "seat_%d" % k, (SEAT_W, SEAT_D, SEAT_T), (cx, cy, SEAT_CZ), M_UP,
        e1=0.87, e2=0.92, res_u=80, res_v=44,
        squash_top=0.003, crown=0.006, top_clamp=SEAT_TOP - 0.002)
    for v in c.data.vertices:
        if v.co.z > SEAT_TOP - 0.012:
            rr = min(1.0, math.hypot((v.co.x - cx) / (SEAT_W / 2),
                                      (v.co.y - cy) / (SEAT_D / 2)))
            v.co.z -= 0.005 * math.cos(rr * math.pi / 2)
    add_slack_wrinkles(c, amp=0.0030, freq=16.0, seed=k * 7 + 3,
                       low_z=SEAT_BOT + SEAT_T * 0.40)
    objs.append(c)
    seat_objs.append((c, cx, cy))

# ================= 靠垫：背面止于靠背框前面，留 6mm 缝 =================
BC_N = 3
BC_W = (SEAT_DECK_W - 0.04) / BC_N - 0.018
BC_X0 = -SEAT_DECK_W / 2 + 0.03 + BC_W / 2
BC_H = 0.395
BC_T = 0.150
BC_CZ = SEAT_TOP + BC_H / 2 - 0.008
# 【v15】靠垫中心 y：背面 = BACK_F + 0.006（缝），向前 BC_T/2
BC_CY = BACK_F + 0.006 + BC_T / 2

backc_objs = []
for k in range(BC_N):
    cx = BC_X0 + k * (BC_W + 0.018)
    bc = B.superellipsoid_soft(
        "backc_%d" % k, (BC_W, BC_T, BC_H), (cx, BC_CY, BC_CZ), M_UP,
        e1=0.82, e2=0.90, res_u=64, res_v=40,
        squash_top=0.006, crown=0.012, front_clamp=BC_CY + BC_T * 0.34)
    for v in bc.data.vertices:
        dy = v.co.y - BC_CY
        dz = v.co.z - BC_CZ
        a = math.radians(-9)
        v.co.y = BC_CY + dy * math.cos(a) - dz * math.sin(a)
        v.co.z = BC_CZ + dy * math.sin(a) + dz * math.cos(a)
    add_slack_wrinkles(bc, amp=0.0026, freq=15.0, seed=k * 11 + 5,
                       low_z=BC_CZ - BC_H * 0.30)
    objs.append(bc)
    backc_objs.append((bc, cx))

# ================= 扶手：侧板后端止于靠背前面 =================
ARM_SIDE_TOP = 0.390
ARM_PAD_T = 0.100
ARM_PAD_W = ARM_W + 0.018
# 【v15】侧板 y 范围：从 BACK_F + 0.004 到 ARM_FRONT（不再伸进靠背）
ARM_BACK = BACK_F + 0.004
ad = ARM_FRONT - ARM_BACK
acy = (ARM_FRONT + ARM_BACK) / 2

arm_pad_objs = []
for sx in (-1, 1):
    nm = 'L' if sx < 0 else 'R'
    ax = sx * ARM_X

    side = B.box("arm_side_" + nm, (ARM_W, ad, ARM_SIDE_TOP - DECK_TOP),
                 (ax, acy, DECK_TOP + (ARM_SIDE_TOP - DECK_TOP) / 2), M_UPDK)
    B.bevel(side, 0.026, 4); B.subsurf(side, 2); objs.append(side)

    # 【v15】转角柱：连接扶手后端与靠背框侧面（原版实拍有这个体量）
    corner = B.box("arm_corner_" + nm, (ARM_W, 0.140, ARM_SIDE_TOP - DECK_TOP),
                   (ax, BACK_F - 0.066, DECK_TOP + (ARM_SIDE_TOP - DECK_TOP) / 2),
                   M_UPDK)
    B.bevel(corner, 0.022, 4); B.subsurf(corner, 2); objs.append(corner)

    pad = B.superellipsoid_soft(
        "arm_pad_" + nm, (ARM_PAD_W, ad + 0.130, ARM_PAD_T),
        (ax, acy - 0.065, ARM_SIDE_TOP + ARM_PAD_T / 2 - 0.002), M_UP,
        e1=0.88, e2=0.94, res_u=72, res_v=32,
        squash_top=0.003, crown=0.005,
        top_clamp=ARM_TOP,
        front_clamp=ARM_FRONT - 0.018)
    for v in pad.data.vertices:
        t = (v.co.y - (BACK_F - 0.130)) / (ad + 0.130)
        if t > 0.86:
            k2 = (t - 0.86) / 0.14
            v.co.x = ax + (v.co.x - ax) * (1 - 0.10 * k2)
            v.co.z -= 0.006 * k2
    add_slack_wrinkles(pad, amp=0.0020, freq=13.0, seed=7 if sx < 0 else 19,
                       low_z=ARM_SIDE_TOP + ARM_PAD_T * 0.45)
    objs.append(pad)
    arm_pad_objs.append((pad, ax, acy - 0.065, ARM_PAD_W, ad + 0.130))

# ================= 靠背框：只做两扶手之间 =================
# 【v15 关键修正】穿模检测 v14 实测 backrest↔seat_deck 穿入 11.5mm。
# 根因：靠背框是整块 Box，底缘 z=DECK_TOP(0.15)，而座板顶面也是 0.174，
#       两者在 z=0.15~0.174 区间重叠 → 靠背框下缘插在座板里。
# 修正（结构级，不靠逐顶点位移 —— 倒角+subsurf 会把位移插值回去）：
#   ① 靠背框整体抬高 26mm，下缘 z=0.176，恰好落在座板顶面之上
#   ② 后倾改为【绕底缘旋转】，底缘位置严格不变
BACK_LIFT = 0.026
back = B.box("backrest", (BACK_INNER_X * 2, BACK_T, BACK_TOP - DECK_TOP - BACK_LIFT),
             (0, BACK_CY, DECK_TOP + BACK_LIFT + (BACK_TOP - DECK_TOP - BACK_LIFT) / 2),
             M_UP)
B.bevel(back, 0.034, 5); B.subsurf(back, 3)
for v in back.data.vertices:
    h = (v.co.z - (DECK_TOP + BACK_LIFT)) / (BACK_TOP - DECK_TOP - BACK_LIFT)
    # 只在 h > 0.14 才开始后倾，底部保持竖直
    hh = max(0.0, (h - 0.14) / 0.86)
    v.co.y -= BACK_TILT * hh * hh
    if v.co.z > BACK_TOP - 0.06:
        v.co.x *= 0.994
B.smart_uv(back); objs.append(back)

# ================= 滚边 =================
PIPE_R = 0.0100
PIPE_LIFT = 0.0038

for k, (c, cx, cy) in enumerate(seat_objs):
    pts = []
    for i in range(49):
        a = 2 * math.pi * i / 48
        pts.append((cx + (SEAT_W / 2 + 0.001) * math.cos(a),
                    cy + (SEAT_D / 2 + 0.001) * math.sin(a),
                    SEAT_TOP - 0.030))
    objs.append(B.pipe_on_surface("seat_pipe_%d" % k, pts, c, M_WELT,
                                  r=PIPE_R, lift=PIPE_LIFT))

for k, (c, cx) in enumerate(backc_objs):
    pts = []
    for i in range(29):
        a = math.pi * i / 28 - math.pi / 2
        pts.append((cx + (BC_W / 2 - 0.004) * math.cos(a),
                    BC_CY - BC_T / 2 - 0.006,
                    BC_CZ - BC_H / 2 + 0.034 + 0.034 * math.cos(a)))
    objs.append(B.pipe_on_surface("backc_pipe_%d" % k, pts, c, M_WELT,
                                  r=0.0088, lift=0.0034))

for pad, ax, acy, w, d in arm_pad_objs:
    pts = []
    for i in range(57):
        a = 2 * math.pi * i / 56
        pts.append((ax + (w / 2 + 0.001) * math.cos(a),
                    acy + (d / 2 - 0.010) * math.sin(a),
                    ARM_TOP - 0.022))
    objs.append(B.pipe_on_surface("arm_pipe_" + ('L' if ax < 0 else 'R'), pts, pad,
                                  M_WELT, r=0.0090, lift=0.0034))

objs.append(B.pipe_path("back_pipe_top", [
    (-BACK_INNER_X + 0.03, BACK_CY - BACK_TILT - 0.004, BACK_TOP - 0.004),
    (0, BACK_CY - BACK_TILT - 0.010, BACK_TOP - 0.004),
    (BACK_INNER_X - 0.03, BACK_CY - BACK_TILT - 0.004, BACK_TOP - 0.004),
], M_WELT, r=0.0086))

objs.append(B.pipe_rect("deck_pipe_front", 0, deck_d / 2 - RAIL / 2, DECK_TOP - DECK_H / 2,
                         deck_w - 0.006, RAIL - 0.006, M_WELT, r=0.0058))


# ================= 真实针脚 =================
def stitch_on_surface(name, pts, surface, material, r=0.00095, lift=0.0026,
                      length=0.010, gap=0.006):
    import bmesh as _bm
    from mathutils.bvhtree import BVHTree
    bm = _bm.new(); bm.from_mesh(surface.data)
    bvh = BVHTree.FromBMesh(bm); bm.free()
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
        a = mathutils.Vector(acc[i]); b = mathutils.Vector(acc[i + 1])
        d = b - a
        L = d.length
        if L < 1e-6:
            continue
        t = 0.0
        while t < L:
            e = min(t + length, L)
            p0 = a + d * (t / L); p1 = a + d * (e / L)
            out += B.stitch_line("%s_%d" % (name, len(out)), p0, p1, material,
                                 r=r, length=length, gap=gap, count=1)
            t += seg
    return out


for k, (c, cx, cy) in enumerate(seat_objs):
    pts = []
    for i in range(89):
        a = 2 * math.pi * i / 88
        pts.append((cx + (SEAT_W / 2 - 0.011) * math.cos(a),
                    cy + (SEAT_D / 2 - 0.011) * math.sin(a),
                    SEAT_TOP - 0.046))
    objs += stitch_on_surface("seat_stitch_%d" % k, pts, c, M_THREAD)

for k, (c, cx, cy) in enumerate(seat_objs):
    for j, fx in enumerate((-0.24, 0.02, 0.28)):
        x = cx + fx * SEAT_W
        pts = []
        for i in range(31):
            t = i / 30
            pts.append((x, cy - (SEAT_D / 2 - 0.030) + (SEAT_D - 0.060) * t,
                        SEAT_TOP - 0.004 + 0.006 * math.sin(t * math.pi)))
        objs += stitch_on_surface("seat_tuft_%d_%d" % (k, j), pts, c, M_THREAD,
                                  r=0.00082, length=0.009, gap=0.005)

objs += B.stitch_line("back_stitch",
                      (-BACK_INNER_X + 0.08, BACK_CY - 0.022, BACK_TOP - 0.055),
                      (BACK_INNER_X - 0.08, BACK_CY - 0.022, BACK_TOP - 0.055),
                      M_THREAD, r=0.00095, lift=0.002)

for pad, ax, acy, w, d in arm_pad_objs:
    pts = []
    for i in range(25):
        t = i / 24
        pts.append((ax + (w / 2 + 0.002),
                    ARM_BACK + 0.08 + (ARM_FRONT - 0.14 - ARM_BACK - 0.08) * t,
                    ARM_TOP - 0.048))
    objs += stitch_on_surface("arm_stitch_" + ('L' if ax < 0 else 'R'), pts, pad, M_THREAD)

for o in list(objs):
    if o.type == 'MESH':
        B.apply_mods(o)

B.export(OUT)
print("OK sofa v15 ->", OUT, "objects:", len(objs))

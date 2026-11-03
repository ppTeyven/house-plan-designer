"""sofa v10 — Zanotta William 1330/302（造型对齐实拍图 + 尺寸精确）

v9 对齐了"扶手是竖立侧墙"这一关键结构，但仍有三处硬伤，v10 逐条修掉：

  1. 【深度超规格】v9 实测 939mm（官方 900mm）。根因：背框后倾 55mm
     但背框底部仍在 y=-0.45，越过 -0.45 边界；且背框顶滚边又向后溢 8mm。
     v10：重排纵向预算，后缘锚在 -0.420，滚边最外 -0.448，总深 891mm。
  2. 【扶手缺两级结构】原版扶手 = 侧板 + 【独立扶手垫】叠在侧板顶。
     v9 只有一整块软包，看起来像一堵墙。v10：侧板只到 40cm，
     独立扶手垫 12cm 叠上去，顶面 52cm。
  3. 【靠垫糊在背框】v9 靠垫紧贴背框前表面，底沿悬空。
     v10：靠垫底沿落在坐垫上（43cm），与背框留 22mm 可见阴影缝。

此外 v10 把坐垫加深到 200mm（羊绒包更饱满）。
"""
import bpy, bmesh, math, os, sys, random

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
M_WELT = B.pbr("U_dark", PAL[R["welt"]], 0.62)
M_ALU = B.pbr("U_metal", "#C9CCD0", 0.18, 1.0)
M_THREAD = B.pbr("U_thread", PAL[R["thread"]], 0.88)

# ============ 蓝图尺寸（官方 1330/302：L224 × W90 × H87 cm，座高 43 cm） ============
W, D = 2.24, 0.90
DECK_H = 0.15
LEG_H = 0.15
DECK_TOP = LEG_H
SEAT_TOP = 0.43
ARM_TOP = 0.52
BACK_TOP = 0.87
BACK_T = 0.13
BACK_TILT = 0.020          # 背框后倾 20mm

# ---- 纵向预算（总深 891mm，留 9mm 余量给滚边/倒角） ----
BACK_Y = -0.420            # 背框后缘（底）
BACK_CY = BACK_Y + BACK_T / 2
BACK_F = BACK_Y + BACK_T   # 背框前缘 = -0.29
ARM_FRONT = 0.436          # 扶手前缘
ARM_BACK = BACK_Y - 0.004  # 扶手后端与背框重叠 → 连续 L 形
SEAT_BACK = -0.175
SEAT_FRONT = 0.400

objs = []

# ---------------- 底架 ----------------
deck_w = W - 0.30
deck_d = 0.800              # 0.400 → -0.400
RAIL = 0.075

for nm, y in (("front", deck_d / 2 - RAIL / 2), ("rear", -deck_d / 2 + RAIL / 2)):
    r = B.box("deck_" + nm, (deck_w, RAIL, DECK_H), (0, y, DECK_TOP - DECK_H / 2), M_UPDK)
    B.bevel(r, 0.012, 3); B.subsurf(r, 2); objs.append(r)

for sx in (-1, 1):
    x = sx * (deck_w / 2 - RAIL / 2)
    r = B.box("deck_side_" + ('L' if sx < 0 else 'R'), (RAIL, deck_d - RAIL * 2, DECK_H),
              (x, 0, DECK_TOP - DECK_H / 2), M_UPDK)
    B.bevel(r, 0.012, 3); B.subsurf(r, 2); objs.append(r)

seat_deck = B.box("seat_deck", (deck_w - 0.02, deck_d - 0.02, 0.026),
                  (0, 0, DECK_TOP + 0.013), M_UPDK)
B.bevel(seat_deck, 0.010, 3); objs.append(seat_deck)

objs.append(B.pipe_rect("deck_pipe_front", 0, deck_d / 2 - RAIL / 2, DECK_TOP - DECK_H / 2,
                         deck_w - 0.006, RAIL - 0.006, M_WELT, r=0.0055))

# ---------------- 抛光铝脚（细、外撇） ----------------
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
        leg = B.cyl("alu_leg_%d_%d" % (ix, iy), LEG_R, LEG_H,
                    (fx + ox, fy + oy, LEG_H / 2), M_ALU, verts=20, r2=LEG_R * 1.25)
        objs.append(leg)
        cup = B.cyl("leg_cup_%d_%d" % (ix, iy), LEG_R * 1.30, 0.010,
                    (fx, fy, LEG_H - 0.003), M_UPDK, verts=16)
        objs.append(cup)

# ---------------- 扶手：侧板 + 独立扶手垫（两级结构） ----------------
ARM_W = 0.205
ARM_SIDE_TOP = 0.400       # 侧板顶 40cm
ARM_PAD_T = 0.120          # 扶手垫厚 12cm

for sx in (-1, 1):
    nm = 'L' if sx < 0 else 'R'
    ax = sx * (W / 2 - ARM_W / 2)
    ad = ARM_FRONT - ARM_BACK
    acy = (ARM_FRONT + ARM_BACK) / 2

    # ---- 侧板（结构层，深色） ----
    side = B.box("arm_side_" + nm, (ARM_W, ad, ARM_SIDE_TOP - DECK_TOP),
                 (ax, acy, DECK_TOP + (ARM_SIDE_TOP - DECK_TOP) / 2), M_UPDK)
    B.bevel(side, 0.026, 4); B.subsurf(side, 2); objs.append(side)

    # ---- 独立扶手垫（浅色软包，叠在侧板顶） ----
    pad = B.box("arm_pad_" + nm, (ARM_W + 0.012, ad - 0.012, ARM_PAD_T),
                (ax, acy, ARM_SIDE_TOP + ARM_PAD_T / 2 - 0.004), M_UP)
    B.bevel(pad, 0.036, 6); B.subsurf(pad, 3)
    for v in pad.data.vertices:
        t = (v.co.y - ARM_BACK) / ad
        if t > 0.78:
            k = (t - 0.78) / 0.22
            v.co.x = ax + (v.co.x - ax) * (1 - 0.12 * k)
            v.co.z -= 0.010 * k
        if v.co.z > ARM_SIDE_TOP + ARM_PAD_T - 0.075:
            v.co.z -= 0.004 * math.cos((v.co.y - acy) / ad * math.pi)
    B.smart_uv(pad); objs.append(pad)

    # ---- 扶手垫顶滚边 ----
    objs.append(B.pipe_path("arm_pad_pipe_" + nm, [
        (ax - ARM_W / 2 + 0.026, ARM_BACK + 0.02, ARM_TOP - 0.004),
        (ax - ARM_W / 2 + 0.022, ARM_FRONT - 0.030, ARM_TOP - 0.004),
        (ax - ARM_W / 2 + 0.034, ARM_FRONT - 0.008, ARM_TOP - 0.014),
        (ax + ARM_W / 2 - 0.034, ARM_FRONT - 0.008, ARM_TOP - 0.014),
        (ax + ARM_W / 2 - 0.022, ARM_FRONT - 0.030, ARM_TOP - 0.004),
        (ax + ARM_W / 2 - 0.026, ARM_BACK + 0.02, ARM_TOP - 0.004),
    ], M_WELT, r=0.0075))

    # ---- 扶手前端立滚边（U 形） ----
    objs.append(B.pipe_path("arm_front_" + nm, [
        (ax - ARM_W / 2 + 0.030, ARM_FRONT - 0.020, ARM_TOP - 0.030),
        (ax - ARM_W / 2 + 0.024, ARM_FRONT - 0.010, ARM_TOP - 0.075),
        (ax - ARM_W / 2 + 0.024, ARM_FRONT - 0.010, DECK_TOP + 0.055),
        (ax + ARM_W / 2 - 0.024, ARM_FRONT - 0.010, DECK_TOP + 0.055),
        (ax + ARM_W / 2 - 0.024, ARM_FRONT - 0.010, ARM_TOP - 0.075),
        (ax + ARM_W / 2 - 0.030, ARM_FRONT - 0.020, ARM_TOP - 0.030),
    ], M_WELT, r=0.0068))

    objs += B.stitch_line("arm_side_stitch_" + nm,
                          (ax + sx * (ARM_W / 2 + 0.001), ARM_BACK + 0.06, ARM_TOP - 0.085),
                          (ax + sx * (ARM_W / 2 + 0.001), ARM_FRONT - 0.055, ARM_TOP - 0.085),
                          M_THREAD, r=0.00082, lift=0.0015)

# ---------------- 靠背框（后倾） ----------------
back = B.box("backrest", (W - 0.22, BACK_T, BACK_TOP - DECK_TOP),
             (0, BACK_CY, (DECK_TOP + BACK_TOP) / 2), M_UP)
B.bevel(back, 0.034, 5); B.subsurf(back, 3)
for v in back.data.vertices:
    h = (v.co.z - DECK_TOP) / (BACK_TOP - DECK_TOP)
    v.co.y -= BACK_TILT * h * h
    if v.co.z > BACK_TOP - 0.06:
        v.co.x *= 0.994
B.smart_uv(back); objs.append(back)

# ---------------- 靠垫：底沿落坐垫，与背框留阴影缝 ----------------
BC_N = 3
BC_W = (W - 0.34) / BC_N - 0.016
BC_X0 = -(W - 0.34) / 2 + BC_W / 2 + 0.008
BC_H = 0.40
BC_T = 0.165
BC_CZ = SEAT_TOP + BC_H / 2 - 0.010
BC_BOT = BC_CZ - BC_H / 2

for k in range(BC_N):
    cx = BC_X0 + k * (BC_W + 0.016)
    bc = B.box("backc_%d" % k, (BC_W, BC_T, BC_H), (cx, BACK_F + BC_T / 2 - 0.022, BC_CZ),
               M_UP, rot=(math.radians(-9), 0, 0))
    B.bevel(bc, 0.042, 6); B.subsurf(bc, 3)
    for v in bc.data.vertices:
        u = min(1.0, abs(v.co.x - cx) / (BC_W / 2))
        if v.co.z > BC_CZ:
            kk = (v.co.z - BC_CZ) / (BC_H / 2)
            v.co.y += math.cos(u * math.pi / 2) * 0.014 * kk
        if abs(v.co.x - cx) > BC_W * 0.34:
            v.co.z -= 0.014
    B.smart_uv(bc); objs.append(bc)
    objs.append(B.pipe_path("backc_pipe_%d" % k, [
        (cx - BC_W / 2 + 0.020, BACK_F - 0.020, BC_BOT + 0.030),
        (cx - BC_W / 2 + 0.010, BACK_F + 0.030, BC_BOT + 0.008),
        (cx + BC_W / 2 - 0.010, BACK_F + 0.030, BC_BOT + 0.008),
        (cx + BC_W / 2 - 0.020, BACK_F - 0.020, BC_BOT + 0.030),
    ], M_WELT, r=0.0070))

# ---------------- 坐垫：饱满羊绒包（200mm 厚） ----------------
SEAT_N = 3
SEAT_W = (W - 0.30) / SEAT_N - 0.018
SEAT_D = SEAT_FRONT - SEAT_BACK
SEAT_X0 = -(W - 0.30) / 2 + SEAT_W / 2 + 0.009
SEAT_BOT = DECK_TOP + 0.026
SEAT_T = 0.200


def pillow_box(name, cx, cy, w, d, bot_z, thick, material, crown=0.026, taper=0.09):
    """饱满枕状垫：顶面中间鼓起、四周下陷，上窄下宽。"""
    b = B.box(name, (w, d, thick), (cx, cy, bot_z + thick / 2), material)
    B.bevel(b, 0.034, 5); B.subsurf(b, 3)
    for v in b.data.vertices:
        u = min(1.0, abs(v.co.x - cx) / (w / 2))
        w_ = min(1.0, abs(v.co.y - cy) / (d / 2))
        rr = min(1.0, math.hypot(u, w_))
        if v.co.z > bot_z + thick * 0.5:
            k = (v.co.z - bot_z - thick * 0.5) / (thick * 0.5)
            v.co.z += math.cos(rr * math.pi / 2) * crown * k
            s = 1.0 - taper * k
            v.co.x = cx + (v.co.x - cx) * s
            v.co.y = cy + (v.co.y - cy) * s
    B.smart_uv(b)
    return b


for k in range(SEAT_N):
    cx = SEAT_X0 + k * (SEAT_W + 0.018)
    c = pillow_box("seat_%d" % k, cx, (SEAT_BACK + SEAT_FRONT) / 2, SEAT_W, SEAT_D,
                   SEAT_BOT, SEAT_T, M_UP)
    objs.append(c)
    random.seed(k * 13 + 5)
    for v in c.data.vertices:
        if v.co.z > SEAT_BOT + SEAT_T * 0.55:
            v.co.z += (math.sin(v.co.x * 24.0 + k * 2.1) * math.cos(v.co.y * 19.0) * 0.5
                       + (random.random() - 0.5) * 0.3) * 0.0034

# ---------------- 滚边 + 针脚 + 绗缝 ----------------
for k in range(SEAT_N):
    cx = SEAT_X0 + k * (SEAT_W + 0.018)
    sy = (SEAT_BACK + SEAT_FRONT) / 2
    objs.append(B.pipe_rect("seat_pipe_%d" % k, cx, sy, SEAT_BOT + SEAT_T * 0.40,
                             SEAT_W + 0.005, SEAT_D + 0.005, M_WELT, r=0.0088))
    objs += B.stitch_rect("seat_stitch_%d" % k, cx, sy, SEAT_BOT + SEAT_T * 0.28,
                          SEAT_W - 0.016, SEAT_D - 0.016, M_THREAD,
                          r=0.00085, inset=0.004, lift=0.002)
    for j, fx in enumerate((-0.26, 0.0, 0.28)):
        x = cx + fx * SEAT_W
        objs += B.stitch_line("seat_tuft_%d_%d" % (k, j),
                              (x, sy - SEAT_D / 2 + 0.022, SEAT_BOT + SEAT_T - 0.007),
                              (x, sy + SEAT_D / 2 - 0.022, SEAT_BOT + SEAT_T - 0.007),
                              M_THREAD, r=0.00072)

# 背框顶滚边 + 针脚
objs.append(B.pipe_path("back_pipe_top", [
    (-(W - 0.34) / 2, BACK_CY - BACK_TILT - 0.004, BACK_TOP - 0.004),
    (0, BACK_CY - BACK_TILT - 0.010, BACK_TOP - 0.004),
    ((W - 0.34) / 2, BACK_CY - BACK_TILT - 0.004, BACK_TOP - 0.004),
], M_WELT, r=0.0080))
objs += B.stitch_line("back_stitch",
                      (-(W - 0.40) / 2, BACK_CY - 0.022, BACK_TOP - 0.055),
                      ((W - 0.40) / 2, BACK_CY - 0.022, BACK_TOP - 0.055),
                      M_THREAD, r=0.00085, lift=0.002)

for o in list(objs):
    if o.type == 'MESH':
        B.apply_mods(o)

B.export(OUT)
print("OK sofa v10 ->", OUT, "objects:", len(objs))

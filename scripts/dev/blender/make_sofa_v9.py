"""sofa v9 — Zanotta William 1330/302 造型级重做（第 3 版，对齐官方实拍图）

对照 dieter-horn 官方实拍图（zanotta-william-1330-sofaserie-12.jpg）逐项核对后，
v8 暴露的根本性错误：

  1. 【扶手做反了】v8 把扶手做成"水平薄板"（高 11cm，浮在座面侧边），
     所以渲染出来像两块漂浮的板。原版扶手是【竖立的软包侧墙】：
     从底架顶面一直砌到 52cm 高，顶面明显【高于座面 43cm】，
     并且与靠背板在后方连成连续的 L 形，没有断缝。
  2. 【靠垫没分离】v8 靠垫紧贴背板，糊成一片。原版靠垫是【独立鹅绒包】，
     前倾约 10°，底沿坐在坐垫上（43cm），下方与坐垫之间有阴影缝。
  3. 【背板不倾斜】原版背板整体后倾，靠垫也带倾角。
  4. 【铝脚不外撇】原版细铝脚略向外撇（splayed），不是直上直下。

尺寸锚点（Zanotta 官方 1330/302）：L224 × W90 × H87 cm，座高 43 cm。
"""
import bpy, bmesh, math, os, sys, random

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bl_lib as B
from palette import PAL, ROLES

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))),
                   "验收", "models", "sofa.glb")
os.makedirs(os.path.dirname(OUT), exist_ok=True)
B.wipe()

R = ROLES["sofa"]
M_UP = B.fabric("U_upholstery", PAL[R["main"]])
M_UPDK = B.fabric("U_upholsterydk", PAL[R["dark"]])
M_WELT = B.pbr("U_dark", PAL[R["welt"]], 0.62)
# 抛光铝脚（官方规格：aluminium alloy feet, polished）
M_ALU = B.pbr("U_metal", "#C9CCD0", 0.18, 1.0)
M_THREAD = B.pbr("U_thread", PAL[R["thread"]], 0.88)

# ============ 蓝图尺寸 ============
W, D = 2.24, 0.90
DECK_H = 0.15          # 底架（承重薄层）
LEG_H = 0.15           # 铝脚高度 → 底架顶面离地 15cm
DECK_TOP = LEG_H
SEAT_TOP = 0.43        # 官方座高
ARM_TOP = 0.52         # 【修正】原版扶手顶高于座面
BACK_TOP = 0.87        # 官方总高
BACK_T = 0.13          # 背板厚
BACK_CY = -D / 2 + BACK_T / 2        # 背板中心
CUSH_T = 0.155

# 纵向分区（从后往前）
BACK_F = BACK_CY + BACK_T / 2       # 背板前面 y = -0.32
SEAT_BACK = -0.19                   # 坐垫后缘
SEAT_FRONT = 0.415                  # 坐垫前缘（前留 35mm 到沙发前沿）

objs = []

# ---------------- 底架：薄层框 + 座板 ----------------
deck_w = W - 0.30
deck_d = D - 0.10
RAIL = 0.075

for nm, y in (("front", deck_d / 2 - RAIL / 2), ("rear", -deck_d / 2 + RAIL / 2)):
    r = B.box(f"deck_{nm}", (deck_w, RAIL, DECK_H), (0, y, DECK_TOP - DECK_H / 2), M_UPDK)
    B.bevel(r, 0.012, 3); B.subsurf(r, 2); objs.append(r)

for sx in (-1, 1):
    x = sx * (deck_w / 2 - RAIL / 2)
    r = B.box(f"deck_side_{'L' if sx < 0 else 'R'}", (RAIL, deck_d - RAIL * 2, DECK_H),
              (x, 0, DECK_TOP - DECK_H / 2), M_UPDK)
    B.bevel(r, 0.012, 3); B.subsurf(r, 2); objs.append(r)

seat_deck = B.box("seat_deck", (deck_w - 0.02, deck_d - 0.02, 0.026),
                  (0, 0, DECK_TOP + 0.013), M_UPDK)
B.bevel(seat_deck, 0.010, 3); objs.append(seat_deck)

# 底架前沿滚边
objs.append(B.pipe_rect("deck_pipe_front", 0, deck_d / 2 - RAIL / 2, DECK_TOP - DECK_H / 2,
                         deck_w - 0.006, RAIL - 0.006, M_WELT, r=0.0055))

# ---------------- 抛光铝脚（细、外撇） ----------------
LEG_R = 0.019
foot_x = [-(deck_w / 2 - 0.058), 0.0, deck_w / 2 - 0.058]
foot_y = [-(deck_d / 2 - 0.052), deck_d / 2 - 0.052]
for ix, fx in enumerate(foot_x):
    for iy, fy in enumerate(foot_y):
        if ix == 1 and iy == 1:
            continue
        # 外撇：底端比顶端向外偏移 14mm
        splay = 0.014
        ox = math.copysign(splay, fx) if fx != 0 else 0.0
        oy = math.copysign(splay, fy)
        leg = B.cyl(f"alu_leg_{ix}_{iy}", LEG_R, LEG_H,
                    (fx + ox, fy + oy, LEG_H / 2), M_ALU, verts=20,
                    r2=LEG_R * 1.25)
        objs.append(leg)
        cup = B.cyl(f"leg_cup_{ix}_{iy}", LEG_R * 1.30, 0.010,
                    (fx, fy, LEG_H - 0.003), M_UPDK, verts=16)
        objs.append(cup)

# ---------------- 扶手：竖立软包侧墙（关键修正） ----------------
ARM_W = 0.205
ARM_FRONT = D / 2 - 0.012
ARM_BACK = BACK_CY - BACK_T / 2 - 0.010     # 与背板重叠一点 → 连续 L 形，无断缝
ARM_H = ARM_TOP - DECK_TOP
for sx in (-1, 1):
    nm = 'L' if sx < 0 else 'R'
    ax = sx * (W / 2 - ARM_W / 2)
    ad = ARM_FRONT - ARM_BACK
    acy = (ARM_FRONT + ARM_BACK) / 2
    a = B.box(f"arm_{nm}", (ARM_W, ad, ARM_H), (ax, acy, DECK_TOP + ARM_H / 2), M_UP)
    B.bevel(a, 0.042, 6); B.subsurf(a, 3)
    for v in a.data.vertices:
        t = (v.co.y - ARM_BACK) / ad
        if t > 0.80:
            # 前端收头：向前渐窄、顶微降（软包圆收）
            k = (t - 0.80) / 0.20
            v.co.x = ax + (v.co.x - ax) * (1 - 0.13 * k)
            v.co.z -= 0.010 * k
        # 顶部中央微微下塌（被坐/靠压出来的真实形变）
        if v.co.z > ARM_TOP - 0.10:
            v.co.z -= 0.004 * math.cos((v.co.y - acy) / ad * math.pi)
    B.smart_uv(a); objs.append(a)

    # 扶手顶滚边（沿顶面前后走，POLY 精确路径）
    objs.append(B.pipe_path(f"arm_top_pipe_{nm}", [
        (ax - ARM_W / 2 + 0.026, ARM_BACK + 0.02, ARM_TOP - 0.004),
        (ax - ARM_W / 2 + 0.022, ARM_FRONT - 0.030, ARM_TOP - 0.004),
        (ax - ARM_W / 2 + 0.034, ARM_FRONT - 0.008, ARM_TOP - 0.014),
        (ax + ARM_W / 2 - 0.034, ARM_FRONT - 0.008, ARM_TOP - 0.014),
        (ax + ARM_W / 2 - 0.022, ARM_FRONT - 0.030, ARM_TOP - 0.004),
        (ax + ARM_W / 2 - 0.026, ARM_BACK + 0.02, ARM_TOP - 0.004),
    ], M_WELT, r=0.0075))

    # 扶手前端立滚边（U 形）
    objs.append(B.pipe_path(f"arm_front_{nm}", [
        (ax - ARM_W / 2 + 0.030, ARM_FRONT - 0.020, ARM_TOP - 0.030),
        (ax - ARM_W / 2 + 0.024, ARM_FRONT - 0.010, ARM_TOP - 0.075),
        (ax - ARM_W / 2 + 0.024, ARM_FRONT - 0.010, DECK_TOP + 0.055),
        (ax + ARM_W / 2 - 0.024, ARM_FRONT - 0.010, DECK_TOP + 0.055),
        (ax + ARM_W / 2 - 0.024, ARM_FRONT - 0.010, ARM_TOP - 0.075),
        (ax + ARM_W / 2 - 0.030, ARM_FRONT - 0.020, ARM_TOP - 0.030),
    ], M_WELT, r=0.0068))

    # 扶手外侧面缝线（可见针脚沿侧板走）
    objs += B.stitch_line(f"arm_side_stitch_{nm}",
                          (ax + sx * (ARM_W / 2 + 0.001), ARM_BACK + 0.06, ARM_TOP - 0.075),
                          (ax + sx * (ARM_W / 2 + 0.001), ARM_FRONT - 0.055, ARM_TOP - 0.075),
                          M_THREAD, r=0.00082, lift=0.0015)

# ---------------- 靠背板（后倾） ----------------
back = B.box("backrest", (W - 0.22, BACK_T, BACK_TOP - DECK_TOP),
             (0, BACK_CY, (DECK_TOP + BACK_TOP) / 2), M_UP)
B.bevel(back, 0.034, 5); B.subsurf(back, 3)
for v in back.data.vertices:
    h = (v.co.z - DECK_TOP) / (BACK_TOP - DECK_TOP)
    # 越往上越往后倾（背板后仰）
    v.co.y -= 0.055 * h * h
    if v.co.z > BACK_TOP - 0.10:
        v.co.x *= 0.994
B.smart_uv(back); objs.append(back)

# ---------------- 靠垫：独立鹅绒包，前倾，与背板分离 ----------------
BC_N = 3
BC_W = (W - 0.34) / BC_N - 0.016
BC_X0 = -(W - 0.34) / 2 + BC_W / 2 + 0.008
BC_H = 0.40
BC_T = 0.165
BC_CZ = SEAT_TOP + BC_H / 2 - 0.012
for k in range(BC_N):
    cx = BC_X0 + k * (BC_W + 0.016)
    bc = B.box(f"backc_{k}", (BC_W, BC_T, BC_H), (cx, BACK_F + BC_T / 2 - 0.012, BC_CZ), M_UP,
               rot=(math.radians(-9), 0, 0))
    B.bevel(bc, 0.042, 6); B.subsurf(bc, 3)
    for v in bc.data.vertices:
        u = min(1.0, abs(v.co.x - cx) / (BC_W / 2))
        # 鹅绒包：顶部与两侧鼓起
        if v.co.z > BC_CZ:
            kk = (v.co.z - BC_CZ) / (BC_H / 2)
            v.co.y += math.cos(u * math.pi / 2) * 0.014 * kk
        if abs(v.co.x - cx) > BC_W * 0.34:
            v.co.z -= 0.014
    B.smart_uv(bc); objs.append(bc)
    # 靠垫前缘滚边（沿底沿弧线）
    objs.append(B.pipe_path(f"backc_pipe_{k}", [
        (cx - BC_W / 2 + 0.020, BACK_F - 0.020, BC_CZ - BC_H / 2 + 0.030),
        (cx - BC_W / 2 + 0.010, BACK_F + 0.030, BC_CZ - BC_H / 2 + 0.008),
        (cx + BC_W / 2 - 0.010, BACK_F + 0.030, BC_CZ - BC_H / 2 + 0.008),
        (cx + BC_W / 2 - 0.020, BACK_F - 0.020, BC_CZ - BC_H / 2 + 0.030),
    ], M_WELT, r=0.0070))

# ---------------- 坐垫：饱满枕状 ----------------
SEAT_N = 3
SEAT_W = (W - 0.30) / SEAT_N - 0.018
SEAT_D = SEAT_FRONT - SEAT_BACK
SEAT_X0 = -(W - 0.30) / 2 + SEAT_W / 2 + 0.009
SEAT_BOT = DECK_TOP + 0.026


def pillow_box(name, cx, cy, w, d, bot_z, thick, material, crown=0.024, taper=0.08):
    """饱满枕状垫：顶面中间鼓起、四周下陷，上窄下宽。"""
    b = B.box(name, (w, d, thick), (cx, cy, bot_z + thick / 2), material)
    B.bevel(b, 0.032, 5); B.subsurf(b, 3)
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
    c = pillow_box(f"seat_{k}", cx, (SEAT_BACK + SEAT_FRONT) / 2, SEAT_W, SEAT_D,
                   SEAT_BOT, CUSH_T, M_UP)
    objs.append(c)
    random.seed(k * 13 + 5)
    for v in c.data.vertices:
        if v.co.z > SEAT_BOT + CUSH_T * 0.55:
            v.co.z += (math.sin(v.co.x * 24.0 + k * 2.1) * math.cos(v.co.y * 19.0) * 0.5
                       + (random.random() - 0.5) * 0.3) * 0.0032

# ---------------- 滚边 + 真实针脚 + 绗缝 ----------------
for k in range(SEAT_N):
    cx = SEAT_X0 + k * (SEAT_W + 0.018)
    sy = (SEAT_BACK + SEAT_FRONT) / 2
    objs.append(B.pipe_rect(f"seat_pipe_{k}", cx, sy, SEAT_BOT + CUSH_T * 0.40,
                             SEAT_W + 0.005, SEAT_D + 0.005, M_WELT, r=0.0088))
    objs += B.stitch_rect(f"seat_stitch_{k}", cx, sy, SEAT_BOT + CUSH_T * 0.28,
                          SEAT_W - 0.016, SEAT_D - 0.016, M_THREAD,
                          r=0.00085, inset=0.004, lift=0.002)
    for j, fx in enumerate((-0.26, 0.0, 0.26)):
        x = cx + fx * SEAT_W
        objs += B.stitch_line(f"seat_tuft_{k}_{j}",
                              (x, sy - SEAT_D / 2 + 0.022, SEAT_BOT + CUSH_T - 0.007),
                              (x, sy + SEAT_D / 2 - 0.022, SEAT_BOT + CUSH_T - 0.007),
                              M_THREAD, r=0.00072)

# 背板顶滚边 + 针脚
objs.append(B.pipe_path("back_pipe_top", [
    (-(W - 0.34) / 2, BACK_CY - 0.050, BACK_TOP - 0.004),
    (0, BACK_CY - 0.056, BACK_TOP - 0.004),
    ((W - 0.34) / 2, BACK_CY - 0.050, BACK_TOP - 0.004),
], M_WELT, r=0.0080))
objs += B.stitch_line("back_stitch",
                      (-(W - 0.40) / 2, BACK_CY - 0.020, BACK_TOP - 0.055),
                      ((W - 0.40) / 2, BACK_CY - 0.020, BACK_TOP - 0.055),
                      M_THREAD, r=0.00085, lift=0.002)

# ---------------- 应用修改器并导出 ----------------
for o in list(objs):
    if o.type == 'MESH':
        B.apply_mods(o)

B.export(OUT)
print("OK sofa v9 ->", OUT, "objects:", len(objs))

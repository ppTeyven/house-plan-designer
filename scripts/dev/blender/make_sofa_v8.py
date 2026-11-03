"""sofa v8 — Zanotta William 1330/302 造型级重做（依据官方实拍图 + 规格书）

v7 的问题（对照 dieter-horn 官方实拍图 zanotta-william-1330-sofaserie-12.jpg 逐项核对）：
  1. 底座是 26cm 厚的实心方盒，从地面堆起来 —— 原版是【15cm 薄层】，整层悬空
  2. 铝脚几乎看不见（半径 19mm 的小木/铜柱）—— 原版是【可见的抛光铝圆柱脚】，直径约 40mm
  3. 扶手是分离的厚圆角块，与座面之间有缝 —— 原版是【薄板层】，与座面齐平、向前延伸
  4. 整体厚重墩实 —— 原版是【低而宽、底下大量留空】的水平层叠语言

v8 的做法（William 流程：先描蓝图比例，再做布料解算，最后针脚滚边）：
  1. 骨架层：薄底架（15cm）+ 前后承重横梁 + 6 根可见抛光铝脚
  2. 座面层：3 块饱满枕状坐垫（厚度按实测 146mm），垫在薄底架上
  3. 扶手层：薄板（11cm），顶面与座垫顶齐平（43cm），前端略收圆
  4. 靠背层：薄背板 + 3 块独立鹅绒靠垫（可拆卸、可微调角度）
  5. 缝制：每层滚边 + 真实针脚几何 + 坐垫绗缝分格
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
M_FAB = B.fabric("U_fabric", PAL["fabric_cream"])
M_WELT = B.pbr("U_dark", PAL[R["welt"]], 0.62)
# 【关键】脚是抛光铝，不是木/铜。原版规格：aluminium alloy feet, polished
M_ALU = B.pbr("U_metal", "#C9CCD0", 0.18, 1.0)
M_THREAD = B.pbr("U_thread", PAL[R["thread"]], 0.88)

# ============ 蓝图尺寸（Zanotta William 1330/302 官方：L224 × W90 × H87 cm，座高 43 cm） ============
W, D = 2.24, 0.90
DECK_H = 0.15        # 底架（承重层）厚度 —— 原版薄层语言，不是厚箱体
SEAT_TOP = 0.43      # 座高（官方）
LEG_H = 0.15         # 铝脚可见高度（底架底面 15cm 离地）
DECK_TOP = LEG_H     # 底架顶面 = 脚顶 = 15cm
CUSH_T = 0.155       # 坐垫厚 155mm（饱满枕状，官方座高 43cm 且底架低）
ARM_TOP = 0.43      # 扶手顶与座垫顶齐平（原版语言）
ARM_T = 0.11        # 扶手薄层厚
BACK_TOP = 0.87     # 靠背顶（官方 87cm）
BACK_T = 0.13

objs = []

# ---------------- 骨架：薄底架 + 承重横梁 ----------------
# 底架只做【周边一圈】的框（像原版那样能看到下面的空隙与铝脚）
deck_w = W - 0.30
deck_d = D - 0.12
RAIL = 0.075        # 边框宽度

# 前梁 / 后梁（前后各一根完整横梁）
for nm, y in (("front", -deck_d / 2 + RAIL / 2), ("rear", deck_d / 2 - RAIL / 2)):
    r = B.box(f"deck_{nm}", (deck_w, RAIL, DECK_H), (0, y, DECK_TOP - DECK_H / 2), M_UPDK)
    B.bevel(r, 0.012, 3); B.subsurf(r, 2)
    objs.append(r)

# 左右侧梁
for sx in (-1, 1):
    x = sx * (deck_w / 2 - RAIL / 2)
    r = B.box(f"deck_side_{'L' if sx < 0 else 'R'}",
              (RAIL, deck_d - RAIL * 2, DECK_H),
              (x, 0, DECK_TOP - DECK_H / 2), M_UPDK)
    B.bevel(r, 0.012, 3); B.subsurf(r, 2)
    objs.append(r)

# 底架上方的薄座板（承托坐垫，整面封住以免看见框架）
seat_deck = B.box("seat_deck", (deck_w, deck_d, 0.028),
                  (0, 0, DECK_TOP + 0.014), M_UPDK)
B.bevel(seat_deck, 0.010, 3)
objs.append(seat_deck)

# 底架前沿滚边（细滚边，强化"薄层"轮廓）
objs.append(B.pipe_rect("deck_pipe_front", 0, -deck_d / 2 + RAIL / 2, DECK_TOP - DECK_H / 2,
                         deck_w, RAIL, M_WELT, r=0.006))

# ---------------- 抛光铝脚（可见圆柱脚，原版关键特征） ----------------
# 位置：四角 + 中间各一只，共 6 只（原版是细铝脚，不是厚木墩）
LEG_R = 0.021        # 铝脚半径 21mm → 直径 42mm
foot_x = [-(deck_w / 2 - 0.055), 0.0, deck_w / 2 - 0.055]
foot_y = [-(deck_d / 2 - 0.055), deck_d / 2 - 0.055]
for ix, fx in enumerate(foot_x):
    for iy, fy in enumerate(foot_y):
        if ix == 1 and iy == 1:
            continue          # 中后位不设脚（原版腿距有讲究）
        # 铝脚：下粗上细的锥形柱 + 顶部一小段与底架同色的安装座
        leg = B.cyl(f"alu_leg_{ix}_{iy}", LEG_R, LEG_H, (fx, fy, LEG_H / 2),
                    M_ALU, verts=24, r2=LEG_R * 0.82)
        objs.append(leg)
        # 脚顶安装座（深色小圆盘，遮住与底架的接缝）
        cup = B.cyl(f"leg_cup_{ix}_{iy}", LEG_R * 1.22, 0.012,
                    (fx, fy, LEG_H - 0.004), M_UPDK, verts=20)
        objs.append(cup)

# ---------------- 坐垫：饱满枕状，垫在薄底架上 ----------------
SEAT_N = 3
SEAT_W = (W - 0.30) / SEAT_N - 0.020
SEAT_D = D - 0.16
SEAT_X0 = -(W - 0.30) / 2 + SEAT_W / 2 + 0.010
SEAT_BOT = DECK_TOP + 0.028       # 坐在座板上


def pillow_box(name, cx, cy, w, d, bot_z, thick, material, crown=0.022, taper=0.075):
    """饱满枕状垫：底面平整，顶面中间鼓起、四周下陷（真实羽绒包的形状）。

    与 v7 的区别：v7 是「梯形收窄的方盒 + 平面顶」，
    这里用 superellipsoid 化的厚度场做出真正的枕状鼓面。
    """
    b = B.box(name, (w, d, thick), (cx, cy, bot_z + thick / 2), material)
    B.bevel(b, 0.030, 5)
    B.subsurf(b, 3)
    for v in b.data.vertices:
        # 顶面鼓起：按到中心的归一化距离做余弦隆起
        u = min(1.0, abs(v.co.x - cx) / (w / 2))
        v_ = min(1.0, abs(v.co.y - cy) / (d / 2))
        rr = min(1.0, math.hypot(u, v_))
        if v.co.z > bot_z + thick * 0.5:
            k = (v.co.z - bot_z - thick * 0.5) / (thick * 0.5)
            # 中间隆起、边缘收平
            v.co.z += (math.cos(rr * math.pi / 2) * crown) * k
            # 四周轻微收窄（上窄下宽的枕头感）
            s = 1.0 - taper * k
            v.co.x = cx + (v.co.x - cx) * s
            v.co.y = cy + (v.co.y - cy) * s
    B.smart_uv(b)
    return b


print("解算 3 块坐垫 ...")
for k in range(SEAT_N):
    cx = SEAT_X0 + k * (SEAT_W + 0.020)
    c = pillow_box(f"seat_{k}", cx, 0.012, SEAT_W, SEAT_D,
                   SEAT_BOT, CUSH_T, M_UP)
    objs.append(c)
    # 布面微褶（模拟羽绒包的松弛）
    random.seed(k * 13 + 5)
    for v in c.data.vertices:
        if v.co.z > SEAT_BOT + CUSH_T * 0.55:
            v.co.z += (math.sin(v.co.x * 26.0 + k * 2.1) * math.cos(v.co.y * 21.0) * 0.5
                       + (random.random() - 0.5) * 0.3) * 0.0035

# ---------------- 扶手：薄板层，与座面齐平并向前延伸 ----------------
ARM_W = 0.205
ARM_FRONT = D / 2       # 扶手前端与沙发前沿齐平
ARM_BACK = -D / 2 + 0.10
for sx in (-1, 1):
    nm = 'L' if sx < 0 else 'R'
    ax = sx * (W / 2 - ARM_W / 2)
    ad = ARM_FRONT - ARM_BACK
    acy = (ARM_FRONT + ARM_BACK) / 2
    a = B.box(f"arm_{nm}", (ARM_W, ad, ARM_T), (ax, acy, ARM_TOP - ARM_T / 2), M_UP)
    B.bevel(a, 0.026, 5); B.subsurf(a, 3)
    for v in a.data.vertices:
        # 前端略收（圆润收头），顶面微微下塌一点点
        t = (v.co.y - ARM_BACK) / ad
        if t > 0.86:
            k = (t - 0.86) / 0.14
            v.co.x = ax + (v.co.x - ax) * (1 - 0.10 * k)
            v.co.z -= 0.006 * k
        if v.co.z > ARM_TOP - ARM_T * 0.35:
            v.co.z -= 0.004
    B.smart_uv(a)
    objs.append(a)
    # 扶手顶滚边 + 前端立滚边
    objs.append(B.pipe_rect(f"arm_pipe_{nm}", ax, acy, ARM_TOP - 0.004,
                             ARM_W - 0.024, ad - 0.014, M_WELT, r=0.0072))
    objs.append(B.pipe_path(f"arm_front_{nm}", [
        (ax - ARM_W / 2 + 0.020, ARM_FRONT - 0.016, ARM_TOP - ARM_T + 0.014),
        (ax - ARM_W / 2 + 0.014, ARM_FRONT - 0.012, ARM_TOP - 0.014),
        (ax + ARM_W / 2 - 0.014, ARM_FRONT - 0.012, ARM_TOP - 0.014),
        (ax + ARM_W / 2 - 0.020, ARM_FRONT - 0.016, ARM_TOP - ARM_T + 0.014),
    ], M_WELT, r=0.0068))
    # 扶手下方托板（原版扶手下面有薄托，不是落地实体）
    sup = B.box(f"arm_support_{nm}", (ARM_W - 0.05, ad - 0.10, 0.016),
                (ax, acy, ARM_TOP - ARM_T - 0.008), M_UPDK)
    B.bevel(sup, 0.004, 2); objs.append(sup)

# ---------------- 靠背：薄背板 + 独立鹅绒靠垫 ----------------
# 背板（结构层，薄）
back = B.box("backrest", (W - 0.22, BACK_T, BACK_TOP - DECK_TOP),
             (0, -D / 2 + BACK_T / 2 + 0.015, (DECK_TOP + BACK_TOP) / 2), M_UP)
B.bevel(back, 0.030, 5); B.subsurf(back, 3)
for v in back.data.vertices:
    if v.co.z > DECK_TOP + 0.42:
        v.co.y += 0.010          # 上段后仰一点
    if v.co.z > BACK_TOP - 0.08:
        v.co.x *= 0.995
B.smart_uv(back)
objs.append(back)

# 靠垫（3 块，饱满鹅绒包，独立摆放，可微调）
BC_N = 3
BC_W = (W - 0.30) / BC_N - 0.018
BC_X0 = -(W - 0.30) / 2 + BC_W / 2 + 0.009
for k in range(BC_N):
    cx = BC_X0 + k * (BC_W + 0.018)
    bc = B.box(f"backc_{k}", (BC_W, 0.155, 0.44), (cx, -D / 2 + 0.185, 0.635), M_UP)
    B.bevel(bc, 0.040, 5); B.subsurf(bc, 3)
    for v in bc.data.vertices:
        u = min(1.0, abs(v.co.x - cx) / (BC_W / 2))
        if v.co.z > 0.80:
            v.co.y += 0.010
        # 顶部鼓起 + 两侧收窄（鹅绒包）
        if v.co.z > 0.635:
            v.co.y += math.cos(u * math.pi / 2) * 0.010 * (1 if v.co.y > -D / 2 + 0.185 else -1)
        if abs(v.co.x - cx) > BC_W * 0.36:
            v.co.z -= 0.012
    B.smart_uv(bc)
    objs.append(bc)
    objs.append(B.pipe_rect(f"backc_pipe_{k}", cx, -D / 2 + 0.185, 0.635,
                             BC_W - 0.012, 0.142, M_WELT, r=0.0072))

# ---------------- 滚边 + 真实针脚 + 绗缝 ----------------
for k in range(SEAT_N):
    cx = SEAT_X0 + k * (SEAT_W + 0.020)
    objs.append(B.pipe_rect(f"seat_pipe_{k}", cx, 0.012, SEAT_BOT + CUSH_T * 0.42,
                             SEAT_W + 0.006, SEAT_D + 0.006, M_WELT, r=0.0090))
    objs += B.stitch_rect(f"seat_stitch_{k}", cx, 0.012, SEAT_BOT + CUSH_T * 0.30,
                          SEAT_W - 0.016, SEAT_D - 0.016, M_THREAD,
                          r=0.00085, inset=0.004, lift=0.002)
    # 绗缝：中间一条 + 两侧各一条，划分"面包格"
    for j, fx in enumerate((-0.26, 0.0, 0.26)):
        x = cx + fx * SEAT_W
        objs += B.stitch_line(f"seat_tuft_{k}_{j}",
                              (x, 0.012 - SEAT_D / 2 + 0.025, SEAT_BOT + CUSH_T - 0.006),
                              (x, 0.012 + SEAT_D / 2 - 0.025, SEAT_BOT + CUSH_T - 0.006),
                              M_THREAD, r=0.00072)

# 靠背顶滚边 + 针脚
# 【关键】滚边中心必须落在背板实际中心（backrest 的 cy），否则会向后溢出 D/2，
# 实测曾造成总深度 950mm（超出官方 900mm 规格 50mm）。
BACK_CY = -D / 2 + BACK_T / 2 + 0.015
objs.append(B.pipe_rect("back_pipe_top", 0, BACK_CY, BACK_TOP - 0.004,
                         W - 0.30, BACK_T - 0.010, M_WELT, r=0.0082))
objs += B.stitch_line("back_stitch",
                      (-(W - 0.34) / 2, BACK_CY + 0.018, BACK_TOP - 0.048),
                      ((W - 0.34) / 2, BACK_CY + 0.018, BACK_TOP - 0.048),
                      M_THREAD, r=0.00085, lift=0.002)

# ---------------- 应用修改器 ----------------
for o in list(objs):
    if o.type == 'MESH':
        B.apply_mods(o)

B.export(OUT)
print("OK sofa v8 ->", OUT, "objects:", len(objs))

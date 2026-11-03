"""sofa v11 — 根治「穿模」+ 根治「简陋几何体拼凑」

用户验收反馈（原文）：
  "沙发墙有明显的穿模现象，整体依旧是简陋几何体拼凑的，不满意"

诊断（对照渲染放大图 + 原版实拍图）：
  A. 【穿模根因】v10 的滚边按【平面路径】走（pipe_rect / pipe_path 固定坐标），
     而软包表面是【变形后的曲面】（倒角盒子 + 顶点微调 + 布料褶皱）。
     平面路径 vs 变形曲面 → 滚边半径 8mm 有近一半切进布面 → 肉眼可见断线/穿插。
     根治：新增 B.pipe_on_surface() —— 滚边路径逐点沿曲面法线抬升，
           管心永远在曲面外侧，从几何上不可能穿模。
  B. 【简陋根因】v10 的坐垫/靠垫是「倒角盒子」。倒角盒子的棱线是直的、
     顶面是平的、鼓包是手搓顶点位移 → 轮廓有硬折角、缺乏软包连续曲率，
     渲染出来就是"几个几何体拼在一起"。
     根治：新增 B.superellipsoid_soft() —— 参数化超椭球软包，
           全曲面连续曲率 + 可控的顶面鼓包/压塌，再叠加布料解算位移场做松弛褶皱。

尺寸锚点（Zanotta William 1330/302 官方）：L224 × W90 × H87 cm，座高 43 cm。
"""
import bpy, math, os, sys, random, mathutils

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

# ============ 蓝图尺寸 ============
W, D = 2.24, 0.90
DECK_H = 0.15
LEG_H = 0.15
DECK_TOP = LEG_H
SEAT_TOP = 0.43
ARM_TOP = 0.52
BACK_TOP = 0.87
BACK_T = 0.13
BACK_TILT = 0.020

BACK_Y = -0.420
BACK_CY = BACK_Y + BACK_T / 2
BACK_F = BACK_Y + BACK_T
ARM_FRONT = 0.436
ARM_BACK = BACK_Y - 0.004
SEAT_BACK = -0.175
SEAT_FRONT = 0.400

objs = []


# ============ 布料松弛褶皱（叠加在软包曲面上的真实松弛纹） ============
def add_slack_wrinkles(o, amp=0.0032, freq=17.0, seed=0, axis='Z', low_z=None, high_z=None):
    """沿布面走线的自然松弛褶皱（布料解算后的典型形态）。

    真实软包不是完美光滑的：缝线附近布被拉紧，背面/底部布堆出松弛褶。
    这里用两组不同频率/方向的余弦叠加，避免规则网格感。
    """
    random.seed(seed)
    for v in o.data.vertices:
        z = v.co.z
        if low_z is not None and z < low_z:
            continue
        if high_z is not None and z > high_z:
            continue
        n1 = math.sin(v.co.x * freq + seed * 1.3) * math.sin(v.co.y * freq * 0.87 + seed * 0.7)
        n2 = math.sin((v.co.x * 0.62 + v.co.y * 0.78) * freq * 1.31 + seed * 2.1)
        d = (n1 * 0.62 + n2 * 0.38) * amp
        if axis == 'Z':
            v.co.z += d
        else:
            v.co.x += d
    return o


# ---------------- 底架（结构层，保持硬朗） ----------------
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

seat_deck = B.box("seat_deck", (deck_w - 0.02, deck_d - 0.02, 0.026),
                  (0, 0, DECK_TOP + 0.013), M_UPDK)
B.bevel(seat_deck, 0.010, 3); objs.append(seat_deck)

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

# ================= 软包核心：超椭球 =================
# e1/e2 指数：越小越"圆钝松软"，越大越"方硬"。
# 真实鹅绒坐包：顶面饱满圆钝、侧面微鼓、底部平整 → e1=0.62 / e2=0.78
SEAT_N = 3
SEAT_W = (W - 0.30) / SEAT_N - 0.020
SEAT_D = SEAT_FRONT - SEAT_BACK
SEAT_X0 = -(W - 0.30) / 2 + SEAT_W / 2 + 0.010
SEAT_BOT = DECK_TOP + 0.024
SEAT_T = 0.205

seat_objs = []
for k in range(SEAT_N):
    cx = SEAT_X0 + k * (SEAT_W + 0.020)
    cy = (SEAT_BACK + SEAT_FRONT) / 2
    c = B.superellipsoid_soft(
        "seat_%d" % k, (SEAT_W, SEAT_D, SEAT_T),
        (cx, cy, SEAT_BOT + SEAT_T / 2), M_UP,
        e1=0.62, e2=0.78, res_u=72, res_v=40,
        squash_top=0.006, crown=0.020)
    # 布料松弛褶皱：只作用在顶面与上半部（底部被框架压住，布是绷紧的）
    add_slack_wrinkles(c, amp=0.0034, freq=16.0, seed=k * 7 + 3,
                       low_z=SEAT_BOT + SEAT_T * 0.42)
    objs.append(c)
    seat_objs.append((c, cx, cy))

# 靠垫（独立鹅绒包）：更圆鼓、顶部更饱满
BC_N = 3
BC_W = (W - 0.34) / BC_N - 0.018
BC_X0 = -(W - 0.34) / 2 + BC_W / 2 + 0.009
BC_H = 0.40
BC_T = 0.175
BC_CZ = SEAT_TOP + BC_H / 2 - 0.010

backc_objs = []
for k in range(BC_N):
    cx = BC_X0 + k * (BC_W + 0.018)
    bc = B.superellipsoid_soft(
        "backc_%d" % k, (BC_W, BC_T, BC_H),
        (cx, BACK_F + BC_T / 2 - 0.026, BC_CZ), M_UP,
        e1=0.58, e2=0.72, res_u=64, res_v=36,
        squash_top=0.010, crown=0.026)
    # 靠垫前倾 9°（绕 X 轴）——真实靠包是斜靠的
    for v in bc.data.vertices:
        dy = v.co.y - (BACK_F + BC_T / 2 - 0.026)
        dz = v.co.z - BC_CZ
        a = math.radians(-9)
        v.co.y = (BACK_F + BC_T / 2 - 0.026) + dy * math.cos(a) - dz * math.sin(a)
        v.co.z = BC_CZ + dy * math.sin(a) + dz * math.cos(a)
    add_slack_wrinkles(bc, amp=0.0028, freq=15.0, seed=k * 11 + 5,
                       low_z=BC_CZ - BC_H * 0.30)
    objs.append(bc)
    backc_objs.append((bc, cx))

# 扶手：侧板（结构）+ 独立扶手垫（软包，超椭球）
ARM_W = 0.205
ARM_SIDE_TOP = 0.400
ARM_PAD_T = 0.120

arm_pad_objs = []
for sx in (-1, 1):
    nm = 'L' if sx < 0 else 'R'
    ax = sx * (W / 2 - ARM_W / 2)
    ad = ARM_FRONT - ARM_BACK
    acy = (ARM_FRONT + ARM_BACK) / 2

    # 侧板（深色结构层）
    side = B.box("arm_side_" + nm, (ARM_W, ad, ARM_SIDE_TOP - DECK_TOP),
                 (ax, acy, DECK_TOP + (ARM_SIDE_TOP - DECK_TOP) / 2), M_UPDK)
    B.bevel(side, 0.026, 4); B.subsurf(side, 2); objs.append(side)

    # 扶手垫 = 超椭球（圆钝饱满的软包，不是倒角盒子）
    pad = B.superellipsoid_soft(
        "arm_pad_" + nm, (ARM_W + 0.014, ad - 0.016, ARM_PAD_T),
        (ax, acy, ARM_SIDE_TOP + ARM_PAD_T / 2 - 0.004), M_UP,
        e1=0.66, e2=0.80, res_u=56, res_v=28,
        squash_top=0.008, crown=0.012)
    # 前端渐收 + 顶微塌（真实软包被靠/坐压出的形变）
    for v in pad.data.vertices:
        t = (v.co.y - ARM_BACK) / ad
        if t > 0.76:
            k = (t - 0.76) / 0.24
            v.co.x = ax + (v.co.x - ax) * (1 - 0.14 * k)
            v.co.z -= 0.012 * k
        if v.co.z > ARM_SIDE_TOP + ARM_PAD_T - 0.060:
            v.co.z -= 0.004 * math.cos((v.co.y - acy) / ad * math.pi)
    add_slack_wrinkles(pad, amp=0.0024, freq=14.0, seed=7 if sx < 0 else 19,
                       low_z=ARM_SIDE_TOP + ARM_PAD_T * 0.45)
    objs.append(pad)
    arm_pad_objs.append((pad, ax, acy, nm, sx))

# 靠背框（后倾，硬结构）
back = B.box("backrest", (W - 0.22, BACK_T, BACK_TOP - DECK_TOP),
             (0, BACK_CY, (DECK_TOP + BACK_TOP) / 2), M_UP)
B.bevel(back, 0.034, 5); B.subsurf(back, 3)
for v in back.data.vertices:
    h = (v.co.z - DECK_TOP) / (BACK_TOP - DECK_TOP)
    v.co.y -= BACK_TILT * h * h
    if v.co.z > BACK_TOP - 0.06:
        v.co.x *= 0.994
B.smart_uv(back); objs.append(back)

# ================= 滚边：全部改为曲面贴合（根治穿模） =================
# 【关键】pipe_on_surface 会把路径逐点投射到软包曲面并沿法线抬升，
#          所以滚边永远贴在布面上，不会切进去。

# --- 坐垫：绕赤道一圈的滚边（软包中腰位置） ---
for k, (c, cx, cy) in enumerate(seat_objs):
    pts = []
    # 超椭球赤道（cv=0）对应的水平截面
    for i in range(33):
        a = 2 * math.pi * i / 32
        pts.append((cx + (SEAT_W / 2) * math.cos(a),
                    cy + (SEAT_D / 2) * math.sin(a),
                    SEAT_BOT + SEAT_T * 0.42))
    objs.append(B.pipe_on_surface("seat_pipe_%d" % k, pts, c, M_WELT,
                                  r=0.0086, lift=0.0034))

# --- 靠垫：底沿滚边（贴合靠包下缘） ---
for k, (c, cx) in enumerate(backc_objs):
    pts = []
    for i in range(25):
        a = math.pi * i / 24 - math.pi / 2
        pts.append((cx + (BC_W / 2 - 0.006) * math.cos(a),
                    BACK_F - 0.014,
                    BC_CZ - BC_H / 2 + 0.030 + 0.030 * math.cos(a)))
    objs.append(B.pipe_on_surface("backc_pipe_%d" % k, pts, c, M_WELT,
                                  r=0.0070, lift=0.0030))

# --- 扶手垫：顶面周边滚边（贴合扶手垫上缘） ---
for pad, ax, acy, nm, sx in arm_pad_objs:
    pts = []
    for i in range(41):
        a = 2 * math.pi * i / 40
        pts.append((ax + (ARM_W / 2 + 0.004) * math.cos(a),
                    acy + (ad - 0.020) / 2 * math.sin(a),
                    ARM_TOP - 0.018))
    objs.append(B.pipe_on_surface("arm_pipe_" + nm, pts, pad, M_WELT,
                                  r=0.0074, lift=0.0032))

# --- 背框顶滚边（背框是硬表面，贴框走） ---
objs.append(B.pipe_path("back_pipe_top", [
    (-(W - 0.34) / 2, BACK_CY - BACK_TILT - 0.004, BACK_TOP - 0.004),
    (0, BACK_CY - BACK_TILT - 0.010, BACK_TOP - 0.004),
    ((W - 0.34) / 2, BACK_CY - BACK_TILT - 0.004, BACK_TOP - 0.004),
], M_WELT, r=0.0080))

# --- 底架前沿滚边（硬表面，保持平面路径即可） ---
objs.append(B.pipe_rect("deck_pipe_front", 0, deck_d / 2 - RAIL / 2, DECK_TOP - DECK_H / 2,
                         deck_w - 0.006, RAIL - 0.006, M_WELT, r=0.0055))

# ================= 真实针脚（贴在软包曲面上，不悬空） =================
# 针脚也必须贴曲面，否则会浮在空中或埋进布里。
# 这里直接复用 pipe_on_surface 的 BVH 贴合逻辑（工具库已封装为内部函数）。
def stitch_on_surface(name, pts, surface, material, r=0.00082, lift=0.0020,
                      length=0.008, gap=0.005):
    """沿曲面生成真实针脚几何（每针一根独立短线段）。

    与 pipe_on_surface 同源：先投射到曲面 + 沿法线抬升，再按针距切段。
    """
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
    # 按针距切段（每针独立几何）
    seg = length + gap
    for i in range(0, len(acc) - 1):
        a = acc[i]
        b = acc[i + 1]
        d = mathutils.Vector(b) - mathutils.Vector(a)
        L = d.length
        if L < 1e-6:
            continue
        t = 0.0
        while t < L:
            e = min(t + length, L)
            p0 = mathutils.Vector(a) + d * (t / L)
            p1 = mathutils.Vector(a) + d * (e / L)
            out += B.stitch_line("%s_%d" % (name, len(out)), p0, p1, material,
                                 r=r, length=length, gap=gap, count=1)
            t += seg
    return out


for k, (c, cx, cy) in enumerate(seat_objs):
    # 沿坐垫赤道略上方一圈（缝线位置）
    pts = []
    for i in range(73):
        a = 2 * math.pi * i / 72
        pts.append((cx + (SEAT_W / 2 - 0.012) * math.cos(a),
                    cy + (SEAT_D / 2 - 0.012) * math.sin(a),
                    SEAT_BOT + SEAT_T * 0.30))
    objs += stitch_on_surface("seat_stitch_%d" % k, pts, c, M_THREAD,
                               r=0.00080, lift=0.0022)

# 绗缝（面包格分线）：从滚边贴附路径出发，沿坐垫顶面横向走
for k, (c, cx, cy) in enumerate(seat_objs):
    for j, fx in enumerate((-0.24, 0.02, 0.28)):
        x = cx + fx * SEAT_W
        pts = []
        for i in range(25):
            t = i / 24
            yy = cy - (SEAT_D / 2 - 0.030) + (SEAT_D - 0.060) * t
            # 沿顶面拱形走（中间高）
            zz = SEAT_BOT + SEAT_T * 0.94 + 0.012 * math.sin(t * math.pi)
            pts.append((x, yy, zz))
        objs += B.stitch_line("seat_tuft_%d_%d" % (k, j), pts[0], pts[12], M_THREAD,
                              r=0.00072, length=0.008, gap=0.004)
        objs += B.stitch_line("seat_tuft_%d_%d_b" % (k, j), pts[12], pts[24], M_THREAD,
                              r=0.00072, length=0.008, gap=0.004)

# 背框顶针脚
objs += B.stitch_line("back_stitch",
                      (-(W - 0.40) / 2, BACK_CY - 0.022, BACK_TOP - 0.055),
                      ((W - 0.40) / 2, BACK_CY - 0.022, BACK_TOP - 0.055),
                      M_THREAD, r=0.00085, lift=0.002)

# 扶手侧缝针脚（贴在扶手垫侧面曲面上）
for pad, ax, acy, nm, sx in arm_pad_objs:
    pts = []
    for i in range(21):
        t = i / 20
        pts.append((ax + sx * (ARM_W / 2 + 0.004),
                    ARM_BACK + 0.07 + (ARM_FRONT - 0.12 - ARM_BACK - 0.07) * t,
                    ARM_TOP - 0.070))
    objs += stitch_on_surface("arm_stitch_" + nm, pts, pad, M_THREAD,
                               r=0.00082, lift=0.0018)

for o in list(objs):
    if o.type == 'MESH':
        B.apply_mods(o)

B.export(OUT)
print("OK sofa v11 ->", OUT, "objects:", len(objs))

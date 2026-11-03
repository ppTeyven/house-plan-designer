"""sofa v13 — 按原版实拍图把软包「压扁」回真实比例

v12 解决了穿模与滚边可见性，但并排对比原版实拍图后发现比例失真：

  原版（Zanotta William 实拍）            v12
  · 坐垫 = 扁平软板，棱角圆但整体平      · 坐垫 = 棉花糖，e1=0.62 太圆
  · 扶手 = 低位水平软板，顶面接近座面    · 扶手 = 高耸圆枕（52cm）
  · 靠垫 = 薄、斜靠                     · 靠垫 = 圆胖
  · 整体低矮横向，读作「层叠软包」      · 整体臃肿，读作「一堆抱枕」

根因：superellipsoid 的指数 e1 决定「方棱 vs 圆钝」。
  e1=0.62 → 接近球体（棉花糖）
  e1=0.62 真实软包（皮革/织物绷在框架上）应该是 e1≈0.86：
  侧棱接近垂直、只在 2~3cm 范围内圆转，crown 也要从 20mm 降到 8mm。

v13 改动：
  1. 坐垫 e1 0.62→0.87, e2 0.78→0.92, crown 20→8mm, squash 6→4mm, 厚 205→178mm
  2. 扶手垫 e1 0.70→0.88, e2 0.86→0.94, crown 10→6mm, ARM_TOP 52→49cm
  3. 靠垫 e1 0.58→0.82, e2 0.72→0.90, crown 26→12mm
  4. 底架前沿露出【底架线】——原版坐垫下方能看到底架前沿的一道横线
  5. 滚边维持可见性（v12 的加粗/半嵌参数保留）
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
M_WELT = B.pbr("U_dark", "#4A4438", 0.78)
M_ALU = B.pbr("U_metal", "#C9CCD0", 0.18, 1.0)
M_THREAD = B.pbr("U_thread", "#8A7E68", 0.85)

W, D = 2.24, 0.90
DECK_H = 0.15
LEG_H = 0.15
DECK_TOP = LEG_H
SEAT_TOP = 0.43
ARM_TOP = 0.49        # 【v13】52 → 49cm（原版扶手只比座面高一点）
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
# 座板：略窄于底架 → 四周留出台阶（原版能看到坐垫下面有一圈退进的底座）
seat_deck = B.box("seat_deck", (deck_w - 0.055, deck_d - 0.055, 0.024),
                  (0, 0, DECK_TOP + 0.012), M_UPDK)
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

# ================= 坐垫：扁平软板（v13 核心修正） =================
SEAT_N = 3
SEAT_W = (W - 0.30) / SEAT_N - 0.020
SEAT_D = SEAT_FRONT - SEAT_BACK
SEAT_X0 = -(W - 0.30) / 2 + SEAT_W / 2 + 0.010
SEAT_BOT = DECK_TOP + 0.024
SEAT_T = 0.178            # 【v13】205 → 178mm

seat_objs = []
for k in range(SEAT_N):
    cx = SEAT_X0 + k * (SEAT_W + 0.020)
    cy = (SEAT_BACK + SEAT_FRONT) / 2
    c = B.superellipsoid_soft(
        "seat_%d" % k, (SEAT_W, SEAT_D, SEAT_T),
        (cx, cy, SEAT_BOT + SEAT_T / 2), M_UP,
        e1=0.87, e2=0.92, res_u=72, res_v=40,
        squash_top=0.004, crown=0.008)
    add_slack_wrinkles(c, amp=0.0032, freq=16.0, seed=k * 7 + 3,
                       low_z=SEAT_BOT + SEAT_T * 0.42)
    objs.append(c)
    seat_objs.append((c, cx, cy))

# ================= 靠垫：薄片 + 前倾 =================
BC_N = 3
BC_W = (W - 0.34) / BC_N - 0.018
BC_X0 = -(W - 0.34) / 2 + BC_W / 2 + 0.009
BC_H = 0.395
BC_T = 0.150          # 【v13】175 → 150mm（薄片）
BC_CZ = SEAT_TOP + BC_H / 2 - 0.008
BC_CY = BACK_F + BC_T / 2 - 0.022

backc_objs = []
for k in range(BC_N):
    cx = BC_X0 + k * (BC_W + 0.018)
    bc = B.superellipsoid_soft(
        "backc_%d" % k, (BC_W, BC_T, BC_H),
        (cx, BC_CY, BC_CZ), M_UP,
        e1=0.82, e2=0.90, res_u=64, res_v=36,
        squash_top=0.006, crown=0.012)
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


# ================= 扶手：侧板 + 扁平软板扶手垫 =================
ARM_W = 0.205
ARM_SIDE_TOP = 0.390
ARM_PAD_T = 0.100       # 【v13】120 → 100mm
ARM_PAD_W = ARM_W + 0.018

arm_pad_objs = []
for sx in (-1, 1):
    nm = 'L' if sx < 0 else 'R'
    ax = sx * (W / 2 - ARM_W / 2)
    ad = ARM_FRONT - ARM_BACK
    acy = (ARM_FRONT + ARM_BACK) / 2

    side = B.box("arm_side_" + nm, (ARM_W, ad, ARM_SIDE_TOP - DECK_TOP),
                 (ax, acy, DECK_TOP + (ARM_SIDE_TOP - DECK_TOP) / 2), M_UPDK)
    B.bevel(side, 0.026, 4); B.subsurf(side, 2); objs.append(side)

    pad = B.superellipsoid_soft(
        "arm_pad_" + nm, (ARM_PAD_W, ad - 0.012, ARM_PAD_T),
        (ax, acy, ARM_SIDE_TOP + ARM_PAD_T / 2 - 0.002), M_UP,
        e1=0.88, e2=0.94, res_u=64, res_v=28,
        squash_top=0.004, crown=0.006)
    for v in pad.data.vertices:
        t = (v.co.y - ARM_BACK) / ad
        if t > 0.76:
            k = (t - 0.76) / 0.24
            v.co.x = ax + (v.co.x - ax) * (1 - 0.12 * k)
            v.co.z -= 0.010 * k
        if v.co.z > ARM_SIDE_TOP + ARM_PAD_T - 0.040:
            v.co.z -= 0.0028 * math.cos((v.co.y - acy) / ad * math.pi)
    add_slack_wrinkles(pad, amp=0.0020, freq=13.0, seed=7 if sx < 0 else 19,
                       low_z=ARM_SIDE_TOP + ARM_PAD_T * 0.50)
    objs.append(pad)
    arm_pad_objs.append((pad, ax, acy, nm, sx, ad))

# 靠背框
back = B.box("backrest", (W - 0.22, BACK_T, BACK_TOP - DECK_TOP),
             (0, BACK_CY, (DECK_TOP + BACK_TOP) / 2), M_UP)
B.bevel(back, 0.034, 5); B.subsurf(back, 3)
for v in back.data.vertices:
    h = (v.co.z - DECK_TOP) / (BACK_TOP - DECK_TOP)
    v.co.y -= BACK_TILT * h * h
    if v.co.z > BACK_TOP - 0.06:
        v.co.x *= 0.994
B.smart_uv(back); objs.append(back)

# ================= 滚边 =================
PIPE_R = 0.0100
PIPE_LIFT = 0.0038

for k, (c, cx, cy) in enumerate(seat_objs):
    pts = []
    for i in range(41):
        a = 2 * math.pi * i / 40
        pts.append((cx + (SEAT_W / 2) * math.cos(a),
                    cy + (SEAT_D / 2) * math.sin(a),
                    SEAT_BOT + SEAT_T * 0.40))
    objs.append(B.pipe_on_surface("seat_pipe_%d" % k, pts, c, M_WELT,
                                  r=PIPE_R, lift=PIPE_LIFT))

for k, (c, cx) in enumerate(backc_objs):
    pts = []
    for i in range(29):
        a = math.pi * i / 28 - math.pi / 2
        pts.append((cx + (BC_W / 2 - 0.004) * math.cos(a),
                    BACK_F - 0.014,
                    BC_CZ - BC_H / 2 + 0.034 + 0.034 * math.cos(a)))
    objs.append(B.pipe_on_surface("backc_pipe_%d" % k, pts, c, M_WELT,
                                  r=0.0088, lift=0.0034))

for pad, ax, acy, nm, sx, ad in arm_pad_objs:
    pts = []
    for i in range(49):
        a = 2 * math.pi * i / 48
        pts.append((ax + (ARM_PAD_W / 2) * math.cos(a),
                    acy + (ad - 0.020) / 2 * math.sin(a),
                    ARM_TOP - 0.012))
    objs.append(B.pipe_on_surface("arm_pipe_" + nm, pts, pad, M_WELT,
                                  r=0.0090, lift=0.0034))

objs.append(B.pipe_path("back_pipe_top", [
    (-(W - 0.34) / 2, BACK_CY - BACK_TILT - 0.004, BACK_TOP - 0.004),
    (0, BACK_CY - BACK_TILT - 0.010, BACK_TOP - 0.004),
    ((W - 0.34) / 2, BACK_CY - BACK_TILT - 0.004, BACK_TOP - 0.004),
], M_WELT, r=0.0086))

# 底架前沿滚边（原版坐垫下那道横线）
objs.append(B.pipe_rect("deck_pipe_front", 0, deck_d / 2 - RAIL / 2, DECK_TOP - DECK_H / 2,
                         deck_w - 0.006, RAIL - 0.006, M_WELT, r=0.0058))
# 座板前沿滚边（v13 新增：坐垫与底架之间的分层线）
objs.append(B.pipe_rect("seatdeck_pipe", 0, (deck_d - 0.055) / 2, DECK_TOP + 0.020,
                         deck_w - 0.060, 0.008, M_WELT, r=0.0050))

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
    for i in range(81):
        a = 2 * math.pi * i / 80
        pts.append((cx + (SEAT_W / 2 - 0.013) * math.cos(a),
                    cy + (SEAT_D / 2 - 0.013) * math.sin(a),
                    SEAT_BOT + SEAT_T * 0.28))
    objs += stitch_on_surface("seat_stitch_%d" % k, pts, c, M_THREAD)

for k, (c, cx, cy) in enumerate(seat_objs):
    for j, fx in enumerate((-0.24, 0.02, 0.28)):
        x = cx + fx * SEAT_W
        pts = []
        for i in range(31):
            t = i / 30
            yy = cy - (SEAT_D / 2 - 0.030) + (SEAT_D - 0.060) * t
            zz = SEAT_BOT + SEAT_T * 0.90 + 0.010 * math.sin(t * math.pi)
            pts.append((x, yy, zz))
        objs += stitch_on_surface("seat_tuft_%d_%d" % (k, j), pts, c, M_THREAD,
                                  r=0.00082, length=0.009, gap=0.005)

objs += B.stitch_line("back_stitch",
                      (-(W - 0.40) / 2, BACK_CY - 0.022, BACK_TOP - 0.055),
                      ((W - 0.40) / 2, BACK_CY - 0.022, BACK_TOP - 0.055),
                      M_THREAD, r=0.00095, lift=0.002)

for pad, ax, acy, nm, sx, ad in arm_pad_objs:
    pts = []
    for i in range(25):
        t = i / 24
        pts.append((ax + sx * (ARM_PAD_W / 2 + 0.002),
                    ARM_BACK + 0.08 + (ARM_FRONT - 0.14 - ARM_BACK - 0.08) * t,
                    ARM_TOP - 0.052))
    objs += stitch_on_surface("arm_stitch_" + nm, pts, pad, M_THREAD)

for o in list(objs):
    if o.type == 'MESH':
        B.apply_mods(o)

B.export(OUT)
print("OK sofa v13 ->", OUT, "objects:", len(objs))

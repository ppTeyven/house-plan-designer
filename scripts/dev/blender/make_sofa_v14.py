"""sofa v14 — 坐垫/扶手做成【平整顶面 + 圆肩】（真实软包形态）

v13 与原版并排对比后，剩下的最大差异是「扶手形态」：

  原版实拍：扶手顶面是一条【平直线】，两侧圆肩收下去，前端切角
  v13：     扶手是【圆滚滚的枕卷】，顶面是圆拱 —— 读作抱枕，不像扶手板

根因：超椭球的顶永远是圆拱（z = hz * |sin v|^e1）。真实软包是织物
绷在框上、上面被手/臀压平，所以顶面应该是平的、只有边缘圆转。

v14 用 B.superellipsoid_soft 的新参数 top_clamp 做顶面压平：
  · 顶面高于 top_clamp 的顶点被压到同一高度 → 得到平整台面
  · 压平后边缘自然形成圆肩（连续曲率不断裂）

同时：
  · 坐垫：顶面压平到 43cm（座高），得到真实坐垫的平整受压面
  · 扶手：顶面压平到 49cm，前端用 front_clamp 做切角收头
  · 靠垫：前面压平（受压面），保留饱满的顶部
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
ARM_TOP = 0.49
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


def add_slack_wrinkles(o, amp=0.0032, freq=17.0, seed=0, low_z=None, high_z=None):
    random.seed(seed)
    for v in o.data.vertices:
        if low_z is not None and v.co.z < low_z:
            continue
        if high_z is not None and v.co.z > high_z:
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

# ================= 坐垫：平整顶面 + 圆肩 =================
SEAT_N = 3
SEAT_W = (W - 0.30) / SEAT_N - 0.020
SEAT_D = SEAT_FRONT - SEAT_BACK
SEAT_X0 = -(W - 0.30) / 2 + SEAT_W / 2 + 0.010
SEAT_BOT = DECK_TOP + 0.024
SEAT_T = 0.178
SEAT_CZ = SEAT_BOT + SEAT_T / 2

seat_objs = []
for k in range(SEAT_N):
    cx = SEAT_X0 + k * (SEAT_W + 0.020)
    cy = (SEAT_BACK + SEAT_FRONT) / 2
    # 【v14】top_clamp 把顶面压平到「座高 - 2mm」（中央略低两毫米更真实）
    c = B.superellipsoid_soft(
        "seat_%d" % k, (SEAT_W, SEAT_D, SEAT_T),
        (cx, cy, SEAT_CZ), M_UP,
        e1=0.87, e2=0.92, res_u=80, res_v=44,
        squash_top=0.003, crown=0.006,
        top_clamp=SEAT_TOP - 0.002)
    # 顶面中央再微微下凹（久坐的凹陷）
    for v in c.data.vertices:
        if v.co.z > SEAT_TOP - 0.012:
            rr = min(1.0, math.hypot((v.co.x - cx) / (SEAT_W / 2),
                                      (v.co.y - cy) / (SEAT_D / 2)))
            v.co.z -= 0.005 * math.cos(rr * math.pi / 2)
    add_slack_wrinkles(c, amp=0.0030, freq=16.0, seed=k * 7 + 3,
                       low_z=SEAT_BOT + SEAT_T * 0.40)
    objs.append(c)
    seat_objs.append((c, cx, cy))

# ================= 靠垫：前面压平（受压面） =================
BC_N = 3
BC_W = (W - 0.34) / BC_N - 0.018
BC_X0 = -(W - 0.34) / 2 + BC_W / 2 + 0.009
BC_H = 0.395
BC_T = 0.150
BC_CZ = SEAT_TOP + BC_H / 2 - 0.008
BC_CY = BACK_F + BC_T / 2 - 0.022

backc_objs = []
for k in range(BC_N):
    cx = BC_X0 + k * (BC_W + 0.018)
    bc = B.superellipsoid_soft(
        "backc_%d" % k, (BC_W, BC_T, BC_H),
        (cx, BC_CY, BC_CZ), M_UP,
        e1=0.82, e2=0.90, res_u=64, res_v=40,
        squash_top=0.006, crown=0.012,
        front_clamp=BC_CY + BC_T * 0.34)
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

# ================= 扶手：侧板 + 平顶软板 =================
ARM_W = 0.205
ARM_SIDE_TOP = 0.390
ARM_PAD_T = 0.100
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

    # 【v14】顶面压平到 ARM_TOP，前端用 front_clamp 切角
    pad = B.superellipsoid_soft(
        "arm_pad_" + nm, (ARM_PAD_W, ad - 0.012, ARM_PAD_T),
        (ax, acy, ARM_SIDE_TOP + ARM_PAD_T / 2 - 0.002), M_UP,
        e1=0.88, e2=0.94, res_u=72, res_v=32,
        squash_top=0.003, crown=0.005,
        top_clamp=ARM_TOP,
        front_clamp=ARM_FRONT - 0.018)
    for v in pad.data.vertices:
        t = (v.co.y - ARM_BACK) / ad
        if t > 0.80:
            k = (t - 0.80) / 0.20
            v.co.x = ax + (v.co.x - ax) * (1 - 0.10 * k)
            v.co.z -= 0.006 * k
    add_slack_wrinkles(pad, amp=0.0020, freq=13.0, seed=7 if sx < 0 else 19,
                       low_z=ARM_SIDE_TOP + ARM_PAD_T * 0.45)
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

# 坐垫滚边走「顶面与侧面的交界圆肩」处（top_clamp 造成的折线位置）
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
                    BACK_F - 0.014,
                    BC_CZ - BC_H / 2 + 0.034 + 0.034 * math.cos(a)))
    objs.append(B.pipe_on_surface("backc_pipe_%d" % k, pts, c, M_WELT,
                                  r=0.0088, lift=0.0034))

for pad, ax, acy, nm, sx, ad in arm_pad_objs:
    pts = []
    for i in range(57):
        a = 2 * math.pi * i / 56
        pts.append((ax + (ARM_PAD_W / 2 + 0.001) * math.cos(a),
                    acy + (ad - 0.020) / 2 * math.sin(a),
                    ARM_TOP - 0.022))
    objs.append(B.pipe_on_surface("arm_pipe_" + nm, pts, pad, M_WELT,
                                  r=0.0090, lift=0.0034))

objs.append(B.pipe_path("back_pipe_top", [
    (-(W - 0.34) / 2, BACK_CY - BACK_TILT - 0.004, BACK_TOP - 0.004),
    (0, BACK_CY - BACK_TILT - 0.010, BACK_TOP - 0.004),
    ((W - 0.34) / 2, BACK_CY - BACK_TILT - 0.004, BACK_TOP - 0.004),
], M_WELT, r=0.0086))

objs.append(B.pipe_rect("deck_pipe_front", 0, deck_d / 2 - RAIL / 2, DECK_TOP - DECK_H / 2,
                         deck_w - 0.006, RAIL - 0.006, M_WELT, r=0.0058))
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


# 坐垫缝线（顶面与侧面的交界）
for k, (c, cx, cy) in enumerate(seat_objs):
    pts = []
    for i in range(89):
        a = 2 * math.pi * i / 88
        pts.append((cx + (SEAT_W / 2 - 0.011) * math.cos(a),
                    cy + (SEAT_D / 2 - 0.011) * math.sin(a),
                    SEAT_TOP - 0.046))
    objs += stitch_on_surface("seat_stitch_%d" % k, pts, c, M_THREAD)

# 绗缝分线
for k, (c, cx, cy) in enumerate(seat_objs):
    for j, fx in enumerate((-0.24, 0.02, 0.28)):
        x = cx + fx * SEAT_W
        pts = []
        for i in range(31):
            t = i / 30
            yy = cy - (SEAT_D / 2 - 0.030) + (SEAT_D - 0.060) * t
            zz = SEAT_TOP - 0.004 + 0.006 * math.sin(t * math.pi)
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
                    ARM_TOP - 0.048))
    objs += stitch_on_surface("arm_stitch_" + nm, pts, pad, M_THREAD)

for o in list(objs):
    if o.type == 'MESH':
        B.apply_mods(o)

B.export(OUT)
print("OK sofa v14 ->", OUT, "objects:", len(objs))

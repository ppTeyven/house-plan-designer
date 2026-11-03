"""sofa 模块库 —— 把 v14 的沙发骨架参数化，供 P1 批次派生（实测踩坑）】

【为什么抽出来】
沙发是复用率最高的家具（P1 批次里有 20 款沙发/椅凳）。
v14 把一切写死在 make_sofa_v14.py 的脚本顶层，换款式就只能整份复制粘贴，
结果每款都在偷偷改参数 → 尺寸/配色/缝制细节渐渐不一致。

这里把 v14 的建法抽成参数：
  · build_sofa_modules()  产出【一套坐垫/靠垫/扶手/底架】
  · 每个模块的位置与数量由调用方给
这样 L 形 / U 形 / 扶手椅 / 贵妃椅 都从同一套软包体系长出来，
配色、滚边半径、针脚密度、指数全部自动一致 —— 这正是"配套不违和"的前提。

【核心不变量（不要在这里改，各款式共用）】
  SEAT_T     坐垫厚 178mm
  ARM_TOP    扶手顶 490mm
  BACK_TOP   靠背顶 870mm
  PIPE_R     滚边半径 10mm
  指数       e1=0.87 e2=0.92（扁平软板，不是棉花糖）
"""
import bpy
import math
import mathutils

import bl_lib as B

# ---- 共用不变量 ----
SEAT_T = 0.178
ARM_TOP = 0.49
BACK_TOP = 0.87
BACK_T = 0.13
BACK_TILT = 0.020
DECK_H = 0.15
DECK_TOP = 0.15
SEAT_TOP = 0.43

PIPE_R = 0.0100
PIPE_LIFT = 0.0038
THREAD_R = 0.00095

# 软包指数（扁平软板）
E1_SEAT, E2_SEAT = 0.87, 0.92
E1_BACK, E2_BACK = 0.82, 0.90
E1_ARM, E2_ARM = 0.88, 0.94


def add_slack_wrinkles(o, amp=0.0030, freq=16.0, seed=0, low_z=None):
    """布料松弛褶皱（真实软包不是完美光滑的）"""
    import random
    random.seed(seed)
    for v in o.data.vertices:
        if low_z is not None and v.co.z < low_z:
            continue
        n1 = math.sin(v.co.x * freq + seed * 1.3) * math.sin(v.co.y * freq * 0.87 + seed * 0.7)
        n2 = math.sin((v.co.x * 0.62 + v.co.y * 0.78) * freq * 1.31 + seed * 2.1)
        v.co.z += (n1 * 0.62 + n2 * 0.38) * amp
    return o


def stitch_on_surface(name, pts, surface, material, r=THREAD_R, lift=0.0026,
                      length=0.010, gap=0.006, out=None):
    """沿曲面生成真实针脚几何（每针一根独立短线段）。

    与 pipe_on_surface 同源：先投射到曲面 + 沿法线抬升，再按针距切段。
    针脚也必须贴曲面，否则会浮在空中或埋进布里。

    【v17 效率】所有针脚合成【一个曲线对象】（B.stitch_poly），
    而不是每针一个 mesh —— 见 bl_lib.stitch_poly 的效率说明。
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
    res = B.stitch_poly(name, segments, material, r=r)
    if out is not None:
        out.extend(res)
    return res


def seat_cushion(name, cx, cy, w, d, mats, seed=0, bot=None, top=None):
    """单块坐垫：平整顶面 + 圆肩（真实软包形态）"""
    bot = DECK_TOP + 0.024 if bot is None else bot
    top = SEAT_TOP if top is None else top
    t = top - bot
    c = B.superellipsoid_soft(
        name, (w, d, t), (cx, cy, bot + t / 2), mats["up"],
        e1=E1_SEAT, e2=E2_SEAT, res_u=80, res_v=44,
        squash_top=0.003, crown=0.006, top_clamp=top - 0.002)
    for v in c.data.vertices:
        if v.co.z > top - 0.012:
            rr = min(1.0, math.hypot((v.co.x - cx) / (w / 2), (v.co.y - cy) / (d / 2)))
            v.co.z -= 0.005 * math.cos(rr * math.pi / 2)
    add_slack_wrinkles(c, amp=0.0030, freq=16.0, seed=seed, low_z=bot + t * 0.40)
    return c


def back_cushion(name, cx, cy, w, h, t, mats, seed=0, tilt=-9.0):
    """单块靠垫：前面压平（受压面）+ 前倾"""
    cz = SEAT_TOP + h / 2 - 0.008
    bc = B.superellipsoid_soft(
        name, (w, t, h), (cx, cy, cz), mats["up"],
        e1=E1_BACK, e2=E2_BACK, res_u=64, res_v=40,
        squash_top=0.006, crown=0.012, front_clamp=cy + t * 0.34)
    a = math.radians(tilt)
    for v in bc.data.vertices:
        dy = v.co.y - cy
        dz = v.co.z - cz
        v.co.y = cy + dy * math.cos(a) - dz * math.sin(a)
        v.co.z = cz + dy * math.sin(a) + dz * math.cos(a)
    add_slack_wrinkles(bc, amp=0.0026, freq=15.0, seed=seed, low_z=cz - h * 0.30)
    return bc, cz


def arm_pad(name, ax, cy, w, d, mats, seed=0, top=None, front_clamp=None):
    """扶手垫：平顶软板 + 前端切角"""
    top = ARM_TOP if top is None else top
    side_top = top - 0.100
    pad = B.superellipsoid_soft(
        name, (w, d, 0.100), (ax, cy, side_top + 0.050 - 0.002), mats["up"],
        e1=E1_ARM, e2=E2_ARM, res_u=72, res_v=32,
        squash_top=0.003, crown=0.005, top_clamp=top,
        front_clamp=front_clamp)
    for v in pad.data.vertices:
        t = (v.co.y - (cy - d / 2)) / d
        if t > 0.80:
            k = (t - 0.80) / 0.20
            v.co.x = ax + (v.co.x - ax) * (1 - 0.10 * k)
            v.co.z -= 0.006 * k
    add_slack_wrinkles(pad, amp=0.0020, freq=13.0, seed=seed,
                       low_z=side_top + 0.045)
    return pad, side_top


def leg_set(name, x0, x1, y0, y1, mats, objs, n_x=3, n_y=2, skip_center_front=True):
    """抛光铝脚（细、外撇）+ 脚杯"""
    LEG_R = 0.019
    LEG_H = 0.15
    xs = [x0 + (x1 - x0) * i / max(1, n_x - 1) for i in range(n_x)]
    ys = [y0 + (y1 - y0) * i / max(1, n_y - 1) for i in range(n_y)]
    for ix, fx in enumerate(xs):
        for iy, fy in enumerate(ys):
            if skip_center_front and ix == (n_x - 1) // 2 and iy == n_y - 1:
                continue
            splay = 0.014
            ox = math.copysign(splay, fx) if abs(fx) > 1e-6 else 0.0
            oy = math.copysign(splay, fy)
            objs.append(B.cyl("%s_leg_%d_%d" % (name, ix, iy), LEG_R, LEG_H,
                               (fx + ox, fy + oy, LEG_H / 2), mats["metal"],
                               verts=20, r2=LEG_R * 1.25))
            objs.append(B.cyl("%s_cup_%d_%d" % (name, ix, iy), LEG_R * 1.30, 0.010,
                               (fx, fy, LEG_H - 0.003), mats.get("dark") or mats["updk"],
                               verts=16))


def deck(name, cx, cy, w, d, mats, objs, rail=0.075):
    """薄层软包底架（四周有退进的台阶）"""
    for nm, y in (("front", cy + d / 2 - rail / 2), ("rear", cy - d / 2 + rail / 2)):
        r = B.box("%s_deck_%s" % (name, nm), (w, rail, DECK_H),
                  (cx, y, DECK_TOP - DECK_H / 2), mats["updk"])
        B.bevel(r, 0.012, 3)
        B.subsurf(r, 2)
        objs.append(r)
    for sx in (-1, 1):
        x = cx + sx * (w / 2 - rail / 2)
        r = B.box("%s_deck_side_%s" % (name, 'L' if sx < 0 else 'R'),
                  (rail, d - rail * 2, DECK_H),
                  (x, cy, DECK_TOP - DECK_H / 2), mats["updk"])
        B.bevel(r, 0.012, 3)
        B.subsurf(r, 2)
        objs.append(r)
    sd = B.box("%s_seat_deck" % name, (w - 0.055, d - 0.055, 0.024),
               (cx, cy, DECK_TOP + 0.012), mats["updk"])
    B.bevel(sd, 0.009, 3)
    objs.append(sd)


def back_shell(name, cx, cy, w, mats, objs, top=None):
    """靠背框（后倾的硬结构）"""
    top = BACK_TOP if top is None else top
    back = B.box(name, (w, BACK_T, top - DECK_TOP),
                 (cx, cy, (DECK_TOP + top) / 2), mats["up"])
    B.bevel(back, 0.034, 5)
    B.subsurf(back, 3)
    for v in back.data.vertices:
        h = (v.co.z - DECK_TOP) / (top - DECK_TOP)
        v.co.y -= BACK_TILT * h * h
        if v.co.z > top - 0.06:
            v.co.x = cx + (v.co.x - cx) * 0.994
    B.smart_uv(back)
    objs.append(back)
    return back


def pipe_ring_equator(name, cx, cy, w, d, z, surface, mats, objs):
    """坐垫赤道滚边（贴合曲面，半嵌进布面）"""
    pts = []
    for i in range(41):
        a = 2 * math.pi * i / 40
        pts.append((cx + (w / 2 + 0.001) * math.cos(a),
                    cy + (d / 2 + 0.001) * math.sin(a), z))
    objs.append(B.pipe_on_surface(name, pts, surface, mats["welt"],
                                  r=PIPE_R, lift=PIPE_LIFT))


def pipe_back_bottom(name, cx, y, w, z0, surface, mats, objs):
    """靠垫底沿滚边"""
    pts = []
    for i in range(29):
        a = math.pi * i / 28 - math.pi / 2
        pts.append((cx + (w / 2 - 0.004) * math.cos(a),
                    y, z0 + 0.034 + 0.034 * math.cos(a)))
    objs.append(B.pipe_on_surface(name, pts, surface, mats["welt"],
                                  r=0.0088, lift=0.0034))


def pipe_arm_top(name, ax, cy, w, d, z, surface, mats, objs):
    """扶手垫顶缘滚边"""
    pts = []
    for i in range(57):
        a = 2 * math.pi * i / 56
        pts.append((ax + (w / 2 + 0.001) * math.cos(a),
                    cy + (d / 2 - 0.010) * math.sin(a), z))
    objs.append(B.pipe_on_surface(name, pts, surface, mats["welt"],
                                  r=0.0090, lift=0.0034))

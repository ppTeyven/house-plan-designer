"""sofa v6 — William 流程重做（基于 bl_lib：网格坐标=世界坐标，杜绝尺寸/落地歧义）

Part1 蓝图比例 : Zanotta William 实测尺寸 W2240 D940 H700 座高430 扶手高620
Part2 布料解算 : Cloth + pressure_factor 真解算吹鼓坐垫
Part3 布刷褶皱 : 解算后按布刷思路加褶 + 边缘松量 + 缝线拉力
Part6 真实针脚 : 每针独立几何短线段
包边          : 曲线 + 圆截面，直径一致
"""
import bpy, math, os, sys, random, mathutils

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bl_lib as B

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))),
                   "验收", "models", "sofa.glb")
os.makedirs(os.path.dirname(OUT), exist_ok=True)

B.wipe()

# ================= 材质 =================
M_UP    = B.fabric("U_upholstery", "#c9bba6")
M_UPDK  = B.fabric("U_upholsterydk", "#9d8f7a")
M_FAB   = B.fabric("U_fabric", "#f2ede2")
M_WELT  = B.pbr("U_dark", "#4a4238", 0.72)
M_METAL = B.pbr("U_metal", "#22252a", 0.30, 0.92)
M_BRASS = B.pbr("U_brass", "#a8843e", 0.26, 1.0)
M_WOOD  = B.wood("U_wood", "#6b4a2d")
M_THREAD = B.pbr("U_thread", "#d8cdb8", 0.88)
M_OR = B.fabric("pillow_orange", "#d96f2e")
M_BL = B.fabric("pillow_blue", "#2f7fd0")

# ================= 蓝图尺寸 =================
W, D = 2.24, 0.94          # William: 2240 x 940
BASE_H = 0.30              # 底座高
SEAT_TOP = 0.43            # 座高
ARM_TOP = 0.62             # 扶手高
BACK_TOP = 0.70            # 靠背顶

objs = []

# ---------------- 底座 ----------------
# 底座与扶手前沿齐平（深度 D=0.94），只在底部做内收倒角（避免踢脚悬空）
base = B.box("base", (W - 0.16, D, BASE_H), (0, 0, BASE_H / 2), M_UP)
B.bevel(base, 0.02, 3); B.subsurf(base, 3)
objs.append(base)

plinth = B.box("plinth", (W - 0.30, D - 0.06, 0.07), (0, 0, 0.035), M_UPDK)
B.bevel(plinth, 0.006, 2)
objs.append(plinth)

# ---------------- Track 扶手 ----------------
# William 实物扶手与底座前沿齐平：扶手深度取到 D（0.94），前端仅做轻微内收
ARM_W = 0.27
for sx in (-1, 1):
    nm = 'L' if sx < 0 else 'R'
    ax = sx * (W / 2 - ARM_W / 2)
    a = B.box(f"arm_{nm}", (ARM_W, D, ARM_TOP - BASE_H),
              (ax, 0.0, (BASE_H + ARM_TOP) / 2), M_UP)
    B.bevel(a, 0.045, 4); B.subsurf(a, 3)
    for v in a.data.vertices:
        if (v.co.x - ax) * -sx > 0.06 and abs(v.co.y) < 0.30 and v.co.z < BASE_H + 0.06:
            v.co.x += sx * 0.022          # 内侧压出坐垫槽
        if v.co.y > D / 2 - 0.10:
            v.co.y = D / 2 - 0.10 + (v.co.y - (D / 2 - 0.10)) * 0.72
            v.co.x = ax + (v.co.x - ax) * 0.95
            v.co.z -= 0.010               # 前端收窄微垂
    objs.append(a)
    # 扶手顶滚边
    objs.append(B.pipe_rect(f"arm_pipe_{nm}", ax, 0.0, ARM_TOP + 0.002,
                             ARM_W - 0.035, D - 0.02, M_WELT, r=0.0085))
    # 扶手前端竖向滚边（真实弧线）
    objs.append(B.pipe_path(f"arm_front_{nm}", [
        (ax - ARM_W / 2 + 0.022, D / 2 - 0.012, BASE_H + 0.03),
        (ax - ARM_W / 2 + 0.018, D / 2 - 0.010, ARM_TOP - 0.02),
        (ax + ARM_W / 2 - 0.018, D / 2 - 0.010, ARM_TOP - 0.02),
        (ax + ARM_W / 2 - 0.022, D / 2 - 0.012, BASE_H + 0.03),
    ], M_WELT, r=0.008))

# ---------------- 靠背 ----------------
back = B.box("backrest", (W - 0.27, 0.22, BACK_TOP - BASE_H),
             (0, -D / 2 + 0.115, (BASE_H + BACK_TOP) / 2), M_UP)
B.bevel(back, 0.045, 4); B.subsurf(back, 3)
for v in back.data.vertices:
    if v.co.z > BASE_H + 0.34:
        v.co.y += 0.014          # 顶部微前卷
objs.append(back)

# ================= Part2 布料解算：3 块坐垫 =================
SEAT_N = 3
SEAT_W = (W - 0.34) / SEAT_N - 0.018
SEAT_D = D - 0.30
SEAT_X0 = -(W - 0.34) / 2 + SEAT_W / 2 + 0.009
SEAT_Z = BASE_H + 0.085


def cloth_cushion(name, w, d, cx, cy, z, material, pressure=22.0, res=44):
    """真布料解算：平面网格 + Cloth + pressure_factor 从内部吹鼓"""
    o = B.grid(name, w, d, res, (cx, cy, z), material)
    cl = o.modifiers.new("Cloth", 'CLOTH')
    s = cl.settings
    s.quality = 7
    s.mass = 0.30
    s.tension_stiffness = 18.0
    s.compression_stiffness = 18.0
    s.shear_stiffness = 8.0
    s.bending_stiffness = 0.6
    s.air_damping = 1.2
    s.tension_damping = 6.0
    s.compression_damping = 6.0
    s.shear_damping = 6.0
    s.bending_damping = 0.6
    s.vertex_group_mass = "Pins"
    s.pin_stiffness = 1.0
    s.use_pressure = True
    s.pressure_factor = pressure
    s.use_pressure_volume = True
    s.collider_friction = 6.0

    cs = cl.collision_settings
    cs.use_collision = True
    cs.distance_min = 0.006
    cs.use_self_collision = True
    cs.self_distance_min = 0.005
    cs.self_friction = 6.0
    cs.collision_quality = 4
    cs.friction = 6.0

    cnm = "cloth_colliders"
    coll = bpy.data.collections.get(cnm) or bpy.data.collections.new(cnm)
    if cnm not in [c.name for c in bpy.context.scene.collection.children]:
        bpy.context.scene.collection.children.link(coll)
    cs.collection = coll

    # 碰撞体：坐垫托板（底座上表面）
    pad = B.box(name + "_pad", (w * 0.99, d * 0.99, 0.05), (cx, cy, BASE_H + 0.02), None)
    pcol = pad.modifiers.new("Collision", 'COLLISION')
    pcol.settings.use_culling = True
    pcol.settings.thickness_outer = 0.01
    pcol.settings.friction_factor = 8.0
    pad.hide_render = True
    for c in list(pad.users_collection):
        c.objects.unlink(pad)
    coll.objects.link(pad)

    # 钉边（角与边固定，中间自由）
    vg = o.vertex_groups.new(name="Pins")
    for i, v in enumerate(o.data.vertices):
        if abs(v.co.x - cx) > w / 2 * 0.86 or abs(v.co.y - cy) > d / 2 * 0.86:
            vg.add([i], 1.0, 'REPLACE')
    return o, pad


def simulate(o, frames=52):
    sc = bpy.context.scene
    sc.frame_start = 1; sc.frame_end = frames
    for f in range(1, frames + 1):
        sc.frame_set(f)
    sc.frame_set(frames)
    B.activate(o)
    for md in [m.name for m in o.modifiers]:
        try:
            bpy.ops.object.modifier_apply(modifier=md)
        except Exception as e:
            print("apply fail", o.name, md, e)


def brush_wrinkles(o, amp=0.0055, freq=19.0, seed=0):
    random.seed(seed)
    for v in o.data.vertices:
        v.co.z += (math.sin(v.co.x * freq + seed * 1.3) * math.sin(v.co.y * freq * 0.87 + seed * 0.7) * 0.62
                   + (random.random() - 0.5) * 0.5) * amp


def edge_slack(o, cx, cy, hw, hd, amp=0.007):
    for v in o.data.vertices:
        u = max(abs(v.co.x - cx) / hw, abs(v.co.y - cy) / hd)
        if u > 0.72:
            k = (u - 0.72) / 0.28
            v.co.z += (math.sin(v.co.x * 37.0) + math.sin(v.co.y * 29.0)) * amp * k


pads = []
cushions = []
print("开始布料解算 3 块坐垫 ...")
for k in range(SEAT_N):
    cx = SEAT_X0 + k * (SEAT_W + 0.018)
    cu, pad = cloth_cushion(f"seat_{k}", SEAT_W, SEAT_D, cx, 0.02, SEAT_Z, M_UP,
                             pressure=22.0, res=44)
    simulate(cu, frames=52)
    print("  simulated", cu.name)
    # 布刷褶皱 + 边缘松量
    brush_wrinkles(cu, amp=0.0055, freq=19.0, seed=k * 3 + 1)
    edge_slack(cu, cx, 0.02, SEAT_W / 2, SEAT_D / 2, amp=0.007)
    # 落座校正：重力下垂会让布穿过底座，抬到坐垫托板高度并压平贴底圈
    zs = [v.co.z for v in cu.data.vertices]
    bottom = BASE_H + 0.045
    shift = bottom - min(zs)
    for v in cu.data.vertices:
        v.co.z += shift
        if v.co.z < bottom + 0.014:
            v.co.z = bottom + (v.co.z - bottom) * 0.32
    # 顶面轻鼓（解算已吹鼓，这里只做极轻的形状微调）
    for v in cu.data.vertices:
        if v.co.z > bottom + 0.04:
            fx = max(0.0, 1.0 - ((v.co.x - cx) / (SEAT_W / 2)) ** 2)
            fy = max(0.0, 1.0 - ((v.co.y - 0.02) / (SEAT_D / 2)) ** 2)
            v.co.z += 0.008 * min(fx, fy)
    B.smart_uv(cu)
    cushions.append(cu)
    pads.append(pad)

# ---------------- 坐垫滚边 + 真实针脚 ----------------
for k, cu in enumerate(cushions):
    cx = SEAT_X0 + k * (SEAT_W + 0.018)
    zs = [v.co.z for v in cu.data.vertices]
    waist = (min(zs) + max(zs)) * 0.5
    objs.append(B.pipe_rect(f"seat_pipe_{k}", cx, 0.02, waist,
                             SEAT_W - 0.006, SEAT_D - 0.006, M_WELT, r=0.0088))
    objs += B.stitch_rect(f"seat_stitch_{k}", cx, 0.02, waist + 0.010,
                          SEAT_W - 0.022, SEAT_D - 0.022, M_THREAD,
                          r=0.00085, inset=0.004, lift=0.002)

# ---------------- 靠垫 ----------------
for k in range(SEAT_N):
    cx = SEAT_X0 + k * (SEAT_W + 0.018)
    c = B.box(f"backc_{k}", (SEAT_W, 0.18, 0.40), (cx, -D / 2 + 0.215, 0.60), M_UP)
    B.bevel(c, 0.042, 4); B.subsurf(c, 3)
    for v in c.data.vertices:
        if v.co.z > 0.74:
            v.co.y += 0.014
        if abs(v.co.x - cx) > SEAT_W * 0.38:
            v.co.z -= 0.012
    B.smart_uv(c)
    objs.append(c)
    objs.append(B.pipe_rect(f"backc_pipe_{k}", cx, -D / 2 + 0.215, 0.60,
                             SEAT_W - 0.01, 0.16, M_WELT, r=0.008))

# ---------------- 抱枕 ----------------
for nm, cx, col, rz in (("pillow_orange", -0.50, M_OR, 0.20), ("pillow_blue", 0.50, M_BL, -0.18)):
    p = B.box(nm, (0.40, 0.13, 0.40), (cx, -D / 2 + 0.28, 0.63), col)
    B.bevel(p, 0.052, 4); B.subsurf(p, 3)
    for v in p.data.vertices:
        if abs(v.co.x - cx) > 0.115 and abs(v.co.z - 0.63) > 0.115:
            v.co.x = cx + (v.co.x - cx) * 0.88
            v.co.z = 0.63 + (v.co.z - 0.63) * 0.88
        if abs(v.co.x - cx) < 0.05 and abs(v.co.z - 0.63) < 0.05 and v.co.y > -D / 2 + 0.31:
            v.co.y -= 0.014
    B.smart_uv(p)
    p["noTheme"] = 1
    objs.append(p)

# ---------------- 靠背顶部滚边 + 针脚 ----------------
objs.append(B.pipe_rect("back_pipe_top", 0, -D / 2 + 0.16, BACK_TOP - 0.005,
                         W - 0.36, 0.185, M_WELT, r=0.009))
objs += B.stitch_rect("back_stitch", 0, -D / 2 + 0.16, BACK_TOP - 0.04,
                      W - 0.40, 0.185, M_THREAD, r=0.00085, inset=0.006, lift=0.002)

# ---------------- 搭毯 ----------------
throw = B.grid("throw", 0.50, 0.86, 26, (W / 2 - 0.135, 0.0, ARM_TOP + 0.022), M_FAB)
for v in throw.data.vertices:
    ax = abs(v.co.x - (W / 2 - 0.135))
    if ax > 0.115:
        v.co.z -= (ax - 0.115) * 1.25
    v.co.z += math.sin(v.co.y * 15.0) * 0.009 + math.sin(v.co.x * 33.0 + v.co.y * 11.0) * 0.004
sm = throw.modifiers.new("Solid", 'SOLIDIFY')
sm.thickness = 0.007
for p in throw.data.polygons:
    p.use_smooth = True
B.smart_uv(throw)
throw["noTheme"] = 1
objs.append(throw)

# ---------------- 车削木腿 + 黄铜脚箍 ----------------
for sx in (-1, 1):
    for sz in (-1, 1):
        x, y = sx * (W / 2 - 0.20), sz * (D / 2 - 0.20)
        for i, (rad, h) in enumerate([(0.032, 0.10), (0.024, 0.072), (0.028, 0.046), (0.019, 0.022)]):
            seg = B.cyl(f"leg_{sx}_{sz}_{i}", rad, 0.026, (x, y, h + 0.013),
                        M_WOOD if i < 3 else M_BRASS, verts=20)
            objs.append(seg)

# ---------------- 清理碰撞体 ----------------
for pad in pads:
    bpy.data.objects.remove(pad, do_unlink=True)

# ---------------- 应用修改器 ----------------
for o in list(objs):
    if o.type == 'MESH':
        B.apply_mods(o)

B.export(OUT)
print("OK sofa v6 ->", OUT, "objects:", len(objs))

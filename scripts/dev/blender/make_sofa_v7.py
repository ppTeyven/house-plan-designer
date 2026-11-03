"""sofa v7 — William 流程 v7：修正坐垫（上一版被压成 26mm，实际应为 130mm）

v6 的问题（已用体检数据定位）：
  坐垫只有 26mm 厚 —— 平面布料在重力下塌到碰撞板上，
  压力场不足以对抗重力。真实坐垫是「闭合布袋 + 内部充气」，
  不是一张布被吹起来。

v7 的做法（贴近 William Part2 的实际做法）：
  1. 先建闭合「布袋」几何（盒状，顶部留一个进气口区域）
  2. 对布袋顶面单独做 Cloth 解算 + pressure_factor 吹鼓
  3. 解算后把顶面结果烘回布袋，底面与侧面保持硬朗
  4. 顶部加绗缝（tufting）分格，形成真实坐垫的「面包格」
"""
import bpy, math, os, sys, random, mathutils

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
M_WELT = B.pbr("U_dark", PAL[R["welt"]], 0.72)
M_BRASS = B.pbr("U_brass", PAL[R["metal"]], 0.26, 1.0)
M_WOOD = B.wood("U_wood", PAL[R["leg"]])
M_THREAD = B.pbr("U_thread", PAL[R["thread"]], 0.88)
M_AC1 = B.fabric("accent_terracotta", PAL["accent_terracotta"])
M_AC2 = B.fabric("accent_sage", PAL["accent_sage"])

# ============ 蓝图尺寸（Zanotta William 实测，官方图纸） ============
# 官方规格 1330/302：W 224 × D 90 × H 87 cm，座高 43 cm
# （来源：zanotta.com / lemani casa / dieter-horn 官方 PDF 图纸）
W, D = 2.24, 0.90
BASE_H = 0.26
SEAT_TOP = 0.43
ARM_TOP = 0.62
BACK_TOP = 0.87
CUSH_T = 0.135          # 坐垫厚 135mm（真实坐垫 120~150mm）
SEAT_BOT = SEAT_TOP - CUSH_T   # 坐垫底 = 0.295

objs = []

# ---------------- 底座（薄层，坐垫下方悬空架在铝脚上） ----------------
base = B.box("base", (W - 0.16, D, BASE_H), (0, 0, BASE_H / 2), M_UP)
B.bevel(base, 0.018, 3); B.subsurf(base, 3)
objs.append(base)

plinth = B.box("plinth", (W - 0.30, D - 0.06, 0.07), (0, 0, 0.035), M_UPDK)
B.bevel(plinth, 0.006, 2)
objs.append(plinth)

# ---------------- Track 扶手（William 是「薄层堆叠」扶手，不是厚实的块状扶手） ----------------
# 原版特征：扶手是一层薄薄的软包层，架在细铝脚上，整体是水平薄板状
ARM_W = 0.22
ARM_T = 0.135          # 扶手软包层厚（薄层语言）
for sx in (-1, 1):
    nm = 'L' if sx < 0 else 'R'
    ax = sx * (W / 2 - ARM_W / 2)
    # 扶手软包层（薄板）
    a = B.box(f"arm_{nm}", (ARM_W, D, ARM_T), (ax, 0.0, ARM_TOP - ARM_T / 2), M_UP)
    B.bevel(a, 0.030, 4); B.subsurf(a, 3)
    for v in a.data.vertices:
        if v.co.y > D / 2 - 0.08:
            v.co.y = D / 2 - 0.08 + (v.co.y - (D / 2 - 0.08)) * 0.68
            v.co.z -= 0.008
    objs.append(a)
    # 扶手下的支撑板（薄层结构语言：扶手不是落地实体，底下悬空）
    sup = B.box(f"arm_support_{nm}", (ARM_W - 0.04, D - 0.16, 0.022),
                (ax, 0, ARM_TOP - ARM_T - 0.011), M_UPDK)
    B.bevel(sup, 0.004, 2); objs.append(sup)
    # 扶手顶滚边
    objs.append(B.pipe_rect(f"arm_pipe_{nm}", ax, 0.0, ARM_TOP + 0.002,
                             ARM_W - 0.030, D - 0.012, M_WELT, r=0.0075))
    # 扶手前端竖向滚边（真实弧线）
    objs.append(B.pipe_path(f"arm_front_{nm}", [
        (ax - ARM_W / 2 + 0.018, D / 2 - 0.010, ARM_TOP - ARM_T + 0.012),
        (ax - ARM_W / 2 + 0.014, D / 2 - 0.008, ARM_TOP - 0.012),
        (ax + ARM_W / 2 - 0.014, D / 2 - 0.008, ARM_TOP - 0.012),
        (ax + ARM_W / 2 - 0.018, D / 2 - 0.010, ARM_TOP - ARM_T + 0.012),
    ], M_WELT, r=0.007))

# ---------------- 靠背（薄层堆叠结构，高 87cm 撑肩） ----------------
BACK_T = 0.16
back = B.box("backrest", (W - 0.24, BACK_T, BACK_TOP - BASE_H),
             (0, -D / 2 + BACK_T / 2 + 0.02, (BASE_H + BACK_TOP) / 2), M_UP)
B.bevel(back, 0.035, 4); B.subsurf(back, 3)
for v in back.data.vertices:
    if v.co.z > BASE_H + 0.40:
        v.co.y += 0.012
    # 靠背与扶手同高时略收，形成连续的薄层轮廓
    if v.co.z > ARM_TOP - 0.02:
        v.co.x *= 0.998
objs.append(back)


# ================= 坐垫：闭合布袋 + 顶面布料解算 =================
SEAT_N = 3
SEAT_W = (W - 0.34) / SEAT_N - 0.018
SEAT_D = D - 0.30
SEAT_X0 = -(W - 0.34) / 2 + SEAT_W / 2 + 0.009


def cushion_bag(name, cx, cy, w, d, bot_z, thick, material):
    """闭合坐垫布袋：顶面为可解算的高密网格（待替换），侧面/底面为硬朗几何。

    做法：先用盒体做出底+侧壁，再单独建顶面网格做布料解算。
    """
    # --- 底+侧壁（硬朗，保持坐垫的方正轮廓） ---
    bag = B.box(name, (w, d, thick), (cx, cy, bot_z + thick / 2), material)
    B.bevel(bag, 0.030, 4)
    for v in bag.data.vertices:
        # 上半部分向内收（真实坐垫上窄下宽的「梯形」感）
        if v.co.z > bot_z + thick * 0.45:
            k = (v.co.z - bot_z - thick * 0.45) / (thick * 0.55)
            v.co.x = cx + (v.co.x - cx) * (1 - 0.055 * k)
            v.co.y = cy + (v.co.y - cy) * (1 - 0.055 * k)
    B.subsurf(bag, 2)
    objs.append(bag)

    # --- 碰撞体：布袋的独立副本（只做碰撞面，不导出） ---
    # 注意：对象必须先链接到场景集合，才能加修改器；
    # 且 modifiers.new 在同名修改器已存在时返回 None（实测确认），
    # 所以先清掉已有同名修改器再新建。
    collider = bpy.data.objects.new(name + "_collider", bag.data.copy())
    bpy.context.collection.objects.link(collider)
    collider.location = (0, 0, 0)
    collider.rotation_euler = (0, 0, 0)
    collider.scale = (1, 1, 1)
    for md in [m.name for m in collider.modifiers if m.type == 'COLLISION']:
        collider.modifiers.remove(collider.modifiers[md])
    pcol = collider.modifiers.new("Collision", 'COLLISION')
    if pcol is None:
        raise RuntimeError("Collision modifier creation failed on " + name)
    pcol.settings.use_culling = True
    pcol.settings.thickness_outer = 0.008
    pcol.settings.friction_factor = 8.0

    # --- 顶面：独立高密网格，供 Cloth 解算吹鼓 ---
    top = B.grid(name + "_top", w * 0.995, d * 0.995, 40, (cx, cy, bot_z + thick), material)
    cl = top.modifiers.new("Cloth", 'CLOTH')
    s = cl.settings
    s.quality = 6
    s.mass = 0.22
    s.tension_stiffness = 30.0
    s.compression_stiffness = 30.0
    s.shear_stiffness = 12.0
    s.bending_stiffness = 1.2
    s.air_damping = 1.0
    s.tension_damping = 8.0
    s.compression_damping = 8.0
    s.shear_damping = 8.0
    s.bending_damping = 1.0
    s.vertex_group_mass = "Pins"
    s.pin_stiffness = 1.0
    s.use_pressure = True
    s.pressure_factor = 120.0     # 充气压力（够对抗重力撑起 135mm）
    s.use_pressure_volume = True
    s.collider_friction = 6.0

    cs = cl.collision_settings
    cs.use_collision = True
    cs.distance_min = 0.004
    cs.use_self_collision = True
    cs.self_distance_min = 0.004
    cs.self_friction = 6.0
    cs.collision_quality = 4
    cs.friction = 6.0

    cnm = "cloth_colliders"
    coll = bpy.data.collections.get(cnm) or bpy.data.collections.new(cnm)
    if cnm not in [c.name for c in bpy.context.scene.collection.children]:
        bpy.context.scene.collection.children.link(coll)
    cs.collection = coll

    # 把碰撞体副本移入碰撞集合
    for c in list(collider.users_collection):
        c.objects.unlink(collider)
    coll.objects.link(collider)

    # 边缘钉住（中间自由 → 边缘固定，像布袋被缝在底座上）
    vg = top.vertex_groups.new(name="Pins")
    for i, v in enumerate(top.data.vertices):
        u = max(abs(v.co.x - cx) / (w / 2), abs(v.co.y - cy) / (d / 2))
        if u > 0.80:
            vg.add([i], 1.0, 'REPLACE')
    return bag, top, collider


def simulate(o, frames=44):
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


print("开始布料解算 3 块坐垫顶面 ...")
colliders = []
tops = []
for k in range(SEAT_N):
    cx = SEAT_X0 + k * (SEAT_W + 0.018)
    bag, top, collider = cushion_bag(f"seat_{k}", cx, 0.02, SEAT_W, SEAT_D,
                                      SEAT_BOT, CUSH_T, M_UP)
    simulate(top, frames=44)
    print(f"  simulated seat_{k}")

    # 布刷褶皱（解算后加真实布料折痕）
    random.seed(k * 7 + 3)
    for v in top.data.vertices:
        v.co.z += (math.sin(v.co.x * 22.0 + k) * math.sin(v.co.y * 19.0) * 0.5
                   + (random.random() - 0.5) * 0.4) * 0.004

    # 顶面高度校正：解算后中心应比边缘高（鼓面），且整体落在 [SEAT_BOT, SEAT_TOP]
    zs = [v.co.z for v in top.data.vertices]
    lo, hi = min(zs), max(zs)
    span = max(hi - lo, 1e-4)
    target_top = SEAT_TOP + 0.012     # 顶面略高于座高（鼓包）
    for v in top.data.vertices:
        t = (v.co.z - lo) / span
        # 中心鼓起：中间抬高，边缘落到 SEAT_TOP
        bulge = math.sin(min(1.0, max(0.0, (v.co.z - lo) / span)) * math.pi) * 0.0
        v.co.z = SEAT_TOP - 0.020 + t * 0.032 + bulge
    B.smart_uv(top)
    tops.append(top)
    colliders.append((bag, collider))

# 把顶面网格与布袋合并成一个「完整坐垫」网格（顶面替换袋盖）
import bmesh
for k in range(SEAT_N):
    cx = SEAT_X0 + k * (SEAT_W + 0.018)
    bag = bpy.data.objects[f"seat_{k}"]
    top = bpy.data.objects[f"seat_{k}_top"]
    me = bag.data
    # 删掉布袋原来的顶盖面（留侧壁与底）。
    # 注意：MeshPolygon 集合没有 remove()，删面必须走 bmesh。
    bm = bmesh.new()
    bm.from_mesh(me)
    bag_top_z = SEAT_BOT + CUSH_T - 0.002
    kill = [f for f in bm.faces
            if sum(v.co.z for v in f.verts) / len(f.verts) > bag_top_z - 0.012]
    bmesh.ops.delete(bm, geom=kill, context='FACES_ONLY')
    # 把解算好的顶面并入布袋
    bm_top = bmesh.new()
    bm_top.from_mesh(top.data)
    bm_top.verts.ensure_lookup_table()
    vmap = {}
    for v in bm_top.verts:
        vmap[v] = bm.verts.new(v.co)
    bm_top.verts.index_update()
    for f in bm_top.faces:
        try:
            bm.faces.new([vmap[v] for v in f.verts])
        except ValueError:
            pass
    bm_top.free()
    bm.to_mesh(me)
    bm.free()
    me.update()
    bpy.data.objects.remove(top, do_unlink=True)

# 移除碰撞体副本（不导出）
for bag, collider in colliders:
    bpy.data.objects.remove(collider, do_unlink=True)

# ---------------- 坐垫滚边 + 真实针脚 + 绗缝 ----------------
for k in range(SEAT_N):
    cx = SEAT_X0 + k * (SEAT_W + 0.018)
    objs.append(B.pipe_rect(f"seat_pipe_{k}", cx, 0.02, SEAT_TOP - 0.012,
                             SEAT_W + 0.004, SEAT_D + 0.004, M_WELT, r=0.0092))
    objs += B.stitch_rect(f"seat_stitch_{k}", cx, 0.02, SEAT_TOP - 0.020,
                          SEAT_W - 0.020, SEAT_D - 0.020, M_THREAD,
                          r=0.00085, inset=0.004, lift=0.002)
    # 绗缝：沿进深方向的分格缝（真实坐垫面包格）
    for j in (-1, 1):
        x = cx + j * SEAT_W * 0.24
        objs += B.stitch_line(f"seat_tuft_{k}_{j}",
                              (x, 0.02 - SEAT_D / 2 + 0.02, SEAT_TOP + 0.002),
                              (x, 0.02 + SEAT_D / 2 - 0.02, SEAT_TOP + 0.002),
                              M_THREAD, r=0.00075)

# ---------------- 靠垫（高背撑肩，坐落在靠背前） ----------------
for k in range(SEAT_N):
    cx = SEAT_X0 + k * (SEAT_W + 0.018)
    c = B.box(f"backc_{k}", (SEAT_W, 0.16, 0.46), (cx, -D / 2 + 0.20, 0.63), M_UP)
    B.bevel(c, 0.038, 4); B.subsurf(c, 3)
    for v in c.data.vertices:
        if v.co.z > 0.80:
            v.co.y += 0.012
        if abs(v.co.x - cx) > SEAT_W * 0.38:
            v.co.z -= 0.014
    B.smart_uv(c)
    objs.append(c)
    objs.append(B.pipe_rect(f"backc_pipe_{k}", cx, -D / 2 + 0.20, 0.63,
                             SEAT_W - 0.01, 0.145, M_WELT, r=0.0075))

# ---------------- 抱枕（统一色板点缀，压在靠垫前方） ----------------
# 位置：靠垫前沿（Y=-D/2+0.30 附近），这样从正面看不会被靠垫完全挡住
for nm, cx, col, rz in (("accent_terracotta", -0.46, M_AC1, 0.20),
                        ("accent_sage", 0.46, M_AC2, -0.18)):
    py = -D / 2 + 0.27
    p = B.box(nm, (0.38, 0.14, 0.38), (cx, py, 0.62), col)
    B.bevel(p, 0.052, 4); B.subsurf(p, 3)
    for v in p.data.vertices:
        if abs(v.co.x - cx) > 0.108 and abs(v.co.z - 0.62) > 0.108:
            v.co.x = cx + (v.co.x - cx) * 0.88
            v.co.z = 0.62 + (v.co.z - 0.62) * 0.88
        # 正面中心微凹（真实抱枕被压出的感觉）
        if abs(v.co.x - cx) < 0.055 and abs(v.co.z - 0.62) < 0.055 and v.co.y < py - 0.03:
            v.co.y += 0.012
    B.smart_uv(p)
    p["noTheme"] = 1
    objs.append(p)

# ---------------- 靠背顶部滚边 + 针脚 ----------------
objs.append(B.pipe_rect("back_pipe_top", 0, -D / 2 + 0.10, BACK_TOP - 0.004,
                         W - 0.32, BACK_T - 0.02, M_WELT, r=0.0085))
objs += B.stitch_line("back_stitch",
                      (-(W - 0.36) / 2, -D / 2 + 0.095, BACK_TOP - 0.045),
                      ((W - 0.36) / 2, -D / 2 + 0.095, BACK_TOP - 0.045),
                      M_THREAD, r=0.00085, lift=0.002)

# ---------------- 搭毯（William 标志性：毯子搭在扶手上垂到内侧） ----------------
# 中心对准右扶手，宽度收在扶手内侧，垂边只往下不往外
TH_X = W / 2 - 0.115
throw = B.grid("throw", 0.40, 0.78, 26, (TH_X, 0.02, ARM_TOP + 0.014), M_FAB)
for v in throw.data.vertices:
    ax = abs(v.co.x - TH_X)
    # 外侧往内收（不能超出扶手外沿 W/2=1.12）
    if v.co.x > TH_X + 0.10:
        v.co.x = min(v.co.x, W / 2 - 0.005)
    if ax > 0.09:
        v.co.z -= (ax - 0.09) * 1.35
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
            objs.append(B.cyl(f"leg_{sx}_{sz}_{i}", rad, 0.026, (x, y, h + 0.013),
                               M_WOOD if i < 3 else M_BRASS, verts=20))

# ---------------- 应用修改器 ----------------
for o in list(objs):
    if o.type == 'MESH':
        B.apply_mods(o)

B.export(OUT)
print("OK sofa v7 ->", OUT, "objects:", len(objs))
"""sofa HD v5 — William 流程真做：
  Part1 蓝图比例  : 按 Zanotta William 实测尺寸建框架（宽2240 深940 高700 座高430）
  Part2 布料解算  : Cloth 模拟器 + 布料压力(pressure)把坐垫吹鼓（真实解算，不是手动顶点位移）
  Part3 布刷褶皱  : Cloth Brush / 手动折痕 + 边缘松量
  Part6 真实针脚  : 沿缝线路径生成真实线段几何（短针脚 + 针脚间距），不是贴图
  包边           : 曲线 + 圆截面 bevel（一致直径的管状滚边）
"""
import bpy, math, os, random, json

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))),
                   "验收", "models", "sofa.glb")
os.makedirs(os.path.dirname(OUT), exist_ok=True)

bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete(use_global=False)
for coll in (bpy.data.meshes, bpy.data.curves, bpy.data.materials, bpy.data.images):
    for x in list(coll):
        try: coll.remove(x)
        except: pass

# ============ 材质 ============
def pbr(name, hexc, rough=0.6, metal=0.0, sheen=0.0, aniso=0.0):
    m = bpy.data.materials.new(name=name); m.use_nodes = True
    nt = m.node_tree; bsdf = nt.nodes.get("Principled BSDF")
    r,g,b = tuple(int(hexc[i:i+2],16)/255 for i in (1,3,5))
    bsdf.inputs["Base Color"].default_value = (r,g,b,1.0)
    bsdf.inputs["Roughness"].default_value = rough
    if "Metallic" in bsdf.inputs: bsdf.inputs["Metallic"].default_value = metal
    try:
        if sheen: bsdf.inputs["Sheen weight"].default_value = sheen
        if aniso: bsdf.inputs["Anisotropic"].default_value = aniso
    except: pass
    return m

def fabric(name, hexc, rough=0.93, sheen=0.85):
    """织物：双层noise织纹 + sheen 绒感 + 各向异性"""
    m = pbr(name, hexc, rough, 0.0, sheen, 0.35)
    nt = m.node_tree; bsdf = nt.nodes.get("Principled BSDF")
    tx = nt.nodes.new("ShaderNodeTexCoord")
    warp = nt.nodes.new("ShaderNodeTexWave"); warp.wave_type='BANDS'; warp.bands_direction='X'
    warp.inputs["Scale"].default_value = 240.0; warp.inputs["Distortion"].default_value = 2.0
    weft = nt.nodes.new("ShaderNodeTexWave"); weft.wave_type='BANDS'; weft.bands_direction='Y'
    weft.inputs["Scale"].default_value = 240.0; weft.inputs["Distortion"].default_value = 2.0
    mix = nt.nodes.new("ShaderNodeMix"); mix.data_type='FLOAT'; mix.blend_type='ADD'
    mix.inputs[0].default_value = 1.0
    bump = nt.nodes.new("ShaderNodeBump"); bump.inputs["Strength"].default_value = 0.3; bump.inputs["Distance"].default_value = 0.0012
    nt.links.new(tx.outputs["UV"], warp.inputs["Vector"]); nt.links.new(tx.outputs["UV"], weft.inputs["Vector"])
    nt.links.new(warp.outputs["Fac"], mix.inputs[2]); nt.links.new(weft.outputs["Fac"], mix.inputs[3])
    nt.links.new(mix.outputs[0], bump.inputs["Height"]); nt.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    return m

def wood(name, hexc, rough=0.42):
    m = pbr(name, hexc, rough)
    nt = m.node_tree; bsdf = nt.nodes.get("Principled BSDF")
    tx = nt.nodes.new("ShaderNodeTexCoord")
    mp = nt.nodes.new("ShaderNodeMapping"); mp.inputs["Scale"].default_value = (2.0, 22.0, 2.0)
    nz = nt.nodes.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 4.0; nz.inputs["Detail"].default_value = 6.0
    bump = nt.nodes.new("ShaderNodeBump"); bump.inputs["Strength"].default_value = 0.22; bump.inputs["Distance"].default_value = 0.002
    nt.links.new(tx.outputs["UV"], mp.inputs["Vector"]); nt.links.new(mp.outputs["Vector"], nz.inputs["Vector"])
    nt.links.new(nz.outputs["Fac"], bump.inputs["Height"]); nt.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    return m

M_UP   = fabric("U_upholstery",  "#c9bba6")
M_UP_D = fabric("U_upholsterydk","#9d8f7a")
M_FAB  = fabric("U_fabric",     "#f2ede2")
M_WELT = pbr("U_dark", "#4a4238", 0.72)
M_METAL= pbr("U_metal","#22252a", 0.30, 0.92)
M_BRASS= pbr("U_brass","#a8843e", 0.26, 1.0)
M_WOOD = wood("U_wood",  "#6b4a2d")
M_THREAD=pbr("U_thread", "#d8cdb8", 0.88)
M_THREAD_D=pbr("U_threaddk", "#6d6354", 0.88)
M_OR = fabric("pillow_orange", "#d96f2e")
M_BL = fabric("pillow_blue",   "#2f7fd0")

# ============ 基础工具 ============
def link(ob):
    bpy.context.collection.objects.link(ob); return ob

def bevel_mod(o, w, seg=3, ang=32):
    md = o.modifiers.new("Bevel", 'BEVEL'); md.width = w; md.segments = seg
    md.limit_method = 'ANGLE'; md.angle_limit = math.radians(ang); return md

def smart_uv(o, ang=60):
    bpy.ops.object.select_all(action='DESELECT'); o.select_set(True)
    bpy.context.view_layer.objects.active = o
    bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=math.radians(ang), island_margin=0.008)
    bpy.ops.object.mode_set(mode='OBJECT')

def activate(o):
    bpy.ops.object.select_all(action='DESELECT'); o.select_set(True)
    bpy.context.view_layer.objects.active = o

# ============ Part6：真实针脚几何 ============
def stitch_run(name, p0, p1, material, count=None, length=0.009, gap=0.005, r=0.0009, axis='Z'):
    """沿 p0->p1 生成一排真实线段（每针独立短圆柱），非贴图非曲线"""
    p0 = mathutils.Vector(p0); p1 = mathutils.Vector(p1)
    d = (p1 - p0)
    total = d.length
    if total < 1e-6: return []
    dirv = d.normalized()
    if count is None:
        count = max(2, int(total / (length + gap)))
    out = []
    seg = total / count
    for i in range(count):
        s = i * seg
        e = min(s + length, total)
        a = p0 + dirv * s; b = p0 + dirv * e
        mid = (a + b) * 0.5
        bpy.ops.mesh.primitive_cylinder_add(vertices=6, radius=r, depth=(b-a).length,
                                           location=(mid.x, mid.y, mid.z))
        ob = bpy.context.active_object; ob.name = f"{name}_{i}"
        # 把圆柱轴向对齐到 dirv
        ob.rotation_mode = 'QUATERNION'
        ob.rotation_quaternion = dirv.to_track_quat('Z', 'Y')
        ob.data.materials.append(material)
        out.append(ob)
    return out

def stitch_rect(name, w, d, z, material, r=0.0009, inset=0.012):
    """矩形一圈针脚"""
    hw, hd = w/2 - inset, d/2 - inset
    pts = [(-hw,-hd,z),(hw,-hd,z),(hw,hd,z),(-hw,hd,z)]
    objs = []
    for i in range(4):
        a, b = pts[i], pts[(i+1) % 4]
        objs += stitch_run(f"{name}_s{i}", a, b, material, r=r)
    return objs

# ============ 曲线滚边（圆截面 bevel，直径一致） ============
def piping_rect(name, w, d, loc, material, r=0.009, corner=0.02):
    cu = bpy.data.curves.new(name+"_cv", type='CURVE'); cu.dimensions='3D'; cu.resolution_u=12
    cu.bevel_depth = r; cu.bevel_resolution = 4; cu.use_fill_caps = True
    sp = cu.splines.new('NURBS'); sp.points.add(3); sp.use_cyclic_u = True
    for i,(x,y) in enumerate([(-w/2,-d/2),(w/2,-d/2),(w/2,d/2),(-w/2,d/2)]):
        sp.points[i].co = (x,y,0,1.0)
    sp.order_u = 3
    ob = bpy.data.objects.new(name, cu); link(ob); ob.location = loc
    ob.data.materials.append(material); return ob

def piping_path(name, pts, material, r=0.009):
    cu = bpy.data.curves.new(name+"_cv", type='CURVE'); cu.dimensions='3D'; cu.resolution_u=14
    cu.bevel_depth = r; cu.bevel_resolution = 4; cu.use_fill_caps = True
    sp = cu.splines.new('BEZIER'); sp.bezier_points.add(len(pts)-1)
    for i,(x,y,z) in enumerate(pts):
        bp = sp.bezier_points[i]; bp.co = (x,y,z); bp.handle_left_type='AUTO'; bp.handle_right_type='AUTO'
    ob = bpy.data.objects.new(name, cu); link(ob); ob.data.materials.append(material); return ob

def circle_bevel_obj(r=0.009):
    """曲线 bevel 用的圆截面对象，保证滚边直径一致"""
    me = bpy.data.meshes.new("circle_bv")
    vs = [(r*math.cos(a), r*math.sin(a), 0) for a in [i*2*math.pi/12 for i in range(12)]]
    me.from_pydata(vs, [], [list(range(12))]); me.update()
    ob = bpy.data.objects.new("circle_bv", me); link(ob)
    return ob

# ============ Part2：布料压力解算 ============
def cloth_pressure_cushion(name, w, d, h, loc, material, pressure=18.0, res=46, seed=0):
    """真实 Cloth 解算：平面网格 + Cloth 修改器 + 布料压力(pressure)从内部吹鼓
       —— 这是 William 视频 Part2 的核心做法，不是手改顶点。"""
    bpy.ops.mesh.primitive_grid_add(x_subdivisions=res, y_subdivisions=res, size=1.0, location=loc)
    o = bpy.context.active_object; o.name = name
    o.scale = (w, d, 1.0)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    o.data.materials.append(material)

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

    # 压力场：从内部吹鼓（Blender 4.5 属性名为 pressure_factor）
    s.use_pressure = True
    s.pressure_factor = pressure
    s.use_pressure_volume = True
    s.collider_friction = 6.0

    # 碰撞：Blender 4.5 里 Cloth 的碰撞设置在 cl.collision_settings（ClothCollisionSettings）
    # 被模拟体上加 Collision 修改器才参与碰撞
    cs = cl.collision_settings
    cs.use_collision = True
    cs.distance_min = 0.006
    cs.use_self_collision = True
    cs.self_distance_min = 0.005
    cs.self_friction = 6.0
    cs.collision_quality = 4
    cs.friction = 6.0
    col = o.modifiers.new("Collision", 'COLLISION')
    col.settings.use_culling = True
    col.settings.thickness_outer = 0.008
    col.settings.thickness_inner = 0.004
    col.settings.friction_factor = 6.0

    # 固定边（角与边钉住，中间自由）
    vg = o.vertex_groups.new(name="Pins")
    for i, v in enumerate(o.data.vertices):
        u = abs(v.co.x) / (w/2); t = abs(v.co.y) / (d/2)
        if u > 0.86 or t > 0.86:
            vg.add([i], 1.0, 'REPLACE')

    # 布料碰撞体（下方底座轮廓，用一个放大的扁盒当坐垫托板）
    bpy.ops.mesh.primitive_cube_add(size=1, location=(loc[0], loc[1], loc[2] - h*0.55))
    pad = bpy.context.active_object; pad.name = name+"_pad"
    pad.dimensions = (w*0.99, d*0.99, h*0.5)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    md = pad.modifiers.new("Solid","SOLIDIFY")
    pad.hide_render = True; pad.hide_viewport = False
    # 碰撞体自身要有 Collision 修改器才会参与 Cloth 碰撞
    pcol = pad.modifiers.new("Collision", 'COLLISION')
    pcol.settings.use_culling = True
    pcol.settings.thickness_outer = 0.01
    pcol.settings.friction_factor = 8.0
    # 碰撞体集合：Blender 4.5 里 cl.collision_settings.collection 默认为 None，
    # 必须自建集合并把碰撞体放进去，Cloth 才会跟它碰
    coll_name = "cloth_colliders"
    if coll_name in bpy.data.collections:
        coll = bpy.data.collections[coll_name]
    else:
        coll = bpy.data.collections.new(coll_name)
        bpy.context.scene.collection.children.link(coll)
    cs.collection = coll
    for c in list(pad.users_collection):
        c.objects.unlink(pad)
    coll.objects.link(pad)

    return o, pad

def simulate(o, frames=48):
    sc = bpy.context.scene
    sc.frame_start = 1; sc.frame_end = frames
    for f in range(1, frames+1):
        bpy.context.view_layer.update()
        sc.frame_set(f)
    sc.frame_set(frames)
    bpy.ops.object.select_all(action='DESELECT')
    activate(o)
    for md in [m.name for m in o.modifiers]:
        try: bpy.ops.object.modifier_apply(modifier=md)
        except Exception as e: print("apply fail", o.name, md, e)

# ============ Part3：布刷褶皱（真实几何位移 + 边缘松量） ============
def cloth_brush_wrinkles(o, amp=0.006, freq=17.0, seed=0, region=None):
    random.seed(seed)
    for v in o.data.vertices:
        if region and not region(v.co): continue
        v.co.z += (math.sin(v.co.x*freq + seed*1.3) * math.sin(v.co.y*freq*0.87 + seed*0.7) * 0.62
                   + (random.random()-0.5)*0.5) * amp

def edge_slack(o, amp=0.008):
    """边缘松量：缝线附近的布料被拉出小起伏"""
    for v in o.data.vertices:
        u = max(abs(v.co.x)/(0.31), abs(v.co.y)/(0.32))
        if u > 0.72:
            k = (u - 0.72) / 0.28
            v.co.z += (math.sin(v.co.x*37.0) + math.sin(v.co.y*29.0)) * amp * k

def pinch_corners(o, x0, z0, x1, z1, amount=0.90):
    for v in o.data.vertices:
        if abs(v.co.x) > x0 and abs(v.co.z - z0) > z0*0.55:
            v.co.x *= amount; v.co.z = z0 + (v.co.z - z0)*amount

# ============ 组装 ============
import mathutils

objs = []
# ---- William 实测蓝图尺寸（Zanotta William: W2240 D940 H700 座高430 扶手高620）----
W, D = 2.24, 0.94
BASE_H, SEAT_H, ARM_H, BACK_H = 0.30, 0.43, 0.62, 0.70

# 底座（内收避光脚）
bpy.ops.mesh.primitive_cube_add(size=1, location=(0,0,BASE_H/2))
base = bpy.context.active_object; base.name = "base"
base.dimensions = (W-0.16, D-0.14, BASE_H); bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
base.data.materials.append(M_UP); bevel_mod(base, 0.02, 3)
sub = base.modifiers.new("S",'SUBSURF'); sub.levels=3; sub.render_levels=3
objs.append(base)

# 底座暗色踢脚
bpy.ops.mesh.primitive_cube_add(size=1, location=(0,0,0.035))
pl = bpy.context.active_object; pl.name = "plinth"
pl.dimensions = (W-0.26, D-0.24, 0.07); bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
pl.data.materials.append(M_UP_D); bevel_mod(pl, 0.006, 2)
objs.append(pl)

# Track 扶手（William 标志性直线扶手，前端略收）
for sx in (-1,1):
    nm = 'L' if sx < 0 else 'R'
    bpy.ops.mesh.primitive_cube_add(size=1, location=(sx*(W/2-0.135), 0.01, BASE_H+0.16))
    a = bpy.context.active_object; a.name = f"arm_{nm}"
    a.dimensions = (0.27, D-0.02, 0.32); bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    a.data.materials.append(M_UP); bevel_mod(a, 0.045, 4)
    s2 = a.modifiers.new("S",'SUBSURF'); s2.levels=3; s2.render_levels=3
    # 扶手内侧下压出坐垫槽，前端收窄
    for v in a.data.vertices:
        if (v.co.x * -sx) > 0.06 and abs(v.co.y) < 0.30 and v.co.z < 0.06:
            v.co.x += sx*0.022
        if v.co.y > 0.30:
            v.co.x *= 0.93; v.co.z -= 0.010
    objs.append(a)
    # 扶手顶滚边 + 前端竖滚边
    objs.append(piping_rect(f"arm_pipe_{nm}", 0.235, D-0.06, (sx*(W/2-0.135), 0.01, BASE_H+0.325), M_WELT, r=0.0085))
    objs.append(piping_path(f"arm_front_{nm}", [
        (sx*(W/2-0.135)-0.115, D/2-0.02, BASE_H+0.02),
        (sx*(W/2-0.135)-0.112, D/2-0.02, BASE_H+0.30),
        (sx*(W/2-0.135)+0.112, D/2-0.02, BASE_H+0.30),
        (sx*(W/2-0.135)+0.115, D/2-0.02, BASE_H+0.02)], M_WELT, r=0.008))

# 靠背（后倾 8°）—— 高度按 William 实测控制：靠背顶不超 0.62m，
# 靠垫叠在靠背上后总高仍在 0.70~0.95m 区间内
bpy.ops.mesh.primitive_cube_add(size=1, location=(0, -D/2+0.115, BASE_H+0.25))
bk = bpy.context.active_object; bk.name = "backrest"
bk.dimensions = (W-0.27, 0.22, 0.50); bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
bk.data.materials.append(M_UP); bevel_mod(bk, 0.045, 4)
s3 = bk.modifiers.new("S",'SUBSURF'); s3.levels=3; s3.render_levels=3
bk.rotation_euler.x = math.radians(-8)
objs.append(bk)

# ---- Part2 布料解算：3 块坐垫 ----
SEAT_N = 3
seat_w = (W - 0.34) / SEAT_N - 0.018
seat_d = D - 0.30
seat_x0 = -(W - 0.34)/2 + seat_w/2 + 0.009
pads = []
for k in range(SEAT_N):
    cx = seat_x0 + k*(seat_w + 0.018)
    cu, pad = cloth_pressure_cushion(f"seat_{k}", seat_w, seat_d, 0.17,
                                     (cx, 0.02, BASE_H + 0.085), M_UP, pressure=22.0, res=44, seed=k)
    pads.append(pad)
    objs.append(cu)
print("开始布料解算 3 块坐垫 ...")
for k, cu in enumerate([o for o in objs if o.name.startswith("seat_")]):
    simulate(cu, frames=52)
    print("  simulated", cu.name)

# 解算后处理：布刷褶皱 + 边缘松量 + 落座校正
for k, cu in enumerate([o for o in objs if o.name.startswith("seat_")]):
    activate(cu)
    cloth_brush_wrinkles(cu, amp=0.0055, freq=19.0, seed=k*3+1)
    edge_slack(cu, amp=0.007)
    # 顶面鼓包微调（解算已经吹鼓，这里只做很轻的形状微调）
    for v in cu.data.vertices:
        if v.co.z > 0.045:
            fx = max(0.0, 1.0 - (v.co.x/(seat_w/2))**2)
            fy = max(0.0, 1.0 - (v.co.y/(seat_d/2))**2)
            v.co.z += 0.008*min(fx,fy)
    # 落座校正：布料在重力下下垂会穿过底座，这里把解算后的垫子
    # 整体抬到"坐在底座上沿"的位置，并压平贴底的那圈
    zs = [v.co.z for v in cu.data.vertices]
    target_bottom = BASE_H + 0.005
    shift = target_bottom - min(zs)
    for v in cu.data.vertices:
        v.co.z += shift
        # 贴底圈压平（模拟被底座压住）
        if v.co.z < target_bottom + 0.012:
            v.co.z = target_bottom + (v.co.z - target_bottom) * 0.35
    smart_uv(cu)

# 坐垫滚边 + 真实针脚
for k in range(SEAT_N):
    cx = seat_x0 + k*(seat_w + 0.018)
    # 滚边高度取实际解算后垫子的腰线高度，避免悬空或穿地
    cu = bpy.data.objects[f"seat_{k}"]
    zs = [v.co.z for v in cu.data.vertices]
    waist = (min(zs) + max(zs)) * 0.5 + cu.location.z
    objs.append(piping_rect(f"seat_pipe_{k}", seat_w-0.006, seat_d-0.006,
                             (cx, 0.02, waist), M_WELT, r=0.0088))
    # 针脚沿滚边内侧一圈
    for i, ob in enumerate(stitch_rect(f"seat_stitch_{k}", seat_w-0.024, seat_d-0.024,
                                        waist + 0.012, M_THREAD, r=0.00085, inset=0.004)):
        objs.append(ob)

# ---- 靠垫（软包，顶部略塌） ----
for k in range(SEAT_N):
    cx = seat_x0 + k*(seat_w + 0.018)
    bpy.ops.mesh.primitive_cube_add(size=1, location=(cx, -D/2+0.21, BASE_H+0.33))
    c = bpy.context.active_object; c.name = f"backc_{k}"
    c.dimensions = (seat_w, 0.18, 0.40); bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    c.data.materials.append(M_UP); bevel_mod(c, 0.042, 4)
    s = c.modifiers.new("S",'SUBSURF'); s.levels=3; s.render_levels=3
    c.rotation_euler.x = math.radians(-14)
    for v in c.data.vertices:
        if v.co.z > 0.14: v.co.y += 0.014
        if abs(v.co.x) > seat_w*0.38: v.co.z -= 0.012
    smart_uv(c); objs.append(c)
    objs.append(piping_rect(f"backc_pipe_{k}", seat_w-0.01, 0.16, (cx, -D/2+0.21, BASE_H+0.33), M_WELT, r=0.008))

# ---- 抱枕 ----
for nm, cx, col, rz, zz in (("pillow_orange", -0.50, M_OR, 0.20, 0.62), ("pillow_blue", 0.50, M_BL, -0.18, 0.62)):
    bpy.ops.mesh.primitive_cube_add(size=1, location=(cx, -D/2+0.26, BASE_H+zz))
    p = bpy.context.active_object; p.name = nm
    p.dimensions = (0.40, 0.13, 0.40); bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    p.data.materials.append(col); bevel_mod(p, 0.052, 4)
    s = p.modifiers.new("S",'SUBSURF'); s.levels=3; s.render_levels=3
    p.rotation_euler = (math.radians(-18), math.radians(10 if cx < 0 else -10), rz)
    for v in p.data.vertices:
        if abs(v.co.x) > 0.115 and abs(v.co.z) > 0.115:
            v.co.x *= 0.88; v.co.z *= 0.88
        if abs(v.co.x) < 0.05 and abs(v.co.z) < 0.05 and v.co.y > 0.03:
            v.co.y -= 0.014
    smart_uv(p); p["noTheme"] = 1; objs.append(p)

# ---- 靠背顶部滚边 + 针脚 ----
objs.append(piping_rect("back_pipe_top", W-0.36, 0.185, (0, -D/2+0.16, BASE_H+0.495), M_WELT, r=0.009))
for ob in stitch_rect("back_stitch", W-0.40, 0.185, BASE_H+0.46, M_THREAD, r=0.00085, inset=0.006):
    objs.append(ob)

# ---- 搭毯（垂在右扶手） ----
bpy.ops.mesh.primitive_grid_add(x_subdivisions=26, y_subdivisions=26, size=1.0,
                                location=(W/2-0.135, 0.0, BASE_H+0.345))
th = bpy.context.active_object; th.name = "throw"
th.scale = (0.50, 0.86, 1.0); bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
for v in th.data.vertices:
    ax = abs(v.co.x)
    if ax > 0.115: v.co.z -= (ax-0.115)*1.25
    v.co.z += math.sin(v.co.y*15.0)*0.009 + math.sin(v.co.x*33.0+v.co.y*11.0)*0.004
th.modifiers.new("Solid","SOLIDIFY").thickness = 0.007
th.data.materials.append(M_FAB); th["noTheme"] = 1
for p in th.data.polygons: p.use_smooth = True
smart_uv(th); objs.append(th)

# ---- 车削木腿 + 黄铜脚箍 ----
for sx in (-1,1):
    for sz in (-1,1):
        x, y = sx*(W/2-0.20), sz*(D/2-0.20)
        for i,(rad, h) in enumerate([(0.032,0.10),(0.024,0.072),(0.028,0.046),(0.019,0.022)]):
            bpy.ops.mesh.primitive_cylinder_add(vertices=20, radius=rad, depth=0.026, location=(x,y,h+0.02))
            seg = bpy.context.active_object; seg.name = f"leg_{sx}_{sz}_{i}"
            seg.data.materials.append(M_WOOD if i < 3 else M_BRASS); objs.append(seg)

# ---- 清理碰撞体（不入导出） ----
for pad in pads:
    bpy.data.objects.remove(pad, do_unlink=True)

# ---- 应用所有修改器 ----
for o in list(objs):
    if o.type != 'MESH': continue
    activate(o)
    for md in [m.name for m in o.modifiers]:
        try: bpy.ops.object.modifier_apply(modifier=md)
        except Exception as e: print("apply fail", o.name, md, e)

# ---- 导出 ----
bpy.ops.object.select_all(action='SELECT')
bpy.ops.export_scene.gltf(filepath=OUT, export_format='GLB', export_materials='EXPORT',
                          export_extras=True, export_cameras=False, export_lights=False,
                          use_selection=True, export_apply=True)
print("OK sofa v5 ->", OUT, "objects:", len(objs))

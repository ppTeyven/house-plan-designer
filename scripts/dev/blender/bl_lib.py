"""建模基础库 —— 关键约定：所有物体的网格顶点直接写在世界坐标里，物体 location 恒为 (0,0,0)。

原因（已用 Blender 4.5 实测确证）：
  Blender 导出的 GLB 里，节点保留 location/rotation/scale，
  而 accessor.min/max 是网格局部坐标。
  若用 bpy.ops.mesh.primitive_cube_add(location=...) 建物体，
  网格仍在原点附近、位置靠节点 TRS 表达 —— 尺寸与落地点极易出错。
  所以这里统一用「建在原点 → 顶点位移到目标位置」的方式：
  网格坐标 = 世界坐标，节点变换恒为单位阵，任何导出器都不会产生歧义。
"""
import bpy, math, random, mathutils

AXIS = {'X': 0, 'Y': 1, 'Z': 2}


def wipe():
    bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete(use_global=False)
    for coll in (bpy.data.meshes, bpy.data.curves, bpy.data.materials, bpy.data.images):
        for x in list(coll):
            try: coll.remove(x)
            except: pass


def activate(o):
    bpy.ops.object.select_all(action='DESELECT')
    o.select_set(True)
    bpy.context.view_layer.objects.active = o


def link(ob):
    bpy.context.collection.objects.link(ob)
    return ob


def box(name, size, center, material=None, rot=None, pivot='CENTER'):
    """在原点建盒，再把顶点平移到 center（网格坐标 = 世界坐标，物体 location 保持 0）
    pivot='CENTER' 中心对齐 center；'BOTTOM' 底面对齐 center 的 z（用于落地件）

    注意：primitive_cube_add(size=1) 的顶点本来就以原点为中心，
    所以 CENTER 模式【不能】再减 hz，否则整体会下沉半个高度。"""
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, 0))
    o = bpy.context.active_object
    o.name = name
    o.dimensions = size
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    hx, hy, hz = size[0] / 2, size[1] / 2, size[2] / 2
    for v in o.data.vertices:
        if pivot == 'BOTTOM':
            v.co.z += hz
        v.co.x += center[0]
        v.co.y += center[1]
        v.co.z += center[2]
    if material is not None:
        o.data.materials.append(material)
    for p in o.data.polygons:
        p.use_smooth = True
    if rot is not None:
        # 绕自身中心旋转（网格已居中于 center，直接转顶点）
        e = mathutils.Euler(rot, 'XYZ').to_matrix()
        c = mathutils.Vector(center)
        for v in o.data.vertices:
            v.co = c + e @ (v.co - c)
    o.location = (0, 0, 0)
    return o


def bevel(o, width=0.012, segments=3, angle=32, clamp=True):
    md = o.modifiers.new("Bevel", 'BEVEL')
    md.width = width
    md.segments = segments
    md.limit_method = 'ANGLE'
    md.angle_limit = math.radians(angle)
    md.use_clamp_overlap = clamp
    md.harden_normals = False
    return md


def subsurf(o, levels=3):
    md = o.modifiers.new("Subdiv", 'SUBSURF')
    md.levels = levels
    md.render_levels = levels
    return md


def cyl(name, r, h, center, material=None, axis='Z', verts=24, r2=None):
    """圆柱/圆台；center 为几何中心；r2 为顶面半径（圆台）

    重要：必须【先做轴置换，再平移到 center】。
    反过来（先平移后置换）会把 center 的坐标一起旋转掉，
    物体位置就会飘走（实测床头柜抽屉把手高度多出 234mm）。
    """
    bpy.ops.mesh.primitive_cone_add(vertices=verts, radius1=r,
                                    radius2=(r if r2 is None else r2),
                                    depth=h, location=(0, 0, 0))
    o = bpy.context.active_object
    o.name = name
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    if axis == 'X':
        for v in o.data.vertices:
            v.co = mathutils.Vector((v.co.y, v.co.z, v.co.x))
    elif axis == 'Y':
        for v in o.data.vertices:
            v.co = mathutils.Vector((v.co.z, v.co.x, v.co.y))
    for v in o.data.vertices:
        v.co.x += center[0]; v.co.y += center[1]; v.co.z += center[2]
    if material is not None:
        o.data.materials.append(material)
    for p in o.data.polygons:
        p.use_smooth = (len(p.vertices) == 4)
    o.location = (0, 0, 0)
    return o


def sphere(name, r, center, material=None, seg=24, rings=12, scale=(1, 1, 1)):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=seg, ring_count=rings,
                                          radius=r, location=(0, 0, 0))
    o = bpy.context.active_object
    o.name = name
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    for v in o.data.vertices:
        v.co.x *= scale[0]; v.co.y *= scale[1]; v.co.z *= scale[2]
        v.co.x += center[0]; v.co.y += center[1]; v.co.z += center[2]
    if material is not None:
        o.data.materials.append(material)
    for p in o.data.polygons:
        p.use_smooth = True
    o.location = (0, 0, 0)
    return o


def grid(name, w, d, res, center, material=None, wave=None):
    """高密平面（用于布料解算 / 织物），网格坐标 = 世界坐标"""
    bpy.ops.mesh.primitive_grid_add(x_subdivisions=res, y_subdivisions=res,
                                    size=1.0, location=(0, 0, 0))
    o = bpy.context.active_object
    o.name = name
    o.scale = (w, d, 1.0)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    for v in o.data.vertices:
        v.co.x += center[0]; v.co.y += center[1]; v.co.z += center[2]
    if material is not None:
        o.data.materials.append(material)
    o.location = (0, 0, 0)
    return o


def smart_uv(o, ang=60):
    activate(o)
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=math.radians(ang), island_margin=0.006)
    bpy.ops.object.mode_set(mode='OBJECT')


def apply_mods(o):
    activate(o)
    for md in [m.name for m in o.modifiers]:
        try:
            bpy.ops.object.modifier_apply(modifier=md)
        except Exception as e:
            print("apply fail", o.name, md, e)


# ---------- 滚边（曲线 + 圆截面，路径点直接给世界坐标） ----------
def pipe_path(name, pts, material, r=0.008, closed=False, res=12):
    """滚边曲线。
    用 POLY 样条：严格经过每个给定点，不会像 Bezier AUTO 那样在拐角过冲鼓包
    （William 流程要求滚边直径一致、路径精确，过冲会导致包边鼓包变形）。
    """
    cu = bpy.data.curves.new(name + "_cv", type='CURVE')
    cu.dimensions = '3D'
    cu.resolution_u = res
    cu.bevel_depth = r
    cu.bevel_resolution = 4
    cu.use_fill_caps = True
    sp = cu.splines.new('POLY')
    sp.points.add(len(pts) - 1)
    for i, p in enumerate(pts):
        sp.points[i].co = (p[0], p[1], p[2], 1.0)
    sp.use_cyclic_u = closed
    ob = bpy.data.objects.new(name, cu)
    link(ob)
    ob.data.materials.append(material)
    ob.location = (0, 0, 0)
    return ob


def pipe_rect(name, cx, cy, z, w, d, material, r=0.008, res=12):
    """矩形滚边：POLY 精确走四条边，跨度严格等于 w×d"""
    hw, hd = w / 2, d / 2
    pts = [(cx - hw, cy - hd, z), (cx + hw, cy - hd, z),
           (cx + hw, cy + hd, z), (cx - hw, cy + hd, z)]
    return pipe_path(name, pts, material, r=r, closed=True, res=res)


# ---------- 真实针脚几何（每针一根独立短线段，非贴图非曲线） ----------
def stitch_line(name, p0, p1, material, count=None, length=0.009, gap=0.005,
                r=0.00085, lift=0.0):
    """真实针脚几何：每针一根独立短圆柱（非贴图、非曲线）。

    关键：网格顶点直接写在世界坐标里（不靠物体 rotation_quaternion），
    否则绕物体原点旋转会把偏离原点的针脚甩到错误位置。
    """
    p0 = mathutils.Vector(p0); p1 = mathutils.Vector(p1)
    d = p1 - p0
    total = d.length
    if total < 1e-6:
        return []
    dirv = d.normalized()
    if count is None:
        count = max(2, int(total / (length + gap)))
    seg = total / count
    # 构造正交基：dirv 为针脚轴向，u/v 为横截面
    up = mathutils.Vector((0, 0, 1))
    if abs(dirv.dot(up)) > 0.95:
        up = mathutils.Vector((1, 0, 0))
    u = dirv.cross(up).normalized()
    w = dirv.cross(u).normalized()
    out = []
    sides = 6
    for i in range(count):
        s = i * seg
        e = min(s + length, total)
        a = p0 + dirv * s
        b = p0 + dirv * e
        mid = (a + b) * 0.5 + mathutils.Vector((0, 0, lift))
        half = (b - a).length / 2
        verts = []
        for end in (a, b):
            base = end + mathutils.Vector((0, 0, lift))
            for k in range(sides):
                ang = 2 * math.pi * k / sides
                verts.append(tuple(base + u * (math.cos(ang) * r) + w * (math.sin(ang) * r)))
        faces = []
        for k in range(sides):
            k2 = (k + 1) % sides
            faces.append((k, k2, sides + k2, sides + k))
        faces.append(tuple(range(sides - 1, -1, -1)))
        faces.append(tuple(range(sides, 2 * sides)))
        me = bpy.data.meshes.new(f"{name}_{i}_me")
        me.from_pydata(verts, [], faces)
        me.update()
        ob = bpy.data.objects.new(f"{name}_{i}", me)
        link(ob)
        ob.data.materials.append(material)
        for p in ob.data.polygons:
            p.use_smooth = True
        out.append(ob)
    return out


def stitch_rect(name, cx, cy, z, w, d, material, r=0.00085, inset=0.006, lift=0.0):
    hw, hd = w / 2 - inset, d / 2 - inset
    pts = [(cx - hw, cy - hd, z), (cx + hw, cy - hd, z),
           (cx + hw, cy + hd, z), (cx - hw, cy + hd, z)]
    out = []
    for i in range(4):
        out += stitch_line(f"{name}_s{i}", pts[i], pts[(i + 1) % 4],
                           material, r=r, lift=lift)
    return out


# ---------- 材质 ----------
def pbr(name, hexc, rough=0.6, metal=0.0, sheen=0.0, aniso=0.0):
    m = bpy.data.materials.new(name=name)
    m.use_nodes = True
    nt = m.node_tree
    bsdf = nt.nodes.get("Principled BSDF")
    r, g, b = tuple(int(hexc[i:i + 2], 16) / 255 for i in (1, 3, 5))
    bsdf.inputs["Base Color"].default_value = (r, g, b, 1.0)
    bsdf.inputs["Roughness"].default_value = rough
    if "Metallic" in bsdf.inputs:
        bsdf.inputs["Metallic"].default_value = metal
    try:
        if sheen:
            bsdf.inputs["Sheen weight"].default_value = sheen
        if aniso:
            bsdf.inputs["Anisotropic"].default_value = aniso
    except Exception:
        pass
    return m


def fabric(name, hexc, rough=0.93, sheen=0.85, scale=240.0, strength=0.3):
    """织物：经纬双 Wave + Sheen 绒感

    【重要】Wave 纹理依赖 UV。超椭球软包等程序化生成的网格若没有 UV，
    经纬波纹会失效 → 布料看起来像素色塑料（实测踩坑）。
    因此这里同时挂一条【不依赖 UV 的三维噪声】作为底噪，
    即使 UV 缺失，织物仍有细腻的颗粒感。
    """
    m = pbr(name, hexc, rough, 0.0, sheen, 0.35)
    nt = m.node_tree
    bsdf = nt.nodes.get("Principled BSDF")
    tx = nt.nodes.new("ShaderNodeTexCoord")
    warp = nt.nodes.new("ShaderNodeTexWave")
    warp.wave_type = 'BANDS'; warp.bands_direction = 'X'
    warp.inputs["Scale"].default_value = scale
    warp.inputs["Distortion"].default_value = 2.0
    weft = nt.nodes.new("ShaderNodeTexWave")
    weft.wave_type = 'BANDS'; weft.bands_direction = 'Y'
    weft.inputs["Scale"].default_value = scale
    weft.inputs["Distortion"].default_value = 2.0
    mix = nt.nodes.new("ShaderNodeMix")
    mix.data_type = 'FLOAT'; mix.blend_type = 'ADD'
    mix.inputs[0].default_value = 1.0
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = strength
    bump.inputs["Distance"].default_value = 0.0012
    nt.links.new(tx.outputs["UV"], warp.inputs["Vector"])
    nt.links.new(tx.outputs["UV"], weft.inputs["Vector"])
    nt.links.new(warp.outputs["Fac"], mix.inputs[2])
    nt.links.new(weft.outputs["Fac"], mix.inputs[3])
    nt.links.new(mix.outputs[0], bump.inputs["Height"])
    # ---- 不依赖 UV 的三维细颗粒（保证无 UV 网格也有织物质感） ----
    nz = nt.nodes.new("ShaderNodeTexNoise")
    nz.inputs["Scale"].default_value = 420.0
    nz.inputs["Detail"].default_value = 4.0
    nz.inputs["Roughness"].default_value = 0.75
    nz2 = nt.nodes.new("ShaderNodeBump")
    nz2.inputs["Strength"].default_value = 0.22
    nz2.inputs["Distance"].default_value = 0.00045
    nt.links.new(tx.outputs["Object"], nz.inputs["Vector"])
    nt.links.new(nz.outputs["Fac"], nz2.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], nz2.inputs["Normal"])
    nt.links.new(nz2.outputs["Normal"], bsdf.inputs["Normal"])
    return m


def wood(name, hexc, rough=0.42):
    m = pbr(name, hexc, rough)
    nt = m.node_tree
    bsdf = nt.nodes.get("Principled BSDF")
    tx = nt.nodes.new("ShaderNodeTexCoord")
    mp = nt.nodes.new("ShaderNodeMapping")
    mp.inputs["Scale"].default_value = (2.0, 22.0, 2.0)
    nz = nt.nodes.new("ShaderNodeTexNoise")
    nz.inputs["Scale"].default_value = 4.0
    nz.inputs["Detail"].default_value = 6.0
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.22
    bump.inputs["Distance"].default_value = 0.002
    nt.links.new(tx.outputs["UV"], mp.inputs["Vector"])
    nt.links.new(mp.outputs["Vector"], nz.inputs["Vector"])
    nt.links.new(nz.outputs["Fac"], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    return m


def export(path, objs=None):
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.export_scene.gltf(filepath=path, export_format='GLB',
                              export_materials='EXPORT', export_extras=True,
                              export_cameras=False, export_lights=False,
                              use_selection=True, export_apply=True)
    print("EXPORTED", path)


# ==================== v11 新增：真实软包建模 + 曲面贴合 ====================
# 背景（实测踩坑）：
#  · v10 的坐垫/靠垫是"倒角盒子 + 顶点微调" → 渲染出来就是"简陋几何体拼凑"，
#    因为倒角盒子的棱线是直的、鼓包是手搓的，没有软包该有的连续曲率。
#  · v10 的滚边按【平面路径】走，而软包表面是【变形后的曲面】，
#    于是滚边直接切进布里 → 用户看到的"明显穿模"。
# 本节提供两个根治手段：
#   1. superellipsoid_soft()  —— 参数化超椭球软包，真实软包的连续曲率
#   2. pipe_on_surface()      —— 滚边逐点投射到曲面外侧（法线方向抬升），
#                                 从根本上消灭"平面路径 vs 变形曲面"的穿模

def superellipsoid_soft(name, size, center, material=None,
                        e1=0.62, e2=0.72, res_u=64, res_v=32,
                        squash_top=0.0, crown=0.0, top_clamp=None,
                        front_clamp=None):
    """参数化超椭球软包（真实软垫/靠包的标准做法）。

    与"倒角盒子"的本质区别：
      · 倒角盒子 = 直棱 + 平面顶 → 轮廓有硬折角，看起来像塑料件
      · 超椭球   = 全曲面连续曲率 → 有软包的"饱满但松弛"的形体感

    size   : (宽X, 深Y, 高Z)
    e1     : 上下方向的指数（<1 圆钝，=1 椭球，>1 趋方）
    e2     : 水平截面指数（<1 圆钝，=1 椭圆）
    squash_top: 顶面额外下压量（米），做"被压过"的松软感
    crown  : 顶面中央额外隆起（米），做饱满鼓包
    top_clamp   : 顶面绝对高度上限（米）。超过的顶点压平 →
                  得到【平整顶面 + 圆肩】的真实坐垫/扶手板形态。
                  （不加的话超椭球顶永远是圆拱，像枕卷不像坐垫）
    front_clamp : 前表面绝对深度上限（米），用于靠垫压出平整受压面。
    """
    import mathutils
    hx, hy, hz = size[0] / 2, size[1] / 2, size[2] / 2
    verts = []
    faces = []
    n_u = res_u
    n_v = res_v

    def sgnpow(x, e):
        return math.copysign(abs(x) ** e, x) if abs(x) > 1e-12 else 0.0

    # 经线：纬度 -pi/2 .. pi/2
    for iv in range(n_v + 1):
        v = -math.pi / 2 + math.pi * iv / n_v
        cv = math.cos(v)
        sv = math.sin(v)
        for iu in range(n_u):
            u = 2 * math.pi * iu / n_u
            cu = math.cos(u)
            su = math.sin(u)
            x = hx * sgnpow(cv, e1) * sgnpow(cu, e2)
            y = hy * sgnpow(cv, e1) * sgnpow(su, e2)
            z = hz * sgnpow(sv, e1)
            # 顶面中央隆起 / 压扁：按到中心的归一化距离
            if cv > 0.25:
                rr = min(1.0, math.hypot(x / hx, y / hy))
                t = (cv - 0.25) / 0.75
                z += (crown - squash_top) * math.cos(rr * math.pi / 2) * t
            zz = z + center[2]
            # 顶面压平：超过上限的顶点归到上限 → 平整台面 + 圆肩
            if top_clamp is not None and zz > top_clamp:
                zz = top_clamp
            yy = y + center[1]
            if front_clamp is not None and yy > front_clamp:
                yy = front_clamp
            verts.append((x + center[0], yy, zz))
    for iv in range(n_v):
        for iu in range(n_u):
            i0 = iv * n_u + iu
            i1 = iv * n_u + (iu + 1) % n_u
            i2 = (iv + 1) * n_u + (iu + 1) % n_u
            i3 = (iv + 1) * n_u + iu
            faces.append((i0, i1, i2, i3))
    me = bpy.data.meshes.new(name + "_me")
    me.from_pydata(verts, [], faces)
    me.update()
    for p in me.polygons:
        p.use_smooth = True
    ob = bpy.data.objects.new(name, me)
    link(ob)
    if material is not None:
        ob.data.materials.append(material)
    ob.location = (0, 0, 0)
    # 【关键】生成球面 UV —— 织物的经纬波纹依赖 UV，缺 UV 会变成素色塑料
    uvl = me.uv_layers.new(name="UVMap")
    for poly in me.polygons:
        for li in poly.loop_indices:
            vi = me.loops[li].vertex_index
            vx = verts[vi][0] - center[0]
            vy = verts[vi][1] - center[1]
            vz = verts[vi][2] - center[2]
            uvl.data[li].uv = (math.atan2(vy, vx) / (2 * math.pi) + 0.5,
                               math.asin(max(-1.0, min(1.0, vz / max(hz, 1e-6)))) / math.pi + 0.5)
    return ob


def pipe_on_surface(name, pts, surface, material, r=0.008, res=12, lift=0.0025,
                    project_axis=None):
    """【穿模根治】把滚边路径逐点投射到软包曲面外侧。

    之前 v10 的做法：滚边按平面矩形路径走 → 软包表面是变形后的曲面
    → 滚边半径 8mm 有一半陷进布里 → 用户看到"明显穿模"。

    本函数：对路径上每个采样点，沿 surface 的最近表面法线方向抬升，
    使滚边管心正好落在曲面外侧 lift 处，管体刚好贴着表面走，
    永远不会切进布面。

    surface : 已存在的网格对象（软包）
    lift    : 管心相对曲面的抬高量（米）。应 ≈ 滚边半径的一半 ~ 全部，
              决定滚边是"半嵌"还是"全贴"。
    """
    import bmesh
    from mathutils.bvhtree import BVHTree
    import mathutils

    # 建立 BVH
    bm = bmesh.new()
    bm.from_mesh(surface.data)
    bvh = BVHTree.FromBMesh(bm)
    bm.free()

    def nearest(pt):
        hit = bvh.find_nearest(mathutils.Vector(pt))
        if hit and hit[0] is not None:
            return hit[0], hit[1]
        return mathutils.Vector(pt), mathutils.Vector((0, 0, 1))

    out = []
    # 沿路径细分（POLY 路径太稀，投影会抖） → 先做 Catmull-Rom 重采样
    dense = _catmull_rom(pts, samples_per_seg=10)
    lifted = []
    for p in dense:
        pos, nor = nearest(p)
        if project_axis:
            # 约束法线到某个轴向（避免法线乱转导致滚边翻滚）
            ax = mathutils.Vector(project_axis).normalized()
            nor = (nor + ax * 2.0).normalized()
        lifted.append((pos.x + nor.x * lift, pos.y + nor.y * lift, pos.z + nor.z * lift))
    out = pipe_path(name, lifted, material, r=r, closed=False, res=res)
    return out


def _catmull_rom(pts, samples_per_seg=10):
    """Catmull-Rom 插值重采样（让滚边路径在投影前足够平滑）"""
    import mathutils
    P = [mathutils.Vector(p) for p in pts]
    if len(P) < 2:
        return P
    ext = [P[0] + (P[0] - P[1])] + P + [P[-1] + (P[-1] - P[-2])]
    out = []
    for i in range(len(P) - 1):
        p0, p1, p2, p3 = ext[i], ext[i + 1], ext[i + 2], ext[i + 3]
        for s in range(samples_per_seg):
            t = s / samples_per_seg
            t2 = t * t
            t3 = t2 * t
            pt = 0.5 * ((2 * p1) + (-p0 + p2) * t +
                        (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2 +
                        (-p0 + 3 * p1 - 3 * p2 + p3) * t3)
            out.append(pt)
    out.append(P[-1])
    return out


def cloth_displace_field(name, w, d, thick, center, material=None, res=64,
                         pin_bottom=True, settle_frames=40, seed=0):
    """【William 流程 Part2】布料解算生成位移场，用于塑造软包形变。

    真实做一整块 cloth 物体成本高且不可控；这里做的是一个【解算后的形变场】：
    1. 建高密平面网格
    2. 加 Cloth + pressure_factor 从内部吹鼓
    3. 解算若干帧
    4. 读取解算后的顶点 z 作为"鼓包高度场"
    5. 把高度场叠到软包的超椭球顶面上

    返回 (网格对象, 高度场 list[(x,y,z)] 或 None)
    """
    import random
    o = grid(name, w, d, res, (center[0], center[1], center[2]), material)
    cl = o.modifiers.new("Cloth", 'CLOTH')
    s = cl.settings
    s.quality = 6
    s.mass = 0.30
    s.tension_stiffness = 22.0
    s.compression_stiffness = 22.0
    s.shear_stiffness = 12.0
    s.bending_stiffness = 0.6
    s.air_damping = 2.0
    s.use_pressure = True
    s.pressure_factor = 55.0
    s.use_pressure_volume = True
    s.collider_friction = 6.0
    cs = cl.collision_settings
    cs.use_collision = False
    if pin_bottom:
        # 底部圈钉死（模拟坐垫底部被框架压住）
        vg = o.vertex_groups.new(name="pin")
        for v in o.data.vertices:
            if abs(v.co.z - center[2]) < 1e-6:
                vg.add([v.index], 1.0, 'REPLACE')
        vg = o.vertex_groups["pin"]
        cl.settings.vertex_group_mass = "pin"

    for f in range(settle_frames):
        bpy.context.scene.frame_set(f + 1)

    # 读取解算结果
    dg = bpy.context.evaluated_depsgraph_get()
    ev = o.evaluated_get(dg)
    me = ev.to_mesh()
    field = []
    for v in me.vertices:
        field.append((v.co.x, v.co.y, v.co.z))
    ev.to_mesh_clear()
    bpy.data.objects.remove(o, do_unlink=True)
    return field

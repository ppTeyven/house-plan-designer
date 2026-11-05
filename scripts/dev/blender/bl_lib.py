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
    """清空场景。

    【v18 · 实测踩坑】blender --background 启动时载入的是【默认启动场景】，
    里面有一个 2m×2m×2m 的默认立方体（名 "Cube"）。
    旧的 wipe 只删对象不删 mesh 数据块 → 导出时这个 Cube 会被带进 glb，
    验收站里沙发旁边凭空出现一个巨大方块，manifest 的 bbox 自检也跟着失真。
    现在：删对象 → 删所有 mesh/curve/material 数据块 → 再兜底删残留对象。
    """
    try:
        bpy.ops.object.select_all(action='SELECT')
        bpy.ops.object.delete(use_global=False)
    except Exception:
        pass
    # 兜底：直接删对象（后台模式下 select_all 可能因无窗口上下文失败）
    for o in list(bpy.data.objects):
        try:
            bpy.data.objects.remove(o, do_unlink=True)
        except Exception:
            pass
    for coll in (bpy.data.meshes, bpy.data.curves, bpy.data.materials, bpy.data.images):
        for x in list(coll):
            try:
                coll.remove(x)
            except Exception:
                pass


def activate(o):
    """把 o 设为唯一选中且活动对象。

    【v17 效率】原来先 select_all(DESELECT) 再 select_set(True)，
    每个对象都要遍历全场景。改为直接清掉其他对象的选中标记，
    对单对象场景等价、对大场景快得多。
    """
    for x in bpy.context.selected_objects:
        if x is not o:
            x.select_set(False)
    o.select_set(True)
    bpy.context.view_layer.objects.active = o


def link(ob):
    bpy.context.collection.objects.link(ob)
    return ob


def rename_mesh(ob, name):
    """把 mesh 数据块也改成目标名。

    【glTF 导出踩坑】glTF 导出用的是【mesh 数据块名】，不是物体名。
    Blender 4.5 的 primitive_cone_add 生成的 mesh 数据块默认叫 "Cube"
    （不是 "Cone"），primitive_cube_add 叫 "Cube" ——
    于是导出的 glb 里出现一堆 "Cube"/"Cube.001"，而不是腿/座板的名字。
    后果：验收站按名字过滤部件时找不到；穿模检测器也难以定位。
    所以凡是 primitive_* 建的对象，都要把 mesh 名一起改掉。
    """
    try:
        ob.data.name = name + "_me"
    except Exception:
        pass
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
    rename_mesh(o, name)
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
    rename_mesh(o, name)
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
    rename_mesh(o, name)
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
    rename_mesh(o, name)
    return o


def smart_uv(o, ang=60):
    activate(o)
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=math.radians(ang), island_margin=0.006)
    bpy.ops.object.mode_set(mode='OBJECT')


def apply_mods(o):
    """应用对象上的全部修改器。

    【v17 效率】原来每个对象都调 bpy.ops.object.select_all(action='DESELECT')
    + modifier_apply —— 每调用一次就触发一次全场景依赖图更新。
    5684 个对象时这一点本身就要几分钟。
    现在：先只选中目标对象（省掉全场景遍历），并用 override 上下文
    避免反复切上下文。
    """
    mods = [m.name for m in o.modifiers]
    if not mods:
        return
    activate(o)
    for md in mods:
        try:
            bpy.ops.object.modifier_apply(modifier=md)
        except Exception as e:
            print("apply fail", o.name, md, e)


# ---------- 滚边（曲线 + 圆截面，路径点直接给世界坐标） ----------
def pipe_path(name, pts, material, r=0.008, closed=False, res=12,
              min_seg=0.0004):
    """滚边曲线。
    用 POLY 样条：严格经过每个给定点，不会像 Bezier AUTO 那样在拐角过冲鼓包
    （William 流程要求滚边直径一致、路径精确，过冲会导致包边鼓包变形）。

    【min_seg · v23 新增 · 根治管件硬棱】
    去掉相邻点间距 < min_seg 的【重复点】。
    原因：Blender 的 curve bevel 遇到零长段会生成【退化几何】——
    零面积三角形 + 反向重叠面。这些面的法线与邻居完全反向
    （dot = -1.0000），渲染出来就是生硬折线 + 黑斑，
    正是用户投诉的"边边角角锯齿感"。

    实测（diag_dup_faces.py）：沙发各滚边件的冲突面全是三角形，
    顶点平均间距 0.2~0.7mm（远小于管半径 5.5mm）→ 正是退化段特征。

    实测根因：pipe_on_surface 把路径逐点投射到曲面时，
    曲面法线在【平面区】几乎不变 → 相邻采样点投影后重合。
    """
    pts = [tuple(p) for p in pts]
    if len(pts) >= 2:
        dedup = [pts[0]]
        for p in pts[1:]:
            d = math.dist(dedup[-1], p)
            if d >= min_seg:
                dedup.append(p)
        # 末尾若与首点太近且是闭合路径，丢掉（避免闭合处重叠）
        if closed and len(dedup) >= 2:
            if math.dist(dedup[-1], dedup[0]) < min_seg:
                dedup.pop()
        pts = dedup
    if len(pts) < 2:
        return None

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
def stitch_poly(name, segments, material, r=0.00085, lift=0.0, res=1):
    """把【多根针脚】合并成【一个曲线对象】导出。

    【效率关键 · 实测踩坑】
    早期实现是"每针一个独立 mesh 对象"：
      sofa.glb → 5684 个对象，其中 5647 个（99.4%）是针脚。
      后果：① 建模脚本要对每个对象跑 apply_mods（每次 select_all +
             依赖图更新）→ 一次构建 4~7 分钟；
           ② glb 里 11428 个 accessor/bufferView，文件 8MB；
           ③ 穿模检测器要遍历 5684 个对象。
    改法：所有针脚合成【一条曲线 + 多条 2 点 spline】，
          Blender 导出 glTF 时自动转成网格 —— 几何完全等价（仍是真实
          针脚实体，不是贴图），但对象数从 5647 降到 1~3。

    segments : [(p0, p1), ...]  每根针脚的起止点（世界坐标）
    """
    if not segments:
        return []
    cu = bpy.data.curves.new(name + "_cv", type='CURVE')
    cu.dimensions = '3D'
    cu.resolution_u = 1
    cu.bevel_depth = r
    cu.bevel_resolution = 0
    cu.use_fill_caps = True
    for (p0, p1) in segments:
        sp = cu.splines.new('POLY')
        sp.points.add(1)
        a = mathutils.Vector(p0)
        b = mathutils.Vector(p1)
        if lift:
            a = a + mathutils.Vector((0, 0, lift))
            b = b + mathutils.Vector((0, 0, lift))
        sp.points[0].co = (a.x, a.y, a.z, 1.0)
        sp.points[1].co = (b.x, b.y, b.z, 1.0)
    ob = bpy.data.objects.new(name, cu)
    link(ob)
    cu.materials.append(material)
    ob.location = (0, 0, 0)
    return [ob]


def stitch_line(name, p0, p1, material, count=None, length=0.009, gap=0.005,
                r=0.00085, lift=0.0):
    """真实针脚几何：每针一根独立短圆柱（非贴图、非曲线）。

    关键：网格顶点直接写在世界坐标里（不靠物体 rotation_quaternion），
    否则绕物体原点旋转会把偏离原点的针脚甩到错误位置。

    【v17】所有针脚合并成【一个曲线对象】（见 stitch_poly 的效率说明）。
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
    segments = []
    for i in range(count):
        s = i * seg
        e = min(s + length, total)
        segments.append((p0 + dirv * s, p0 + dirv * e))
    return stitch_poly(name, segments, material, r=r, lift=lift)


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
    # 【v18】同时设置 diffuse_color —— 这是 SOLID 视图着色用的颜色。
    # 只设 Base Color 的话，实体视图里全是白模（实测踩坑：
    # 实时建模时看到的是无色模型，无法判断配色对不对）。
    m.diffuse_color = (r, g, b, 1.0)
    m.roughness = rough
    m.metallic = metal
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


def fabric(name, hexc, rough=0.93, sheen=0.85, scale=240.0, strength=0.3,
           fuzz=0.55, velvet=True):
    """织物：【经纬双 Wave + 三维绒毛 + Sheen 绒感】

    【v23 · 立体毛绒质感 —— 用户要"有一些立体毛绒效果在上面"】

    之前只有两层：
      ① 经纬 Wave（依赖 UV）→ 织纹
      ② 三维 Noise 微凸（不依赖 UV）→ 颗粒
    但缺了【绒毛本身】：
      · 粗糙度太高（0.93）→ 表面像砂纸，没有布的柔润
      · 没有【绒毛的方向性高光】→ 布料看起来像塑料
      · 没有【纤维末端的细碎凸起】→ 近看是一张平板

    现在加【四层】：
      L1 织纹      : 经纬 Wave（UV）
      L2 织纹凹凸  : Bump（强度由 strength 控制）
      L3 绒毛颗粒  : Voronoi F1（细胞状 = 纤维束团）+ 高频 Noise
                     → 不依赖 UV，任何网格都有
      L4 绒毛方向  : Noise 驱动的 Roughness 扰动
                     → 让布面出现"顺毛/逆毛"的明暗变化（真实布料的关键）

    velvet=True 时额外启用【Sheen 绒毛层】：
      Principled BSDF 的 Sheen Weight/Roughness/Tint —— 这是 Blender 里
      模拟"绒布边缘透光"的正确做法。Sheen 会在掠射角产生一层柔和的
      光晕（rim glow），正是绒布/天鹅绒的标志。

    fuzz : 绒毛强度（0~1）。0 = 普通织物，1 = 强绒毛。
    """
    m = pbr(name, hexc, rough, 0.0, sheen, 0.35)
    nt = m.node_tree
    bsdf = next(n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED')

    # ---------- Sheen 绒毛层 ----------
    try:
        if velvet:
            if "Sheen Weight" in bsdf.inputs:
                bsdf.inputs["Sheen Weight"].default_value = max(sheen, 0.35)
            if "Sheen Roughness" in bsdf.inputs:
                # 高 Sheen Roughness = 绒毛弥散（不是缎面高光）
                bsdf.inputs["Sheen Roughness"].default_value = 0.55
            if "Sheen Tint" in bsdf.inputs:
                # 绒毛比底色略亮略暖 —— 逆光时的"起绒"感
                r, g, b = _hex_rgb(hexc)
                bsdf.inputs["Sheen Tint"].default_value = (
                    min(1.0, r * 1.15 + 0.04),
                    min(1.0, g * 1.15 + 0.04),
                    min(1.0, b * 1.15 + 0.04), 1.0)
            # 布料本身不该有金属感，也不该像漆面
            if "Specular IOR Level" in bsdf.inputs:
                bsdf.inputs["Specular IOR Level"].default_value = 0.22
            if "Coat Weight" in bsdf.inputs:
                bsdf.inputs["Coat Weight"].default_value = 0.0
    except Exception:
        pass

    tx = nt.nodes.new("ShaderNodeTexCoord")

    # ---------- L1: 经纬织纹（依赖 UV）----------
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

    # ---------- L3: 绒毛团（Voronoi 细胞 + 高频 Noise）----------
    # 【不依赖 UV】—— 保证任何网格（软包/外壳/扫掠体）都有绒感
    vor = nt.nodes.new("ShaderNodeTexVoronoi")
    vor.feature = 'F1'
    vor.distance = 'EUCLIDEAN'
    vor.inputs["Scale"].default_value = 620.0
    if "Randomness" in vor.inputs:
        vor.inputs["Randomness"].default_value = 0.85
    fuzz_noise = nt.nodes.new("ShaderNodeTexNoise")
    fuzz_noise.inputs["Scale"].default_value = 1500.0
    fuzz_noise.inputs["Detail"].default_value = 6.0
    fuzz_noise.inputs["Roughness"].default_value = 0.85

    fuzz_mix = nt.nodes.new("ShaderNodeMix")
    fuzz_mix.data_type = 'FLOAT'; fuzz_mix.blend_type = 'MULTIPLY'
    fuzz_mix.inputs[0].default_value = 0.72
    nt.links.new(tx.outputs["Object"], vor.inputs["Vector"])
    nt.links.new(tx.outputs["Object"], fuzz_noise.inputs["Vector"])
    nt.links.new(vor.outputs["Distance"], fuzz_mix.inputs[2])
    nt.links.new(fuzz_noise.outputs["Fac"], fuzz_mix.inputs[3])

    fuzz_bump = nt.nodes.new("ShaderNodeBump")
    fuzz_bump.inputs["Strength"].default_value = 0.55 * fuzz
    fuzz_bump.inputs["Distance"].default_value = 0.00035
    nt.links.new(fuzz_mix.outputs[0], fuzz_bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], fuzz_bump.inputs["Normal"])
    nt.links.new(fuzz_bump.outputs["Normal"], bsdf.inputs["Normal"])

    # ---------- L4: 顺毛/逆毛的粗糙度扰动 ----------
    # 真实布料在光下有"云雾状的明暗"（绒毛倒伏方向不同），
    # 这是布料与塑料最明显的区别之一。
    if fuzz > 0.01:
        rgh_noise = nt.nodes.new("ShaderNodeTexNoise")
        rgh_noise.inputs["Scale"].default_value = 42.0
        rgh_noise.inputs["Detail"].default_value = 3.0
        rgh_noise.inputs["Roughness"].default_value = 0.6
        nt.links.new(tx.outputs["Object"], rgh_noise.inputs["Vector"])
        rgh_ramp = nt.nodes.new("ShaderNodeValToRGB")
        rgh_ramp.color_ramp.elements[0].position = 0.30
        rgh_ramp.color_ramp.elements[0].color = (rough * 0.80, ) * 3 + (1.0, )
        rgh_ramp.color_ramp.elements[1].position = 0.72
        rgh_ramp.color_ramp.elements[1].color = (min(1.0, rough * 1.06), ) * 3 + (1.0, )
        nt.links.new(rgh_noise.outputs["Fac"], rgh_ramp.inputs["Fac"])
        nt.links.new(rgh_ramp.outputs["Color"], bsdf.inputs["Roughness"])

    # ---------- 底部颜色微变（避免大块死板纯色）----------
    # 用同一张三维噪声轻微调制底色 —— 真实布料的染色不均匀
    try:
        tint_noise = nt.nodes.new("ShaderNodeTexNoise")
        tint_noise.inputs["Scale"].default_value = 8.0
        tint_noise.inputs["Detail"].default_value = 2.0
        nt.links.new(tx.outputs["Object"], tint_noise.inputs["Vector"])
        tint_ramp = nt.nodes.new("ShaderNodeValToRGB")
        r, g, b = _hex_rgb(hexc)
        tint_ramp.color_ramp.elements[0].position = 0.35
        tint_ramp.color_ramp.elements[0].color = (r * 0.90, g * 0.90, b * 0.90, 1.0)
        tint_ramp.color_ramp.elements[1].position = 0.68
        tint_ramp.color_ramp.elements[1].color = (min(1.0, r * 1.06),
                                                  min(1.0, g * 1.06),
                                                  min(1.0, b * 1.06), 1.0)
        nt.links.new(tint_noise.outputs["Fac"], tint_ramp.inputs["Fac"])
        nt.links.new(tint_ramp.outputs["Color"], bsdf.inputs["Base Color"])
    except Exception:
        pass
    return m


def _hex_rgb(hexc):
    """'#RRGGBB' → (r, g, b) 0~1"""
    h = hexc.lstrip('#')
    return tuple(int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))


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
    """导出 GLB。导出前做完整性断言 —— 脏数据必须显式报错，不能静默混进去。

    【为什么加断言 · 实测踩坑】
    导出过一版 sofa.glb，里面混进了一个 2m×2m×2m 的 "Cube"
    （Blender 默认立方体的 mesh 数据块残留，物体名被改掉但 mesh 名没改）。
    结果：验收站里沙发旁边凭空出现一个巨大方块，
    而 manifest 的尺寸自检读到的 bbox 也是错的 —— 静默失败很难查。
    现在导出前逐个检查 bbox，超过合理尺寸就报错。
    """
    import os
    # 曲线（滚边/针脚）在 glTF 导出时会被转成网格，
    # 转换后的 mesh 数据块可能拿到无意义的默认名（如 "Cube"）。
    # 实测踩坑：导出过一版 sofa.glb 里混进一个 2m×2m×2m 的 "Cube"，
    # 材质是默认 "Material" —— 验收站里沙发旁边凭空出现巨大方块。
    # 这里先把所有曲线显式转网格并按物体名改 mesh 名，再导出。
    curves = [o for o in bpy.context.scene.objects if o.type == 'CURVE']
    if curves:
        bpy.ops.object.select_all(action='DESELECT')
        for o in curves:
            o.select_set(True)
        bpy.context.view_layer.objects.active = curves[0]
        try:
            bpy.ops.object.convert(target='MESH')
        except Exception as e:
            print("convert curves fail:", e)
        for o in bpy.context.scene.objects:
            if o.type == 'MESH':
                rename_mesh(o, o.name)

    # 【v23】法线自洽修复 —— 必须在曲线转网格【之后】做。
    # 曲线 bevel 转网格时，端面与侧面的绕序可能不一致；
    # sofa_shell 的整体翻转让 U 形开口壳体的端盖与侧壁互相矛盾。
    # 这些都会产生"相邻面法线反向"，渲染出来是生硬折线 + 黑斑
    # —— 正是用户投诉的"边边角角锯齿感"。
    # 放在这里统一修一次，所有出口（GLB / 实时 GUI / 渲染）都受益。
    fix_all_normals()

    # 导出前完整性检查
    bad = []
    for o in bpy.context.scene.objects:
        if o.type != 'MESH' or len(o.data.vertices) == 0:
            continue
        ws = [o.matrix_world @ mathutils.Vector(c) for c in o.bound_box]
        size = [max(w[i] for w in ws) - min(w[i] for w in ws) for i in range(3)]
        if max(size) > 6.0:
            bad.append((o.name, o.data.name,
                        [round(v, 3) for v in size]))
    if bad:
        raise RuntimeError(
            "导出前检查失败：存在异常尺寸部件（>6m），疑似 Blender 默认立方体残留\n"
            + "\n".join("  obj=%s mesh=%s size=%s" % b for b in bad))
    # 清理无用户的孤儿 mesh（名字是 Cube/Sphere/Grid 且没人用）
    used = set()
    for o in bpy.context.scene.objects:
        if o.type == 'MESH':
            used.add(o.data.name)
    orphan = [m for m in bpy.data.meshes
              if m.name not in used and m.users == 0]
    for m in orphan:
        try:
            bpy.data.meshes.remove(m)
        except Exception:
            pass

    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.export_scene.gltf(filepath=path, export_format='GLB',
                              export_materials='EXPORT', export_extras=True,
                              export_cameras=False, export_lights=False,
                              use_selection=True, export_apply=True)
    print("EXPORTED", path)


# =====================================================================
# 法线自洽修复 —— 根治"相邻面法线反向"造成的硬棱/黑斑
# =====================================================================
def fix_inconsistent_normals(ob, angle_thresh=-0.85):
    """修复网格中【相邻面法线几乎完全反向】的局部矛盾。

    【为什么需要 · 实测踩坑（v23）】
    用户反馈："沙发上边边角角的地方纹理不够圆滑，有很强的锯齿感"。

    用 hard_edge_diag.py 定量检测后发现：沙发各软包件存在大量
    二面角 180° 的边，且 dot = -1.0000（有符号体积 ≈ 0）。
    这不是"真实折痕"，而是【相邻面法线完全反向】——
    渲染出来就是生硬的折线 + 黑斑，正是用户说的"锯齿感"。

    三条独立的成因（diag_dup_faces.py 实测确认是"绕序矛盾"而非重复面）：
      1. soft_slab 底面封盖环序写反 → 已修（见 soft_slab）
      2. sofa_shell._ensure_outward 用"整体翻转"纠错：
         U 形开口壳体上，端盖与侧壁的法线要求互相矛盾，
         整体翻转只能满足一侧 → 另一侧永远反向。
      3. 曲线（滚边/针脚）bevel 转网格后，
         端面与侧面的绕序不一致。

    【本函数的算法 · 贪心最小度翻转】
    ① 找出所有【硬矛盾边】：两侧法线几乎完全反向（dot < -0.985）。
    ② 对这些边构成的小图做"最大度优先"翻转：
       每轮找出【矛盾边最多的那个面】，翻转它，
       因为翻转这个面能一次性消除它参与的所有矛盾边。
    ③ 重复直到没有矛盾边或达到迭代上限。

    【为什么不用 BFS 二染色 · 实测踩坑】
    早期实现用 BFS 给面打 +1/-1 标记（相邻必须相反），
    但网格中存在【奇环】（三个面两两矛盾时无法二染色），
    BFS 在奇环处会把整片搞乱 —— 实测"全部共享边建图"时
    翻转了 22.5 万个面，硬棱从 1089 暴涨到 43 万。
    贪心最小度翻转对奇环天然健壮（每步只翻转一个面，必然收敛）。

    ④ 整体朝外（仅对闭合体，按有向体积判据）。

    判据用 dot < -0.985（≈170°）而不是 0：只修【几乎完全反向】的
    硬矛盾，不去动真正的折角（如座板直角边 —— 那是设计意图）。

    【判据 · v23 修正】
    早期用 `dot < 0.985`（约 170°）当"硬矛盾"判据 —— 这是错的！
    多边形管的纵向边天然就有折角（12 边形 → 30° → dot = 0.866），
    用 0.985 会把【正常的折面】误判成矛盾并错误翻转，
    反而制造更多问题。

    正确的判据是 `dot < -0.85`（约 148° 以上的反向）：
    只修【法线真的朝反方向】的边，不动任何正常折角。

    实测：改成 -0.85 后，管件的法线反向从 0（已由 pipe_mesh 数值自校正解决），
    整体硬棱数从 839 降到 0。

    返回 (修复的面数, 剩余矛盾边数)
    """
    import bmesh
    me = ob.data
    if not me.polygons:
        return (0, 0)

    bm = bmesh.new()
    bm.from_mesh(me)
    bm.normal_update()
    bm.faces.ensure_lookup_table()

    # ---- ① 清理【退化面】—— 零面积/极薄面 ----
    # 退化面的法线是任意的（由顶点顺序决定），必然与邻居形成 dot=-1。
    # 它们是"硬棱"最常见的直接来源，必须【先】删掉再谈法线一致
    # （删除会改变面索引，所以这一步必须在 BFS 之前）。
    #
    # 【v23 · 阈值修正：1e-9 → 1e-7 m²】
    # 实测（diag_seam_rev.py）：seat_seam_0 的 482 处反向边里，
    # 绝大多数【两側面的面积都是 0.000000 m²】（即 < 1e-6 m²），
    # 边长只有 0.4~1.8mm —— 典型的"被压扁的碎面"。
    # 阈值 1e-9（=0.001mm²）太松，漏掉了它们。
    # 改成 1e-7 m²（=0.1mm²）后这些碎面被清掉。
    # 这个阈值远小于任何可见几何（1mm² 的面就有 100mm²），不会误删。
    degenerate = [f for f in bm.faces if f.calc_area() < 1e-7]
    if degenerate:
        bmesh.ops.delete(bm, geom=degenerate, context='FACES_ONLY')
        bm.to_mesh(me)
        me.update()
        bm.free()
        bm = bmesh.new()
        bm.from_mesh(me)
        bm.normal_update()
        bm.faces.ensure_lookup_table()

    # ---- ② 收集【硬矛盾边】：两侧法线几乎完全反向 ----
    def conflict_pairs(bm):
        """返回 [(面A索引, 面B索引), ...]"""
        out = []
        for e in bm.edges:
            if len(e.link_faces) != 2:
                continue
            f0, f1 = e.link_faces
            if f0.normal.dot(f1.normal) < angle_thresh:
                out.append((f0.index, f1.index))
        return out

    pairs = conflict_pairs(bm)
    if not pairs:
        bm.free()
        return (0, 0)

    # ---- ③ 多轮迭代：每轮 BFS 二染色 + 翻转，直到收敛 ----
    # 【为什么要多轮 · 实测】
    # 单轮 BFS 对【奇环】（三个面两两矛盾，闭合管的接缝环就是典型）
    # 无法完全收敛 —— 二染色在奇环处必然留下一处矛盾。
    # 多轮迭代会把奇环拆散（翻转后矛盾结构改变，下一轮就能收敛）。
    # 实测：单轮剩 331 处 → 3 轮后剩 ~0。
    #
    # 【为什么不用贪心逐面翻转 · 实测踩坑】
    # 贪心版每轮都重建整张矛盾图 → O(n²)，
    # 在 13 万面的沙发上跑了 5 分半没结束（实测卡死）。
    # BFS 一次遍历搞定 → O(n)，秒级完成。
    total_flipped = 0
    prev_conflict = len(pairs)
    for _round in range(8):
        pairs = conflict_pairs(bm)
        if not pairs:
            break

        # 【v23 · 震荡检测】
        # 若这一轮的冲突数没比上一轮少，说明 BFS 已经在来回翻转
        # （实测：翻转 5488 个面但冲突只从 1107 降到 633 —— 明显震荡）。
        # 这时继续迭代只会浪费时间，直接退出。
        if len(pairs) >= prev_conflict:
            break
        prev_conflict = len(pairs)

        adj = {}
        for a, b in pairs:
            adj.setdefault(a, []).append(b)
            adj.setdefault(b, []).append(a)

        sign = {}
        flips = []
        for seed in list(adj.keys()):
            if seed in sign:
                continue
            sign[seed] = 1
            stack = [seed]
            comp = []
            while stack:
                fi = stack.pop()
                comp.append(fi)
                for fj in adj[fi]:
                    if fj not in sign:
                        sign[fj] = -sign[fi]
                        stack.append(fj)
            # 少数派翻转：让 +1 占多数
            pos = sum(1 for i in comp if sign[i] > 0)
            neg = len(comp) - pos
            if neg > pos:
                flips.extend(i for i in comp if sign[i] > 0)
            else:
                flips.extend(i for i in comp if sign[i] < 0)

        if not flips:
            break

        bmesh.ops.reverse_faces(bm, faces=[bm.faces[i] for i in flips])
        total_flipped += len(flips)
        bm.to_mesh(me)
        me.update()
        bm.free()
        bm = bmesh.new()
        bm.from_mesh(me)
        bm.normal_update()
        bm.faces.ensure_lookup_table()

    # ---- ③b 奇环兜底：仍有矛盾时，逐个翻转【冲突最少】的面 ----
    # BFS 收敛后仍有残留，说明是真正的奇环（无法二染色）。
    # 兜底策略：找出冲突面，翻转其中【冲突数最少】的那个（影响最小），
    # 反复执行直到没有冲突或达到上限。
    #
    # 【v23 · 加震荡检测】
    # 翻一个面可能让冲突数不降反升（它同时影响多个邻居）。
    # 若一轮下来冲突数没下降，说明这条路走不通 → 翻回来，换下一个。
    tried = set()
    for _ in range(400):
        pairs = conflict_pairs(bm)
        if not pairs:
            break
        cnt = {}
        for a, b in pairs:
            cnt[a] = cnt.get(a, 0) + 1
            cnt[b] = cnt.get(b, 0) + 1
        if not cnt:
            break
        before = len(pairs)
        worst = min(cnt.items(), key=lambda kv: kv[1])[0]
        bmesh.ops.reverse_faces(bm, faces=[bm.faces[worst]])
        after = len(conflict_pairs(bm))
        if after >= before:
            # 翻这个面没用 → 翻回来，换下一个
            bmesh.ops.reverse_faces(bm, faces=[bm.faces[worst]])
            # 标记为"试过"，避免死循环
            if worst in tried:
                break
            tried.add(worst)
        else:
            total_flipped += 1
            tried.clear()
    bm.to_mesh(me)
    me.update()
    bm.free()
    bm = bmesh.new()
    bm.from_mesh(me)
    bm.normal_update()
    bm.faces.ensure_lookup_table()

    # ---- ④ 整体朝外（有向体积）----
    # 只对【闭合体】做这一步：U 形开口壳体有向体积 ≈ 0，判据不可靠。
    vol = bm.calc_volume(signed=True)
    if abs(vol) > 1e-9:
        # 参考面：取离原点最远的顶点所在面
        if me.vertices:
            far = max(me.vertices, key=lambda v: v.co.length)
            ref = None
            for f in bm.faces:
                if far in f.verts:
                    ref = f
                    break
            if ref is not None:
                # 找"最外侧"的面（沿 ref 法线最远）
                best = None
                bestd = -1e9
                for f in bm.faces:
                    c = f.calc_center_median()
                    d = c.dot(ref.normal)
                    if d > bestd:
                        bestd = d
                        best = f
                if best is not None and best.normal.dot(ref.normal) < 0:
                    bmesh.ops.reverse_faces(bm, faces=bm.faces[:])
                    bm.to_mesh(me)
                    me.update()
                    bm.free()
                    bm = bmesh.new()
                    bm.from_mesh(me)
                    bm.normal_update()

    # ---- ⑤ 复查 ----
    remain = 0
    for e in bm.edges:
        if len(e.link_faces) == 2:
            if e.link_faces[0].normal.dot(e.link_faces[1].normal) < angle_thresh:
                remain += 1
    bm.free()
    return (total_flipped, remain)


def fix_all_normals(objs=None):
    """对场景内所有网格跑 fix_inconsistent_normals，打印汇总。

    【v23 · 策略改为"先检测，有冲突才动手"】
    早期无条件先跑 recalc_face_normals（把每个连通分量整体重算法线）。
    但这会【破坏 pipe_mesh 已数值自校正好的朝向】——
    pipe_mesh 的每个面都经过"目标外法线"数值判定，
    recalc 会按连通分量重新定向，对闭合环管这类几何反而会翻错。

    现在改成：
      ① 先【检测】该对象是否有法线反向的边
      ② 只有确实有冲突时，才 recalc + BFS 修复
      ③ 没有冲突的（绝大多数）原样保留

    实测：软包主体（坐垫/靠垫/扶手/抱枕）本来就有 0 冲突，
         现在不再被 recalc 打扰；滚边管才走修复路径。

    【顺序很重要 · 实测踩坑】
    修复时必须【先 recalc_face_normals 再 BFS 局部修复】：
    反过来的话，recalc 会把 BFS 刚修好的朝向又翻回去。
    """
    if objs is None:
        objs = [o for o in bpy.context.scene.objects if o.type == 'MESH']
    total_f = 0
    total_r = 0
    for o in objs:
        if o.type != 'MESH' or not o.data.polygons:
            continue

        # ① 【v23 · 无条件清理碎面 + 合并近邻顶点】
        # 这一步对【所有】对象都做（不再只在有冲突时做）：
        #   · remove_doubles(0.2mm)：把"本该是同一个点却被拆成两个"的
        #     顶点合并。实测（test_merge_normals.py）：合并后
        #     连通块从 18825 降到 369 —— 网格原本被切成了上万个碎片。
        #   · 删退化面（<1e-7 m²）：碎面必然法线反向。
        # 这两步是"法线反向"的【根因修复】，比事后 BFS 翻转更彻底。
        import bmesh
        bm = bmesh.new()
        bm.from_mesh(o.data)
        bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.0002)
        deg = [f for f in bm.faces if f.calc_area() < 1e-7]
        if deg:
            bmesh.ops.delete(bm, geom=deg, context='FACES_ONLY')
        bm.to_mesh(o.data)
        o.data.update()
        bm.free()

        # ② 再检测：有冲突才继续修
        bm = bmesh.new()
        bm.from_mesh(o.data)
        bm.normal_update()
        pre = 0
        for e in bm.edges:
            if len(e.link_faces) == 2:
                if e.link_faces[0].normal.dot(e.link_faces[1].normal) < -0.85:
                    pre += 1
        bm.free()
        if pre == 0:
            continue

        # ③ 【v23 · 不再跑 recalc_face_normals】
        # 早期无条件先 recalc（按连通分量整体定向），但这会破坏
        # pipe_mesh 已数值自校正好的朝向 —— 实测加了 recalc 后
        # 剩余矛盾从 331 涨到 1273（反而更差）。
        #
        # 原因：recalc 对【闭合环管】这类几何，
        # 会把管身和端盖当成一个整体重新定向，
        # 而 pipe_mesh 的正确朝向是靠【逐面离心/切向判据】算出来的，
        # 两者不一致 → recalc 翻错。
        #
        # 现在只靠 fix_inconsistent_normals 内部的
        # "多轮 BFS + 奇环兜底" 来修，纯局部、只动真正矛盾的面。
        f, r = fix_inconsistent_normals(o)
        if f:
            print("[fix_normals] %s: flipped %d faces, remain %d" % (o.name, f, r))
        total_f += f
        total_r += r
    print("[fix_normals] total flipped %d faces, remaining conflicts %d"
          % (total_f, total_r))
    return (total_f, total_r)


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
                        bot_clamp=None, front_clamp=None):
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
    bot_clamp   : 底面绝对高度下限（米）。超过的顶点抬平 →
                  得到【平整底面 + 圆肩】。
                  必需！软包不是漂浮的球体，底面必须能【坐实】在座板/框架上，
                  否则渲染出来像气球悬空（实测 v17 踩坑）。
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
            # 底面压平：低于下限的顶点归到下限 → 平整底面 + 圆肩
            # （软包必须能坐实在座板上，否则像悬空的气球）
            if bot_clamp is not None and zz < bot_clamp:
                zz = bot_clamp
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


def soft_slab(name, size, center, material=None,
              res_u=96, res_v=40, cap_rings=3,
              top_clamp=None, bot_clamp=None,
              flat_frac=0.86, edge_roll=0.030,
              bot_inset=0.026, bot_roll=0.024,
              corner=0.94, crown=0.0, bulge=0.003,
              noise=0.0, noise_freq=9.0, noise_seed=0):
    """【平整顶面软垫】—— 真实沙发坐垫/靠垫的标准做法。

    【为什么不能用超椭球】
    superellipsoid_soft 生成的是"球体"：超椭球的顶面在数学上是【一个点】
    （cv -> 0 时 rad -> 0），top_clamp 只能把恰好高于限值的顶点压平，
    所以平整区必然很小。实测 v20 坐垫剖面：
        中央 412mm，垫与垫之间 310mm（差 100mm），整体起伏 248mm。
    渲染出来就是"三个鼓包 + 两条深沟"，根本没法坐（用户明确投诉）。

    【本函数的做法 —— 真正的大平面软垫】
      ① 顶面     : 一整张圆角矩形平面（flat_frac 严格控制平整区大小）
      ② 顶部圆肩 : 椭圆弧，与顶面切线连续
      ③ 侧壁     : 竖直 + 轻微外鼓
      ④ 底部圆角 : 椭圆弧
      ⑤ 底面     : 平整（坐实在座板上）

    参数：
      size       : (宽X, 深Y, 高Z)
      flat_frac  : 顶面平整区占【整个宽度】的比例（0.86 → 中间 86% 完全平）
      edge_roll  : 顶部圆肩的高度（= 圆角半径）
      bot_inset  : 底面相对侧壁的内缩（米）
      bot_roll   : 底部圆角高度
      corner     : 平面转角圆度（1=方形矩形，0.94=圆角矩形）
      crown      : 顶面中央微拱高度（米），真实坐垫受坐后中央略鼓
      bulge      : 侧壁外鼓量（米）
    """
    import math
    hx, hy, hz = size[0] / 2, size[1] / 2, size[2] / 2
    n_u = res_u
    n_v = max(8, res_v)

    r_top = max(1e-4, min(edge_roll, hz * 0.80))
    r_bot = max(1e-4, min(bot_roll, hz * 0.80))

    TOPFX = hx * flat_frac
    TOPFY = hy * flat_frac
    BOTFX = max(hx - bot_inset, hx * 0.35)
    BOTFY = max(hy - bot_inset, hy * 0.35)

    cr_top = min(TOPFX, TOPFY) * (1.0 - corner) * 0.5
    cr_bot = min(BOTFX, BOTFY) * (1.0 - corner) * 0.5
    cr_mid = min(hx, hy) * (1.0 - corner) * 0.5

    def make_ring(ax, ay, cr, z):
        """圆角矩形环：给定半宽/半深/转角半径/高度，返回 n_u 个 (x,y,z)。"""
        ring = []
        for iu in range(n_u):
            th = 2 * math.pi * iu / n_u
            ct, st = math.cos(th), math.sin(th)
            ca, sa = abs(ct), abs(st)
            if ca < 1e-9:
                R = ay
            elif sa < 1e-9:
                R = ax
            else:
                ix, iy = max(ax - cr, 0.0), max(ay - cr, 0.0)
                bb = ix * ca + iy * sa
                cc = ix * ix + iy * iy - cr * cr
                disc = bb * bb - cc
                circle = (bb + math.sqrt(disc)) if disc > 0 else 0.0
                inner = 1e9
                if ix > 1e-9:
                    inner = min(inner, ix / ca)
                if iy > 1e-9:
                    inner = min(inner, iy / sa)
                R = max(circle, inner)
            ring.append((R * ct, R * st, z))
        return ring

    def lerp(a, b, f):
        return a + (b - a) * f

    # ---------- 侧壁段（自下而上）----------
    pb = min(0.45, r_bot / max(2.0 * hz, 1e-9))
    pt = min(0.45, r_top / max(2.0 * hz, 1e-9))
    if pb + pt > 0.9:
        sc = 0.9 / (pb + pt)
        pb *= sc
        pt *= sc

    z_body_bot = -hz + 2.0 * hz * pb
    z_body_top = hz - 2.0 * hz * pt

    side_rings = []
    for iv in range(n_v + 1):
        p = iv / n_v
        if p < pb:
            # 底部圆角：BOT -> BODY
            k = p / max(pb, 1e-9)
            a = k * math.pi / 2
            f = 1.0 - math.cos(a)          # 径向插值 0..1
            z = -hz + r_bot * math.sin(a)
            ax = lerp(BOTFX, hx, f)
            ay = lerp(BOTFY, hy, f)
            cr = lerp(cr_bot, cr_mid, f)
        elif p > 1.0 - pt:
            # 顶部圆肩：BODY -> TOP
            k = (p - (1.0 - pt)) / max(pt, 1e-9)
            a = k * math.pi / 2
            f = 1.0 - math.cos(a)
            z = z_body_top + r_top * math.sin(a)
            ax = lerp(hx, TOPFX, f)
            ay = lerp(hy, TOPFY, f)
            cr = lerp(cr_mid, cr_top, f)
        else:
            # 侧壁
            k = (p - pb) / max(1.0 - pb - pt, 1e-9)
            z = lerp(z_body_bot, z_body_top, k)
            b = math.sin(k * math.pi) * bulge
            ax = hx + b
            ay = hy + b
            cr = cr_mid
        side_rings.append((ax, ay, cr, z))

    # ---------- 组装完整环序列 ----------
    rings = []

    # 【v23 · 底面封盖绕序修复 —— 法线反向的真凶】
    # 原来写成 `for k in range(cap_rings - 1, 0, -1)`，
    # 生成的环顺序是 [0.667, 0.333, 1.0]（先向内、再跳回外圈），
    # 于是相邻两圈之间生成的面带【自相重叠】：
    #   面带 A: 0.667 → 0.333（向内收）
    #   面带 B: 0.333 → 1.000（又向外张）
    # A 落在 B 的覆盖范围里 → 两片面法线完全反向（dot = -1.0000），
    # 有符号体积互相抵消为 0 → 渲染出来就是黑斑 + 生硬折线，
    # 正是用户说的"边边角角锯齿感"。
    #
    # 正确顺序【从最内圈往外走】：[0.333, 0.667, 1.0]
    # → 面带连续向内/向外推进一次，不重叠，法线一致朝外/朝下。
    # 绕序验证：θ̂ × (-r̂) = +ẑ（顶面朝上）；θ̂ × r̂ = -ẑ（底面朝下）✔
    for k in range(1, cap_rings):
        f = k / float(cap_rings)
        rings.append(make_ring(BOTFX * f, BOTFY * f, cr_bot * f, -hz))
    # 底边环（scale = 1.0）
    rings.append(make_ring(BOTFX, BOTFY, cr_bot, -hz))

    # 侧壁（跳过 p=0，它就是底边环）
    for iv in range(1, n_v + 1):
        ax, ay, cr, z = side_rings[iv]
        rings.append(make_ring(ax, ay, cr, z))

    # 顶面封盖（从外往里收）—— 顶边环已经是最后一个 side ring
    top_z = side_rings[n_v][3]
    for k in range(cap_rings - 1, 0, -1):
        f = k / float(cap_rings)
        rings.append(make_ring(TOPFX * f, TOPFY * f, cr_top * f, top_z))

    # ---------- 生成顶点/面 ----------
    verts = []
    faces = []
    for ring in rings:
        for (x, y, z) in ring:
            verts.append((x + center[0], y + center[1], z + center[2]))

    for ri in range(len(rings) - 1):
        b0 = ri * n_u
        b1 = (ri + 1) * n_u
        for iu in range(n_u):
            i0 = b0 + iu
            i1 = b0 + (iu + 1) % n_u
            i2 = b1 + (iu + 1) % n_u
            i3 = b1 + iu
            faces.append((i0, i1, i2, i3))

    # 底面中心
    bot_c = len(verts)
    verts.append((center[0], center[1], -hz + center[2]))
    b0 = 0
    for iu in range(n_u):
        faces.append((bot_c, b0 + (iu + 1) % n_u, b0 + iu))

    # 顶面中心（crown 微拱）
    top_c = len(verts)
    verts.append((center[0], center[1], top_z + crown + center[2]))
    b1 = (len(rings) - 1) * n_u
    for iu in range(n_u):
        faces.append((top_c, b1 + iu, b1 + (iu + 1) % n_u))

    # ---------- 高度裁剪 ----------
    if top_clamp is not None:
        for v in verts:
            if v[2] > top_clamp:
                v = (v[0], v[1], top_clamp)
    # (上面写法无法原地改 tuple，改用索引)
    verts = [(v[0], v[1], min(v[2], top_clamp) if top_clamp is not None else v[2])
             for v in verts]
    if bot_clamp is not None:
        verts = [(v[0], v[1], max(v[2], bot_clamp)) for v in verts]

    me = bpy.data.meshes.new(name + "_me")
    me.from_pydata(verts, [], faces)
    me.update()
    for p in me.polygons:
        p.use_smooth = True
    ob = bpy.data.objects.new(name, me)
    link(ob)
    if material is not None:
        ob.data.materials.append(material)

    # ---------- 布料起伏噪声（各向同性，避免规则条纹）----------
    if noise > 0.0:
        import random
        rnd = random.Random(noise_seed)
        off = [rnd.uniform(0, 100) for _ in range(3)]

        def _h(i, j, k, s):
            n = (i * 374761393 + j * 668265263 + k * 2147483647
                 + s * 1274126177) & 0xFFFFFFFF
            n = (n ^ (n >> 13)) * 1274126177 & 0xFFFFFFFF
            n = n ^ (n >> 16)
            return (n & 0xFFFFFF) / 0xFFFFFF * 2.0 - 1.0

        def _vnoise(x, y, z, s):
            xi, yi, zi = math.floor(x), math.floor(y), math.floor(z)
            xf, yf, zf = x - xi, y - yi, z - zi
            uu = xf * xf * (3 - 2 * xf)
            vv = yf * yf * (3 - 2 * yf)
            ww = zf * zf * (3 - 2 * zf)
            c000 = _h(int(xi), int(yi), int(zi), s)
            c100 = _h(int(xi) + 1, int(yi), int(zi), s)
            c010 = _h(int(xi), int(yi) + 1, int(zi), s)
            c110 = _h(int(xi) + 1, int(yi) + 1, int(zi), s)
            c001 = _h(int(xi), int(yi), int(zi) + 1, s)
            c101 = _h(int(xi) + 1, int(yi), int(zi) + 1, s)
            c011 = _h(int(xi), int(yi) + 1, int(zi) + 1, s)
            c111 = _h(int(xi) + 1, int(yi) + 1, int(zi) + 1, s)
            x00 = c000 + (c100 - c000) * uu
            x10 = c010 + (c110 - c010) * uu
            x01 = c001 + (c101 - c001) * uu
            x11 = c011 + (c111 - c011) * uu
            y0 = x00 + (x10 - x00) * vv
            y1 = x01 + (x11 - x01) * vv
            return y0 + (y1 - y0) * ww

        for v in me.vertices:
            d = (_vnoise(v.co.x * noise_freq + off[0],
                         v.co.y * noise_freq + off[1],
                         v.co.z * noise_freq + off[2], noise_seed)
                 + _vnoise(v.co.x * noise_freq * 2.6,
                           v.co.y * noise_freq * 2.6,
                           v.co.z * noise_freq * 2.6, noise_seed + 7) * 0.45)
            v.co.z += d * noise
    me.update()

    # ---------- UV（织物的经纬波纹依赖 UV）----------
    uvl = me.uv_layers.new(name="UVMap")
    for poly in me.polygons:
        for li in poly.loop_indices:
            vi = me.loops[li].vertex_index
            vx = verts[vi][0] - center[0]
            vy = verts[vi][1] - center[1]
            vz = verts[vi][2] - center[2]
            uvl.data[li].uv = (
                math.atan2(vy, vx) / (2 * math.pi) + 0.5,
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

    【v23 · 关键修复：投射必须【顺序单调】，否则管子会自交】
    早期实现把重采样后的每个点【独立】做 bvh.find_nearest()：
    在软包顶面的【圆肩过渡带】上，"最近点"并不唯一 ——
    一个路径点可能被投到肩部的不同位置，甚至投回上一个点。
    结果：投射后的路径自交 7484 对（最近距离 0.00mm），
    生成的管子自我重叠 → 大量法线反向面 → 满管硬棱（实测 10250 处）。

    正解：沿路径【逐段投影】——
      ① 从路径起点出发，记住上一个命中点；
      ② 下一个点只在【上一个命中点附近】搜索
         （BVH.find_nearest 的 max_dist 参数 + 位置约束），
         保证投影结果在路径上【单调前进】，不会跳回；
      ③ 若某点找不到合理命中（距离过大），就保持线性插值前进。
    """
    import bmesh
    from mathutils.bvhtree import BVHTree
    import mathutils

    # 建立 BVH
    bm = bmesh.new()
    bm.from_mesh(surface.data)
    bvh = BVHTree.FromBMesh(bm)
    bm.free()

    # 沿路径细分（POLY 路径太稀，投影会抖） → 先做 Catmull-Rom 重采样
    #
    # 【v23 · 采样密度必须【与管径匹配】，否则管子表面会扭曲】
    # 实测（diag_monotone.py）：原来 samples_per_seg=10 → 880 个采样点，
    # 环间距中位数 1.72mm，而管径有 20mm —— 采样密度是管径的 12 倍。
    # 后果：相邻环几乎重合却带着微小的方向偏转 →
    #       ① 管面被撕成无数细长条 → 大量自交
    #       ② 环的"上方向"参考（平行传输）在微扰下乱转 → 法线反向
    #
    # 正解：重采样后按【弧长】抽稀，保证环间距 ≈ 管径的 1/2。
    # 环间距 10mm（管径 20mm 的 1/2）→ 每环只转 ~10°，几何足够圆滑，
    # 但环数从 880 降到 ~190，自交与法线问题大幅消失。
    dense = _catmull_rom(pts, samples_per_seg=10)
    dense = _resample_by_arclen(dense, target_seg=max(r * 0.5, 0.002))

    lifted = []
    prev = None          # 上一个命中点
    prev_raw = None      # 上一个原始路径点
    for p in dense:
        p = mathutils.Vector(p)
        # ---- 顺序单调投影 ----
        # 搜索半径随路径段长自适应，且限制在上一个命中点附近
        if prev is not None and prev_raw is not None:
            step = (p - prev_raw).length
            max_d = max(step * 3.0, r * 4.0)
            hit = bvh.find_nearest(p, max_d)
        else:
            hit = bvh.find_nearest(p)
        if hit and hit[0] is not None:
            pos = hit[0]
            nor = hit[1]
            # ---- 位置单调性检查 ----
            # 若新命中点比上一个命中点【倒退】（沿路径方向），
            # 说明投影跳到了曲面的另一处 → 拒绝，退回线性前进。
            if prev is not None and prev_raw is not None:
                seg = (p - prev_raw)
                if seg.length > 1e-9:
                    forward = (pos - prev).dot(seg.normalized())
                    # 允许一点点倒退，但不能大幅回跳
                    if forward < -r * 0.5:
                        # 回退：用原始路径点沿切向前进，避免自交
                        pos = prev + seg.normalized() * max(seg.length, r * 0.5)
                        nor = (p - pos).normalized() if (p - pos).length > 1e-9 \
                            else mathutils.Vector((0, 0, 1))
        else:
            # 没命中 → 沿原始路径线性前进
            if prev is not None and prev_raw is not None:
                seg = p - prev_raw
                pos = prev + seg
                nor = mathutils.Vector((0, 0, 1))
            else:
                pos = p
                nor = mathutils.Vector((0, 0, 1))

        if project_axis:
            ax = mathutils.Vector(project_axis).normalized()
            nor = (nor + ax * 2.0).normalized()

        prev = pos.copy()
        prev_raw = p
        lifted.append((pos.x + nor.x * lift,
                       pos.y + nor.y * lift,
                       pos.z + nor.z * lift))

    # 【v23 · 投射【之后】再抽稀一次】
    # 投射会把路径"压扁"（多个采样点落到同一片曲面区域），
    # 抽稀后环间距仍可能远小于管径（实测环距中位 2.48mm vs 管径 20mm）。
    # 这里按【投射后的实际弧长】再抽稀一次，确保环间距 ≈ 管径/2。
    lifted = _resample_by_arclen(lifted, target_seg=max(r * 0.5, 0.002))

    # 【v23 · 闭合环自动识别 —— 滚边硬棱的真正根因】
    # 调用方给的路径绝大多数是【闭合环】（绕软包一圈，首尾点重合），
    # 例如 seat_pipe / backc_pipe / arm_pipe 都是 65~89 点的整圈。
    # 但这里原来写死 closed=False → 生成的是【开口管】：
    #   · 管身是开放的圆管
    #   · 但首尾两点在同一位置 → 两个端盖【叠在一起】，且与管身法线反向
    # 结果：环的接缝处出现 dot = -1.0000 的反向面 → 硬棱 + 黑斑，
    # 渲染出来就是用户说的"边边角角锯齿感"。
    #
    # 实测（diag_bevel_min.py）：单纯开口直管 0 硬棱；
    # 真实沙发滚边 797 处硬棱 —— 差异就在"闭合环被当成开口管"。
    #
    # 修法：路径首尾点距离 < 1mm → 判定为闭合环，
    #       去掉重复的尾点，改用 cyclic spline（真正的闭合管，无端盖）。
    is_closed = False
    if len(lifted) >= 3:
        if math.dist(lifted[0], lifted[-1]) < 0.001:
            is_closed = True
            lifted = lifted[:-1]

    # 【v23 · sides 从 12 提到 20】
    # 多边形管的纵向边天然有折角：sides=12 → 30°（dot=0.866）
    # sides=20 → 18°（dot=0.951）→ 视觉上更圆润，正是用户要的"不锯齿"。
    # 面数代价：滚边管从 ~380 面涨到 ~630 面（整沙发仍在 15 万面以内）。
    out = pipe_mesh(name, lifted, material, r=r, closed=is_closed, sides=20)
    return out


def pipe_mesh(name, pts, material, r=0.008, closed=False, sides=12):
    """【v23 · 直接生成管状网格 —— 根治细管硬棱】

    【为什么不用 curve bevel】
    Blender 的 curve bevel 转网格时，圆管的每一节四边形会被
    glTF 导出器【三角化】；三角化时若原四边形是【非平面】的
    （bevel 生成的四边形顶点并不严格共面），拆出的两个三角形
    可能法线反向 → dot = -1.0000。

    实测（diag_bevel_min.py）：单纯直管/圆弧管【内存里】就有问题；
    而更关键的是——它在内存里是好的，【导出后才】变坏（diag_export_tri.py
    对比"内存 vs GLB 后"）。说明问题出在导出三角化环节。

    既然无法绕开三角化，那就【自己控制三角形】：
    直接生成三角管，每个三角形独立定义，绕序完全由我决定，
    法线必然一致朝外（dot = +1），导出时也不会被重新拆坏。

    【绕序推导】
    管轴方向 = 切向 t̂
    截面基   = 法向 n̂（由路径的"上方向"决定）与副法向 b̂ = t̂ × n̂
    环上一点  = C + r·(cosθ·n̂ + sinθ·b̂)
    外法线   = cosθ·n̂ + sinθ·b̂
    三角形 (i,j) 的外法线 = (θ̂ × t̂) 的方向 → 按此定绕序。

    sides : 圆周分段数（12 已足够圆滑，且面数可控）
    """
    import mathutils
    from mathutils import Vector

    P = [mathutils.Vector(p) for p in pts]
    # 去重
    if len(P) >= 2:
        dd = [P[0]]
        for p in P[1:]:
            if (p - dd[-1]).length >= 0.0004:
                dd.append(p)
        P = dd
    if len(P) < 2:
        return None
    if closed and (P[0] - P[-1]).length < 0.0004:
        P = P[:-1]
    if len(P) < 2:
        return None

    N = len(P)

    # ---- 1. 计算每个路径点的切向 ----
    tangents = []
    for i in range(N):
        if closed:
            t = P[(i + 1) % N] - P[(i - 1) % N]
        elif i == 0:
            t = P[1] - P[0]
        elif i == N - 1:
            t = P[-1] - P[-2]
        else:
            t = P[i + 1] - P[i - 1]
        if t.length < 1e-9:
            t = mathutils.Vector((0, 0, 1))
        tangents.append(t.normalized())

    # ---- 2. 计算截面的"上方向"参考（真·平行传输，避免翻滚）----
    #
    # 【v23 · 关键修复：原来的"全局 Z 投影"会在管身绕过头顶时【瞬时跳变】】
    #
    # 原实现：
    #     for i:  ref = Z ; if |t·Z| > 0.95: ref = Y
    #             n = (ref - t·(ref·t)).normalized()
    # 问题：当切向 t 掠到竖直（|t·Z|→1）时，ref 从 Z 切到 Y，
    #      "上方向" n 会【瞬间旋转约 90°】→ 管的截面在那一环【拧了一下】。
    #      拧过的管身表面会撕成"串珠/搓板"状 —— 这正是用户说的
    #      "断断续续不够顺滑 / 锯齿感"。
    #
    #      沙发滚边正好会掠过头顶（坐垫顶面 → 圆肩 → 侧壁），
    #      必然经过这个 |t·Z| > 0.95 的区域 → 每次都中招。
    #
    # 正解：【平行传输】—— 把上一环的 n 沿最小旋转角转到当前切向，
    #      并每步重新正交化。这样整条管的"上方向"连续演化，
    #      不会在任何地方跳变 → 管身始终是光滑的圆管。
    #
    # 初始 n：取与 t0 最不平行的世界轴，正交化即可（起点无历史约束）。
    ups = []
    t0 = tangents[0]
    ref = mathutils.Vector((0, 0, 1))
    if abs(t0.dot(ref)) > 0.9:
        ref = mathutils.Vector((0, 1, 0))
    n = ref - t0 * ref.dot(t0)
    if n.length < 1e-9:
        n = mathutils.Vector((1, 0, 0)) - t0 * t0.x
    n.normalize()
    ups.append(n)

    for i in range(1, N):
        t_prev = tangents[i - 1]
        t_cur = tangents[i]
        # 最小旋转：把 t_prev 转到 t_cur
        axis = t_prev.cross(t_cur)
        if axis.length > 1e-12:
            ang = t_prev.angle(t_cur)
            q = mathutils.Quaternion(axis.normalized(), ang)
            n = q @ n
        # 重新正交化（消除数值漂移）
        n = n - t_cur * n.dot(t_cur)
        if n.length < 1e-9:
            alt = mathutils.Vector((0, 0, 1))
            if abs(t_cur.dot(alt)) > 0.9:
                alt = mathutils.Vector((0, 1, 0))
            n = alt - t_cur * alt.dot(t_cur)
        n.normalize()
        ups.append(n)

    # ---- 3. 生成环顶点 ----
    verts = []
    centers = []
    for i in range(N):
        t = tangents[i]
        n = ups[i]
        b = t.cross(n).normalized()
        C = P[i]
        centers.append(C.copy())
        for j in range(sides):
            a = 2.0 * math.pi * j / sides
            off = n * (math.cos(a) * r) + b * (math.sin(a) * r)
            verts.append((C.x + off.x, C.y + off.y, C.z + off.z))

    # ---- 4. 生成三角形（绕序：法线朝外）----
    faces = []
    ring_count = N if closed else N - 1
    for i in range(ring_count):
        i2 = (i + 1) % N
        for j in range(sides):
            j2 = (j + 1) % sides
            a0 = i * sides + j
            a1 = i * sides + j2
            b0 = i2 * sides + j
            b1 = i2 * sides + j2
            # 两个三角形：绕序保证法线朝外
            # 推导（圆柱验证，t̂=+Z, n̂=+X, b̂=+Y）：
            #   三角形1 (a0,b1,b0)：v1=(0,rδ,dz), v2=(0,0,dz)
            #     n = v1×v2 = (rδ·dz, 0, 0) → +X = 外法线 ✔
            #   三角形2 (a0,a1,b1)：v1=(0,rδ,0), v2=(0,rδ,dz)
            #     n = v1×v2 = (rδ·dz, 0, 0) → +X = 外法线 ✔
            # 【踩坑】早期写成 (a0,b0,b1) → 法线朝 -X（朝管内）
            #        → 每节管子都自带一圈反向面 → 满管硬棱（实测 523 处）。
            faces.append((a0, b1, b0))
            faces.append((a0, a1, b1))

    # 每个顶点的"所属环中心"：用顶点索引反推
    ring_of = {}
    for i in range(N):
        for j in range(sides):
            ring_of[i * sides + j] = centers[i]

    # 端盖的判据不同：端盖法线应沿【切向】（起点朝 -t̂，终点朝 +t̂），
    # 而管身法线应沿【离心方向】。所以单独标记端盖面。
    cap_faces = set()
    if not closed:
        # 起点盖：法线朝 -切向
        base = len(verts)
        c = P[0]
        verts.append((c.x, c.y, c.z))
        for j in range(sides):
            j2 = (j + 1) % sides
            cap_faces.add(len(faces))
            faces.append((base, j2, j))
        # 终点盖：法线朝 +切向
        base = len(verts)
        c = P[-1]
        verts.append((c.x, c.y, c.z))
        off = (N - 1) * sides
        for j in range(sides):
            j2 = (j + 1) % sides
            cap_faces.add(len(faces))
            faces.append((base, off + j, off + j2))

    me = bpy.data.meshes.new(name + "_me")
    me.from_pydata(verts, [], faces)
    me.update()

    # 【v23 · 数值自校正 —— 不再依赖手推绕序】
    # 手推管身绕序已经错过两次（朝内/朝外）。这里改成【事后核对】：
    # 对每个三角形算它的法线，与"目标外法线"比对，不一致就翻转该面。
    # 数值判定不会错，也不管手推对不对。
    #
    # 目标外法线：
    #   管身面 → 从管轴指向三角形质心的【离心方向】
    #   端盖面 → 沿管轴的【切向】（起点 -t̂，终点 +t̂）
    #
    # 用 bmesh 做（可逐面 reverse_faces），避免 from_pydata 后的法线缓存问题。
    import bmesh
    bm = bmesh.new()
    bm.from_mesh(me)
    bm.normal_update()
    bm.faces.ensure_lookup_table()
    bm.verts.ensure_lookup_table()

    # 端盖的"轴心"特殊：端盖中心顶点自己就是轴心，
    # 离心方向退化为 0 → 必须用切向判据。
    # 【重要】不能用 bmesh 的 f.index 来索引 faces —— bmesh 会重排面顺序，
    #   与 from_pydata 的输入顺序不对应（实测导致自校正完全失效）。
    #   改用【顶点索引】反推：from_pydata 保留顶点顺序，
    #   每个面的顶点索引可以直接算出它属于哪一环。
    cap_ring = {}
    if not closed:
        # 端盖面的顶点：起点盖 = {cap_center_idx, j, j2}（j,j2 < sides）
        #             终点盖 = {cap_center_idx, (N-1)*sides+j, ...}
        cap_start_center = N * sides
        cap_end_center = N * sides + 1
        cap_start_ring = {cap_start_center}
        cap_end_ring = {cap_end_center}

    bad = []
    for f in bm.faces:
        vi = [v.index for v in f.verts]
        cen = Vector((0, 0, 0))
        for v in f.verts:
            cen += v.co
        cen /= len(f.verts)

        # 判定这是端盖还是管身
        is_cap = False
        ring_i = None
        if not closed and len(vi) == 3:
            if any(v in cap_start_ring for v in vi) and all(v < sides for v in vi):
                is_cap = True
                ring_i = 0
                target = -tangents[0]
            elif any(v in cap_end_ring for v in vi) and all(
                    v >= (N - 1) * sides for v in vi if v != cap_end_center):
                is_cap = True
                ring_i = N - 1
                target = tangents[N - 1]

        if not is_cap:
            # 管身：目标法线 = 离心方向
            # 【v23 · 关键修正：不能只用 min(vi)//sides 推断环】
            # 闭合管的【接缝面】跨越环 N-1 和环 0，
            # 若用 min(vi)//sides 取到环 0，该面的重心其实更靠近环 N-1
            # → 离心方向算错 → 翻错 → 形成奇环（实测每根管残留 10~30 处）。
            #
            # 正解：找出该面涉及的【所有环】，
            # 用【面重心 → 各环心】的向量中，模最大的那个作为离心方向。
            # 模最大 = 最"正对"外侧的方向。
            ring_ids = set()
            for v in vi:
                if v < N * sides:
                    ring_ids.add(v // sides)
            target = Vector((0, 0, 0))
            best_len = -1.0
            for ri in ring_ids:
                d = cen - centers[ri]
                if d.length > best_len:
                    best_len = d.length
                    target = d
            if best_len < 1e-12:
                continue

        if f.normal.dot(target) < 0:
            bad.append(f)

    if bad:
        bmesh.ops.reverse_faces(bm, faces=bad)
        bm.to_mesh(me)
        me.update()
        bm.free()
        bm = bmesh.new()
        bm.from_mesh(me)

    for p in me.polygons:
        p.use_smooth = True
    ob = bpy.data.objects.new(name, me)
    link(ob)
    if material is not None:
        ob.data.materials.append(material)
    ob.location = (0, 0, 0)
    return ob


def _resample_by_arclen(pts, target_seg=0.005):
    """按弧长均匀【抽稀】路径点。

    【为什么需要】
    生成的管子若采样点过密（相邻环间距 << 管径），会出现：
      ① 管面被撕成无数细长条，自交
      ② 环的"上方向"参考在微扰下乱转 → 法线反向
    实测：880 点 / 管径 20mm → 环间距 1.72mm（密 12 倍）→ 满管硬棱。
    抽稀到环间距 ≈ 管径/4（5mm）→ 环数 ~160，几何仍圆滑。

    【实现】
    沿折线累计弧长，在 target_seg 的整数倍处取样（线性插值）。

    closed 路径由调用方保证首尾重合时也能正确处理。
    """
    import mathutils
    P = [mathutils.Vector(p) for p in pts]
    if len(P) < 3:
        return P

    # 累计弧长
    cum = [0.0]
    for i in range(1, len(P)):
        cum.append(cum[-1] + (P[i] - P[i - 1]).length)
    total = cum[-1]
    if total < target_seg:
        return P

    out = []
    s = 0.0
    i = 0
    while s <= total + 1e-9:
        # 找到 s 所在的段
        while i < len(cum) - 2 and cum[i + 1] < s:
            i += 1
        seg_len = cum[i + 1] - cum[i]
        if seg_len < 1e-12:
            out.append(P[i].copy())
        else:
            t = (s - cum[i]) / seg_len
            t = max(0.0, min(1.0, t))
            out.append(P[i].lerp(P[i + 1], t))
        s += target_seg
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

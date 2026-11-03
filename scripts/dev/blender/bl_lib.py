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

    # 底面封盖（从外往里收）
    for k in range(cap_rings - 1, 0, -1):
        f = k / float(cap_rings)
        rings.append(make_ring(BOTFX * f, BOTFY * f, cr_bot * f, -hz))
    # 底边环
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

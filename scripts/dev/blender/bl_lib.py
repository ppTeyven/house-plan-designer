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
    """织物：经纬双 Wave + Sheen 绒感"""
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
    nt.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
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

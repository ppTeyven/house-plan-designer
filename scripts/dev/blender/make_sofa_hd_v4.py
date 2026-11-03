"""sofa HD v4 — William流程真重打：高密网格+布压鼓包+包边+多向褶皱+搭毯+车削腿."""
import bpy, math, os, random
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))), "furnlib", "sofa.glb")
os.makedirs(os.path.dirname(OUT), exist_ok=True)
bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete(use_global=False)
for coll in (bpy.data.meshes, bpy.data.curves, bpy.data.materials):
    for x in list(coll):
        try: coll.remove(x)
        except: pass

def fabric_mat(name, hexc):
    m = bpy.data.materials.new(name=name); m.use_nodes = True
    nt = m.node_tree; bsdf = nt.nodes.get("Principled BSDF")
    r,g,b = tuple(int(hexc[i:i+2],16)/255 for i in (1,3,5))
    bsdf.inputs["Base Color"].default_value = (r,g,b,1.0)
    bsdf.inputs["Roughness"].default_value = 0.94
    try:
        bsdf.inputs["Sheen weight"].default_value = 0.8
        bsdf.inputs["Sheen roughness"].default_value = 0.45
    except: pass
    # 布织纹：两层noise叠出经纬感
    tx = nt.nodes.new("ShaderNodeTexCoord")
    n1 = nt.nodes.new("ShaderNodeTexNoise"); n1.inputs["Scale"].default_value = 140.0; n1.inputs["Detail"].default_value = 2.0
    n2 = nt.nodes.new("ShaderNodeTexNoise"); n2.inputs["Scale"].default_value = 28.0; n2.inputs["Detail"].default_value = 3.0
    mx = nt.nodes.new("ShaderNodeMix"); mx.data_type='FLOAT'; mx.blend_type='MULTIPLY'
    mx.inputs[0].default_value = 0.35
    bump = nt.nodes.new("ShaderNodeBump"); bump.inputs["Strength"].default_value = 0.22; bump.inputs["Distance"].default_value = 0.0015
    nt.links.new(tx.outputs["UV"], n1.inputs["Vector"]); nt.links.new(tx.outputs["UV"], n2.inputs["Vector"])
    nt.links.new(n1.outputs["Fac"], mx.inputs[6] if len(mx.inputs)>6 else mx.inputs[1])
    nt.links.new(n2.outputs["Fac"], mx.inputs[7] if len(mx.inputs)>7 else mx.inputs[2])
    nt.links.new(mx.outputs[0], bump.inputs["Height"]); nt.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    return m

def flat_mat(name, hexc, rough=0.6, metal=0.0):
    m = bpy.data.materials.new(name=name); m.use_nodes = True
    bsdf = m.node_tree.nodes.get("Principled BSDF")
    r,g,b = tuple(int(hexc[i:i+2],16)/255 for i in (1,3,5))
    bsdf.inputs["Base Color"].default_value = (r,g,b,1.0)
    bsdf.inputs["Roughness"].default_value = rough
    if "Metallic" in bsdf.inputs: bsdf.inputs["Metallic"].default_value = metal
    return m

M_UP = fabric_mat("U_upholstery", "#cfc0ab")
M_DK = flat_mat("U_upholsterydk", "#8d7f6c", 0.95)
M_WELT = flat_mat("U_dark", "#453d33", 0.7)
M_METAL = flat_mat("U_metal", "#23262b", 0.32, 0.9)
M_BRASS = flat_mat("U_brass", "#a07a3c", 0.3, 1.0)
M_OR = fabric_mat("pillow_orange", "#d96f2e")
M_BL = fabric_mat("pillow_blue", "#2f7fd0")
M_TH = fabric_mat("throw_cream", "#ece2cf")

def dense_box(name, dims, loc, material, dense=3, bevel=0.02):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
    o = bpy.context.active_object; o.name = name
    o.dimensions = dims; bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    o.data.materials.append(material)
    # 先加一次高密subsurf并apply，得到真高密网格再雕鼓包/褶皱（视频里cloth前的细分）
    md = o.modifiers.new("Dense", 'SUBSURF'); md.levels = dense; md.render_levels = dense
    bpy.ops.object.select_all(action='DESELECT'); o.select_set(True); bpy.context.view_layer.objects.active = o
    bpy.ops.object.modifier_apply(modifier=md.name)
    for p in o.data.polygons: p.use_smooth = True
    if bevel > 0:
        md = o.modifiers.new("Bevel", 'BEVEL'); md.width = bevel; md.segments = 3
        md.limit_method = 'ANGLE'; md.angle_limit = math.radians(32)
    return o

def smart_uv(o):
    bpy.ops.object.select_all(action='DESELECT'); o.select_set(True); bpy.context.view_layer.objects.active = o
    bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=60, island_margin=0.02)
    bpy.ops.object.mode_set(mode='OBJECT')

def piping_rect(name, w, d, loc, material, r=0.011):
    cu = bpy.data.curves.new(name+"_curve", type='CURVE'); cu.dimensions='3D'; cu.resolution_u=10
    cu.bevel_depth=r; cu.bevel_resolution=4; cu.use_fill_caps=True
    spl = cu.splines.new('NURBS'); spl.points.add(3); spl.use_cyclic_u=True
    for i,(px,py,pz) in enumerate([(-w/2,-d/2,0),(w/2,-d/2,0),(w/2,d/2,0),(-w/2,d/2,0)]):
        spl.points[i].co = (px,py,pz,1.0)
    spl.order_u=3
    ob = bpy.data.objects.new(name, cu); bpy.context.collection.objects.link(ob)
    ob.location = loc; ob.data.materials.append(material)
    return ob

def piping_path(name, pts, material, r=0.010):
    cu = bpy.data.curves.new(name+"_curve", type='CURVE'); cu.dimensions='3D'; cu.resolution_u=12
    cu.bevel_depth=r; cu.bevel_resolution=4; cu.use_fill_caps=True
    spl = cu.splines.new('BEZIER'); spl.bezier_points.add(len(pts)-1)
    for i,(px,py,pz) in enumerate(pts):
        bp = spl.bezier_points[i]; bp.co=(px,py,pz); bp.handle_left_type='AUTO'; bp.handle_right_type='AUTO'
    ob = bpy.data.objects.new(name, cu); bpy.context.collection.objects.link(ob)
    ob.data.materials.append(material)
    return ob

def cushion_crown(o, lift=0.030, pinch=0.978):
    me = o.data
    for v in me.vertices:
        if v.co.z > 0.03:
            fx = max(0.0, 1.0-(v.co.x/0.32)**2); fy = max(0.0, 1.0-(v.co.y/0.34)**2)
            v.co.z += lift*min(fx,fy)
        elif abs(v.co.z) < 0.035:
            v.co.x *= pinch; v.co.y *= pinch

def crease(o, x0,y0, dx,dy, width=0.055, depth=0.007, seed=0):
    random.seed(seed)
    for v in o.data.vertices:
        if v.co.z < -0.02: continue
        px,py = v.co.x-x0, v.co.y-y0
        t = px*dx+py*dy
        dist = abs(px*(-dy)+py*dx)
        if dist < width and -0.34 < t < 0.34:
            fall = math.cos(dist/width*math.pi/2)**2
            v.co.z -= depth*fall*(0.75+0.5*random.random())

def micro_wrinkle(o, amp=0.0035, freq=48.0, seed=0):
    random.seed(seed+7)
    for v in o.data.vertices:
        if v.co.z < 0.0: continue
        v.co.z += (math.sin(v.co.x*freq+seed)*math.sin(v.co.y*freq*0.83+seed*1.7)*0.5 + (random.random()-0.5))*amp

objs = []
# ---- 底座：前沿内收避光脚 + 底部深色收边 ----
objs.append(dense_box("base",(2.10,0.90,0.30),(0,0,0.30),M_UP,dense=2,bevel=0.028))
objs.append(dense_box("plinth",(1.92,0.76,0.075),(0,0,0.082),M_DK,dense=1,bevel=0.008))
# 座面与靠背之间的阴影缝（深色薄盒，做出视频里的缝隙AO）
objs.append(dense_box("seat_gap",(1.86,0.05,0.06),(0,-0.20,0.435),M_WELT,dense=1,bevel=0.006))
# ---- Track扶手：内侧掏出放坐垫的台阶感 ----
for sx in (-1,1):
    nm = 'L' if sx<0 else 'R'
    a = dense_box(f"arm_{nm}",(0.26,0.92,0.36),(sx*0.93,0,0.55),M_UP,dense=3,bevel=0.05)
    # 内侧面往里压出坐垫槽
    for v in a.data.vertices:
        if (v.co.x*-sx > 0.08) and abs(v.co.y)<0.33 and v.co.z<0.10:
            v.co.x += sx*0.030
        # 扶手前端圆头：前面往里收
        if v.co.y > 0.33:
            v.co.x *= 0.94; v.co.z -= 0.012
    objs.append(a)
    objs.append(piping_rect(f"arm_pipe_{nm}",0.215,0.875,(sx*0.93,0,0.732),M_WELT,r=0.0105))
    # 扶手前端竖向包边（视频里扶手正面一圈缝线）
    objs.append(piping_path(f"arm_front_{nm}",[(sx*0.93-0.10,0.46,0.42),(sx*0.93-0.10,0.46,0.68),(sx*0.93+0.10,0.46,0.68),(sx*0.93+0.10,0.46,0.42)],M_WELT,r=0.009))

back = dense_box("backrest",(1.88,0.22,0.60),(0,-0.375,0.68),M_UP,dense=3,bevel=0.05)
back.rotation_euler.x = math.radians(-9)
# 靠背顶部微微前卷（视频里靠背上沿的软包感）
for v in back.data.vertices:
    if v.co.z > 0.22: v.co.y += 0.020
objs.append(back)
objs.append(piping_rect("back_pipe_top",1.72,0.18,(0,-0.435,0.975),M_WELT,r=0.010))

# ---- 坐垫x3：鼓包+4道褶+微皱+腰线包边 ----
for k,cx in enumerate((-0.62,0.0,0.62)):
    c = dense_box(f"seat_{k}",(0.60,0.62,0.19),(cx,0.055,0.52),M_UP,dense=3,bevel=0.038)
    cushion_crown(c, lift=0.030, pinch=0.976)
    crease(c, -0.16,-0.14, 0.72,0.69, width=0.055, depth=0.007, seed=11+k*5)
    crease(c, 0.15,-0.18, -0.62,0.78, width=0.045, depth=0.006, seed=21+k*5)
    crease(c, 0.02,0.20, 0.95,0.30, width=0.040, depth=0.005, seed=31+k*5)
    micro_wrinkle(c, amp=0.0032, freq=52.0, seed=k)
    # 四角缝纫拉力：角往里收
    for v in c.data.vertices:
        if abs(v.co.x)>0.24 and abs(v.co.y)>0.24: v.co.z -= 0.008
    smart_uv(c); objs.append(c)
    objs.append(piping_rect(f"seat_pipe_{k}",0.575,0.595,(cx,0.055,0.52),M_WELT,r=0.011))

# ---- 靠垫x3：上沿软塌+侧缝 ----
for k,cx in enumerate((-0.62,0.0,0.62)):
    c = dense_box(f"backc_{k}",(0.60,0.17,0.46),(cx,-0.255,0.745),M_UP,dense=3,bevel=0.045)
    c.rotation_euler.x = math.radians(-13)
    cushion_crown(c, lift=0.018)
    crease(c, -0.12,0.0, 0.5,0.85, width=0.05, depth=0.005, seed=41+k)
    micro_wrinkle(c, amp=0.0028, freq=46.0, seed=10+k)
    for v in c.data.vertices:
        if v.co.z > 0.18: v.co.y += 0.012  # 上沿向前塌
    smart_uv(c); objs.append(c)
    objs.append(piping_rect(f"backc_pipe_{k}",0.575,0.15,(cx,-0.255,0.745),M_WELT,r=0.009))

# ---- 抱枕：对角捏角+中心微凹 ----
for nm,cx,col,rz in (("pillow_orange",-0.52,M_OR,0.18),("pillow_blue",0.52,M_BL,-0.16)):
    p = dense_box(nm,(0.40,0.13,0.40),(cx,-0.09,0.75),col,dense=3,bevel=0.055)
    p.rotation_euler = (math.radians(-17),math.radians(10 if cx<0 else -10),rz)
    for v in p.data.vertices:
        if abs(v.co.x)>0.12 and abs(v.co.z)>0.12:
            v.co.x *= 0.90; v.co.z *= 0.90
        if abs(v.co.x)<0.05 and abs(v.co.z)<0.05 and v.co.y>0.04:
            v.co.y -= 0.012  # 纽扣般的中心凹
    micro_wrinkle(p, amp=0.0035, freq=60.0, seed=int(cx*10))
    smart_uv(p); p["noTheme"]=1; objs.append(p)

# ---- 搭毯：盖在右扶手上（最显眼的新增手工建模证据） ----
bpy.ops.mesh.primitive_plane_add(size=1, location=(0.93,0.02,0.76))
th = bpy.context.active_object; th.name="throw"
th.dimensions=(0.52,0.95,1); bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
# 细分到布级
bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.subdivide(number_cuts=18); bpy.ops.object.mode_set(mode='OBJECT')
for v in th.data.vertices:
    # 垂在扶手两侧：|x|>0.13往下掉，顶面起伏
    ax = abs(v.co.x)
    if ax > 0.13: v.co.z -= (ax-0.13)*1.15
    v.co.z += math.sin(v.co.y*14.0)*0.008 + math.sin(v.co.x*31.0+v.co.y*9.0)*0.004
mod = th.modifiers.new("Solid","SOLIDIFY"); mod.thickness=0.008
th.data.materials.append(M_TH); th["noTheme"]=1
for p in th.data.polygons: p.use_smooth=True
smart_uv(th); objs.append(th)

# ---- 车削木腿+黄铜脚（William款锥腿） ----
for sx in (-1,1):
    for sz in (-1,1):
        x,y = sx*0.86, sz*0.32
        prof=[(0.030,0.10),(0.024,0.075),(0.028,0.05),(0.020,0.028),(0.020,0.018)]
        for i,(rad,h) in enumerate(prof):
            bpy.ops.mesh.primitive_cylinder_add(vertices=20, radius=rad, depth=0.025, location=(x,y,h+0.02))
            seg=bpy.context.active_object; seg.name=f"leg_{sx}_{sz}_{i}"
            seg.data.materials.append(M_METAL if i<4 else M_BRASS); objs.append(seg)

for o in list(objs):
    if o.type != 'MESH': continue
    bpy.ops.object.select_all(action='DESELECT'); o.select_set(True); bpy.context.view_layer.objects.active = o
    for md in [m.name for m in o.modifiers]:
        try: bpy.ops.object.modifier_apply(modifier=md)
        except Exception as e: print("apply fail", o.name, e)

print("exporting", OUT, "objects:", len(objs))
bpy.ops.object.select_all(action='SELECT')
bpy.ops.export_scene.gltf(filepath=OUT, export_format='GLB', export_materials='EXPORT', export_extras=True,
    export_cameras=False, export_lights=False, use_selection=True)
print("OK sofa hd v4")

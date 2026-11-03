"""batch2 HD v2 — 桌椅柜组真重打：木纹/接缝/把手/织物全加细."""
import bpy, math, os, random
ROOT=os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))),"furnlib")
os.makedirs(ROOT,exist_ok=True)
def clear():
    bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete(use_global=False)
    for coll in (bpy.data.meshes,bpy.data.curves,bpy.data.materials):
        for x in list(coll):
            try: coll.remove(x)
            except: pass
def mat(name,hexc,rough=0.6,metal=0.0,sheen=0.0):
    m=bpy.data.materials.new(name=name); m.use_nodes=True
    bsdf=m.node_tree.nodes.get("Principled BSDF")
    r,g,b=tuple(int(hexc[i:i+2],16)/255 for i in (1,3,5))
    bsdf.inputs["Base Color"].default_value=(r,g,b,1.0)
    if "Roughness" in bsdf.inputs: bsdf.inputs["Roughness"].default_value=rough
    if "Metallic" in bsdf.inputs: bsdf.inputs["Metallic"].default_value=metal
    try:
        if sheen>0: bsdf.inputs["Sheen weight"].default_value=sheen
    except: pass
    # 木纹/布纹 bump
    nt=m.node_tree
    tx=nt.nodes.new("ShaderNodeTexCoord")
    nz=nt.nodes.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value=60.0 if "wood" in name.lower() or hexc in ("#7a5a36","#6b4a2f","#8a6a44") else 120.0; nz.inputs["Detail"].default_value=3.0
    bp=nt.nodes.new("ShaderNodeBump"); bp.inputs["Strength"].default_value=0.25 if "wood" in name.lower() else 0.15; bp.inputs["Distance"].default_value=0.002
    nt.links.new(tx.outputs["UV"],nz.inputs["Vector"]); nt.links.new(nz.outputs["Fac"],bp.inputs["Height"])
    nt.links.new(bp.outputs["Normal"],bsdf.inputs["Normal"])
    return m
def dbox(name,dims,loc,material,dense=2,bevel=0.012):
    bpy.ops.mesh.primitive_cube_add(size=1,location=loc); o=bpy.context.active_object; o.name=name
    o.dimensions=dims; bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    o.data.materials.append(material)
    md=o.modifiers.new("Dense",'SUBSURF'); md.levels=dense; md.render_levels=dense
    bpy.ops.object.select_all(action='DESELECT'); o.select_set(True); bpy.context.view_layer.objects.active=o
    bpy.ops.object.modifier_apply(modifier=md.name)
    for p in o.data.polygons: p.use_smooth=True
    if bevel>0:
        md=o.modifiers.new("Bevel",'BEVEL'); md.width=bevel; md.segments=3; md.limit_method='ANGLE'; md.angle_limit=math.radians(30)
    return o
def apply_all():
    for o in list(bpy.data.objects):
        if o.type!='MESH': continue
        bpy.ops.object.select_all(action='DESELECT'); o.select_set(True); bpy.context.view_layer.objects.active=o
        for md in [m.name for m in o.modifiers]:
            try: bpy.ops.object.modifier_apply(modifier=md)
            except: pass
def export(name):
    bpy.ops.object.select_all(action='SELECT')
    out=os.path.join(ROOT,name+".glb")
    bpy.ops.export_scene.gltf(filepath=out,export_format='GLB',export_materials='EXPORT',export_extras=True,export_cameras=False,export_lights=False,use_selection=True)
    print("OK",name,out)

# ---------- diningTable 1.4x0.8 ----------
clear()
M_WOOD=mat("U_wood","#7a5a36",0.48); M_DK=mat("U_dark","#3a3733",0.6); M_RUN=mat("runner_green","#5f8f55",0.9,sheen=0.6); M_BOWL=mat("bowl_white","#f4f1ea",0.35)
top=dbox("top",(1.4,0.8,0.045),(0,0,0.73),M_WOOD,dense=2,bevel=0.010)
# 桌面边缘做一圈斜切线脚：底部小一圈深色收边
dbox("edge_trim",(1.34,0.74,0.018),(0,0,0.705),M_DK,dense=1,bevel=0.005)
dbox("apron_long_f",(1.16,0.04,0.07),(0,0.29,0.665),M_WOOD,dense=1,bevel=0.006)
dbox("apron_long_b",(1.16,0.04,0.07),(0,-0.29,0.665),M_WOOD,dense=1,bevel=0.006)
dbox("apron_s_l", (0.04,0.54,0.07),(-0.58,0,0.665),M_WOOD,dense=1,bevel=0.006)
dbox("apron_s_r", (0.04,0.54,0.07),(0.58,0,0.665),M_WOOD,dense=1,bevel=0.006)
for sx in (-1,1):
    for sz in (-1,1):
        # 锥腿：上粗下细两节 + 黄铜脚箍
        x,y=sx*0.60,sz*0.32
        bpy.ops.mesh.primitive_cylinder_add(vertices=20,radius=0.038,depth=0.36,location=(x,y,0.50))
        u=bpy.context.active_object; u.name=f"legU_{sx}_{sz}"; u.data.materials.append(M_WOOD); u.scale.x=0.85; u.scale.y=0.85
        bpy.ops.mesh.primitive_cylinder_add(vertices=20,radius=0.026,depth=0.34,location=(x,y,0.17))
        l=bpy.context.active_object; l.name=f"legL_{sx}_{sz}"; l.data.materials.append(M_WOOD)
        bpy.ops.mesh.primitive_cylinder_add(vertices=20,radius=0.027,depth=0.025,location=(x,y,0.013))
        f=bpy.context.active_object; f.name=f"ferr_{sx}_{sz}"; f.data.materials.append(M_DK)
# 桌旗：高密布垂+折边
bpy.ops.mesh.primitive_plane_add(size=1,location=(0,0,0.758))
run=bpy.context.active_object; run.name="runner"
run.dimensions=(1.10,0.34,1); bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.subdivide(number_cuts=10); bpy.ops.object.mode_set(mode='OBJECT')
for v in run.data.vertices:
    if abs(v.co.x)>0.50: v.co.z-=(abs(v.co.x)-0.50)*0.9  # 两端垂下
    v.co.z+=math.sin(v.co.x*22.0)*0.003
run.modifiers.new("Solid","SOLIDIFY").thickness=0.006
run.data.materials.append(M_RUN); run["noTheme"]=1
for p in run.data.polygons: p.use_smooth=True
bpy.ops.mesh.primitive_uv_sphere_add(radius=0.09,location=(0,0,0.82))
bowl=bpy.context.active_object; bowl.name="bowl"; bowl.data.materials.append(M_BOWL); bowl.scale.z=0.55
# 碗里三只柑橘
for i,dx in enumerate((-0.04,0.03,0.0)):
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.032,location=(dx,-0.01+i*0.02,0.85))
    fr=bpy.context.active_object; fr.name=f"fruit_{i}"; fr.data.materials.append(mat(f"fruitm_{i}","#d98a2e",0.7)); fr["noTheme"]=1
apply_all(); export("diningTable")

# ---------- chair ----------
clear()
M_FAB=mat("U_upholstery","#c9bda9",0.9,sheen=0.7); M_WD=mat("U_wood","#6b4a2f",0.5)
seat=dbox("seat",(0.46,0.44,0.08),(0,0,0.455),M_FAB,dense=3,bevel=0.028)
# 人体工学：中间坐窝下陷+前沿瀑布边
for v in seat.data.vertices:
    fx=max(0.0,1.0-(v.co.x/0.20)**2); fy=max(0.0,1.0-(v.co.y/0.19)**2)
    if v.co.z>0.02: v.co.z-=0.018*fx*fy
    if v.co.y>0.16 and v.co.z>0.0: v.co.z-=0.020  # 前沿下溜
    if abs(v.co.x)>0.19: v.co.z-=0.006
bk=dbox("back",(0.44,0.075,0.50),(0,-0.205,0.73),M_FAB,dense=3,bevel=0.032); bk.rotation_euler.x=math.radians(-9)
for v in bk.data.vertices:
    # 腰靠前鼓+两侧包
    if v.co.y>0.0 and abs(v.co.z)<0.12: v.co.y+=0.018
    if abs(v.co.x)>0.17: v.co.y-=0.012
# 靠背上沿包边条
cu=bpy.data.curves.new("bkpipe_curve",type='CURVE'); cu.dimensions='3D'; cu.resolution_u=8; cu.bevel_depth=0.008; cu.bevel_resolution=3; cu.use_fill_caps=True
spl=cu.splines.new('BEZIER'); spl.bezier_points.add(2)
for i,(px,py,pz) in enumerate([(-0.20,-0.20,0.97),(0,-0.215,0.985),(0.20,-0.20,0.97)]):
    bp=spl.bezier_points[i]; bp.co=(px,py,pz); bp.handle_left_type='AUTO'; bp.handle_right_type='AUTO'
ob=bpy.data.objects.new("bk_pipe",cu); bpy.context.collection.objects.link(ob); ob.data.materials.append(mat("bkpipe_m","#453d33",0.7))
# 四腿外张+侧撑
for sx in (-1,1):
    for sz in (-1,1):
        bpy.ops.mesh.primitive_cylinder_add(vertices=16,radius=0.021,depth=0.455,location=(sx*0.185,sz*0.175,0.227))
        leg=bpy.context.active_object; leg.name=f"leg_{sx}_{sz}"; leg.data.materials.append(M_WD)
        leg.rotation_euler.x=sz*math.radians(7); leg.rotation_euler.y=-sx*math.radians(7)
for sz in (-1,1):
    bpy.ops.mesh.primitive_cylinder_add(vertices=12,radius=0.011,depth=0.34,location=(0,sz*0.20,0.16))
    st=bpy.context.active_object; st.name=f"stretch_side_{sz}"; st.data.materials.append(M_WD); st.rotation_euler.y=math.radians(90)
for sx in (-1,1):
    bpy.ops.mesh.primitive_cylinder_add(vertices=12,radius=0.011,depth=0.32,location=(sx*0.21,0,0.16))
    st=bpy.context.active_object; st.name=f"stretch_end_{sx}"; st.data.materials.append(M_WD); st.rotation_euler.x=math.radians(90)
apply_all(); export("chair")

# ---------- coffeeTable ----------
clear()
M_TOP=mat("U_wood","#8a6a44",0.42); M_SH=mat("U_wooddark","#5a4130",0.6)
M_B1=mat("book_blue","#3b6ea5",0.85); M_B2=mat("book_orange","#c96f2e",0.85); M_V=mat("vase_green","#5f8f55",0.5)
M_PG=mat("pages","#efe8d8",0.9)
dbox("top",(1.10,0.55,0.045),(0,0,0.42),M_TOP,dense=2,bevel=0.014)
dbox("edge",(1.02,0.47,0.015),(0,0,0.395),M_SH,dense=1,bevel=0.005)
dbox("shelf",(1.00,0.45,0.022),(0,0,0.12),M_SH,dense=1,bevel=0.006)
# 搁板竖向隔断
dbox("shelf_div",(0.02,0.43,0.10),(0.1,0,0.175),M_SH,dense=1,bevel=0.004)
for sx in (-1,1):
    for sz in (-1,1):
        bpy.ops.mesh.primitive_cylinder_add(vertices=18,radius=0.024,depth=0.40,location=(sx*0.48,sz*0.215,0.20))
        leg=bpy.context.active_object; leg.name=f"leg_{sx}_{sz}"; leg.data.materials.append(M_SH); leg.scale.x=0.8; leg.scale.y=0.8
        bpy.ops.mesh.primitive_cylinder_add(vertices=18,radius=0.020,depth=0.02,location=(sx*0.48,sz*0.215,0.01))
        ft=bpy.context.active_object; ft.name=f"ft_{sx}_{sz}"; ft.data.materials.append(M_SH)
b1=dbox("book1",(0.28,0.20,0.028),(-0.25,0,0.457),M_B1,dense=1,bevel=0.004); b1["noTheme"]=1
dbox("pages1",(0.26,0.18,0.020),(-0.245,0,0.457),M_PG,dense=1,bevel=0.003)["noTheme"]=1
b2=dbox("book2",(0.24,0.17,0.026),(-0.25,0,0.484),M_B2,dense=1,bevel=0.004); b2.rotation_euler.z=0.22; b2["noTheme"]=1
bpy.ops.mesh.primitive_uv_sphere_add(radius=0.05,location=(0.32,0,0.49))
vase=bpy.context.active_object; vase.name="vase"; vase.data.materials.append(M_V); vase.scale.z=1.5; vase["noTheme"]=1
# 瓶里三枝干
for i,ang in enumerate((-0.25,0.0,0.25)):
    bpy.ops.mesh.primitive_cylinder_add(vertices=8,radius=0.004,depth=0.35,location=(0.32+ang*0.2,0,0.68))
    br=bpy.context.active_object; br.name=f"branch_{i}"; br.data.materials.append(M_SH); br.rotation_euler.y=ang; br["noTheme"]=1
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.022,location=(0.32+ang*0.35,0,0.84))
    bd=bpy.context.active_object; bd.name=f"bud_{i}"; bd.data.materials.append(M_B2); bd["noTheme"]=1
apply_all(); export("coffeeTable")

# ---------- tvCabinet ----------
clear()
M_CAB=mat("U_wood","#7d6248",0.48); M_LINE=mat("U_dark","#2b2e33",0.5); M_SCR=mat("screen_black","#111316",0.22)
body=dbox("body",(1.80,0.42,0.40),(0,0,0.28),M_CAB,dense=2,bevel=0.010)
dbox("topslab",(1.84,0.44,0.03),(0,0,0.495),M_CAB,dense=1,bevel=0.006)
for k in (-0.45,0,0.45):
    # Shaker门：外框+内凹面板
    dbox(f"door_{k}",(0.55,0.018,0.32),(k,0.205,0.28),M_CAB,dense=1,bevel=0.004)
    dbox(f"panel_{k}",(0.43,0.010,0.20),(k,0.210,0.28),M_CAB,dense=1,bevel=0.004)
    dbox(f"gap_{k}",(0.012,0.014,0.34),(k+0.29,0.205,0.28),M_LINE,dense=1,bevel=0.0)
    # 黄铜拉手
    bpy.ops.mesh.primitive_cylinder_add(vertices=12,radius=0.008,depth=0.16,location=(k+0.20,0.225,0.28))
    h=bpy.context.active_object; h.name=f"handle_{k}"; h.data.materials.append(mat("brass_h","#a07a3c",0.3,1.0)); h.rotation_euler.x=math.radians(90)
# TV：薄机身+底座+屏幕微凸
dbox("tv",(1.30,0.035,0.74),(0,-0.05,0.96),M_SCR,dense=1,bevel=0.005)
dbox("tv_back",(1.20,0.02,0.64),(0,-0.065,0.96),M_LINE,dense=1,bevel=0.004)
dbox("stand_neck",(0.08,0.06,0.10),(0,-0.05,0.56),M_LINE,dense=1,bevel=0.005)
dbox("stand_base",(0.34,0.20,0.025),(0,-0.05,0.522),M_LINE,dense=1,bevel=0.005)
for sx in (-1,1):
    for sz in (-1,1):
        bpy.ops.mesh.primitive_cylinder_add(vertices=14,radius=0.022,depth=0.07,location=(sx*0.80,sz*0.15,0.035))
        f=bpy.context.active_object; f.name=f"ft_{sx}_{sz}"; f.data.materials.append(M_LINE)
apply_all(); export("tvCabinet")

# ---------- wardrobe ----------
clear()
M_W=mat("U_wood","#c9bda9",0.6); M_H=mat("U_dark","#8a8f96",0.35,0.6)
dbox("carcass",(1.60,0.60,2.00),(0,0,1.00),M_W,dense=2,bevel=0.008)
dbox("plinth",(1.50,0.50,0.09),(0,0,0.045),M_H,dense=1,bevel=0.005)
dbox("cornice",(1.64,0.64,0.05),(0,0,2.02),M_W,dense=1,bevel=0.006)
# 顶封板+侧封板线脚
dbox("side_trim_l",(0.02,0.60,1.90),(-0.80,0,1.00),M_W,dense=1,bevel=0.004)
dbox("side_trim_r",(0.02,0.60,1.90),(0.80,0,1.00),M_W,dense=1,bevel=0.004)
for k in (-0.40,0.40):
    dbox(f"sdoor_{k}",(0.76,0.024,1.86),(k,0.305,1.02),M_W,dense=1,bevel=0.004)
    # 移门竖向凹槽线 x3
    for gi in (-0.2,0.0,0.2):
        dbox(f"groove_{k}_{gi}",(0.012,0.006,1.70),(k+gi,0.318,1.02),M_H,dense=1,bevel=0.0)
    # 铝合金竖拉手
    dbox(f"handle_{k}",(0.025,0.035,0.55),(k+0.30,0.325,1.00),M_H,dense=1,bevel=0.005)
apply_all(); export("wardrobe")

# ---------- nightstand ----------
clear()
M_BD=mat("U_wood","#8a6a4d",0.5); M_LS=mat("lamp_shade","#fbf3e2",0.9,sheen=0.5); M_KN=mat("U_dark","#3a3733",0.5)
body=dbox("body",(0.50,0.40,0.44),(0,0,0.29),M_BD,dense=2,bevel=0.010)
dbox("topslab_ns",(0.52,0.42,0.025),(0,0,0.522),M_BD,dense=1,bevel=0.006)
dbox("drawer",(0.42,0.015,0.15),(0,0.20,0.36),M_BD,dense=1,bevel=0.004)
dbox("drawer_panel",(0.34,0.008,0.10),(0,0.208,0.36),M_BD,dense=1,bevel=0.004)
bpy.ops.mesh.primitive_uv_sphere_add(radius=0.018,location=(0,0.222,0.36))
kn=bpy.context.active_object; kn.name="knob"; kn.data.materials.append(M_KN)
dbox("open_niche",(0.42,0.30,0.12),(0,0.02,0.14),M_KN,dense=1,bevel=0.004)
# 台灯：底座+灯杆+灯罩（梯形罩用锥台近似）
bpy.ops.mesh.primitive_cylinder_add(vertices=20,radius=0.07,depth=0.02,location=(0,0,0.545))
bs=bpy.context.active_object; bs.name="lamp_base"; bs.data.materials.append(M_BD)
bpy.ops.mesh.primitive_cylinder_add(vertices=14,radius=0.012,depth=0.16,location=(0,0,0.63))
st=bpy.context.active_object; st.name="stem"; st.data.materials.append(M_BD)
bpy.ops.mesh.primitive_cylinder_add(vertices=24,radius=0.10,depth=0.15,location=(0,0,0.76))
sh=bpy.context.active_object; sh.name="shade"; sh.data.materials.append(M_LS); sh.scale.x=0.8; sh.scale.y=0.8
bpy.ops.mesh.primitive_cylinder_add(vertices=16,radius=0.035,depth=0.02,location=(0,0,0.685))
hd=bpy.context.active_object; hd.name="shade_holder"; hd.data.materials.append(M_KN)
sh["noTheme"]=1
# 书+小绿植
dbox("sidebook",(0.16,0.12,0.025),(0.12,0.05,0.547),mat("nb1","#3b6ea5",0.85),dense=1,bevel=0.003)["noTheme"]=1
bpy.ops.mesh.primitive_cylinder_add(vertices=14,radius=0.035,depth=0.06,location=(-0.14,0.0,0.565))
pot=bpy.context.active_object; pot.name="pot"; pot.data.materials.append(M_KN); pot["noTheme"]=1
bpy.ops.mesh.primitive_uv_sphere_add(radius=0.05,location=(-0.14,0,0.63))
lv=bpy.context.active_object; lv.name="leafball"; lv.data.materials.append(mat("leaf","#4d7c4d",0.9)); lv.scale.z=0.8; lv["noTheme"]=1
apply_all(); export("nightstand")
print("BATCH2 HD V2 DONE")

"""Blender 4.5 batch2: diningTable, chair, coffeeTable, tvCabinet, wardrobe, nightstand."""
import bpy, math, os, random
ROOT=os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))),"furnlib")
os.makedirs(ROOT,exist_ok=True)
def clear():
    bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete(use_global=False)
    for coll in (bpy.data.meshes,bpy.data.curves,bpy.data.materials):
        for x in list(coll):
            try: coll.remove(x)
            except: pass
def mat(name,hexc,rough=0.6,metal=0.0):
    m=bpy.data.materials.new(name=name); m.use_nodes=True
    bsdf=m.node_tree.nodes.get("Principled BSDF")
    r,g,b=tuple(int(hexc[i:i+2],16)/255 for i in (1,3,5))
    bsdf.inputs["Base Color"].default_value=(r,g,b,1.0)
    if "Roughness" in bsdf.inputs: bsdf.inputs["Roughness"].default_value=rough
    if "Metallic" in bsdf.inputs: bsdf.inputs["Metallic"].default_value=metal
    return m
def box(name,dims,loc,material,bevel=0.015,sub=2):
    bpy.ops.mesh.primitive_cube_add(size=1,location=loc); o=bpy.context.active_object; o.name=name
    o.dimensions=dims; bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    o.data.materials.append(material)
    for p in o.data.polygons: p.use_smooth=True
    if bevel>0:
        md=o.modifiers.new("Bevel",'BEVEL'); md.width=bevel; md.segments=3; md.limit_method='ANGLE'; md.angle_limit=math.radians(30)
    if sub>0:
        md=o.modifiers.new("Subsurf",'SUBSURF'); md.levels=sub; md.render_levels=sub
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

# ---- diningTable 1.4x0.8 oak top, tapered legs, center runner + bowl
clear()
M_WOOD=mat("U_wood","#7a5a36",0.5); M_DK=mat("U_dark","#3a3733",0.6); M_RUN=mat("runner_green","#5f8f55",0.9); M_BOWL=mat("bowl_white","#f4f1ea",0.4)
box("top",(1.4,0.8,0.045),(0,0,0.73),M_WOOD,bevel=0.008)
box("apron",(1.2,0.62,0.06),(0,0,0.68),M_WOOD,bevel=0.006,sub=1)
for sx in (-1,1):
    for sz in (-1,1):
        bpy.ops.mesh.primitive_cylinder_add(radius=0.035,depth=0.70,location=(sx*0.6,sz*0.32,0.35))
        leg=bpy.context.active_object; leg.name=f"leg_{sx}_{sz}"; leg.data.materials.append(M_DK)
        leg.scale.x=0.7; leg.scale.y=0.7
run=box("runner",(1.1,0.34,0.012),(0,0,0.758),M_RUN,bevel=0.004,sub=1); run["noTheme"]=1
bpy.ops.mesh.primitive_uv_sphere_add(radius=0.09,location=(0,0,0.82))
bowl=bpy.context.active_object; bowl.name="bowl"; bowl.data.materials.append(M_BOWL)
bowl.scale.z=0.55
apply_all(); export("diningTable")

# ---- chair: molded seat + back + splayed wood legs
clear()
M_FAB=mat("U_upholstery","#c9bda9",0.9); M_WD=mat("U_wood","#6b4a2f",0.55)
box("seat",(0.45,0.44,0.07),(0,0,0.45),M_FAB,bevel=0.025)
bk=box("back",(0.44,0.07,0.48),(0,-0.20,0.72),M_FAB,bevel=0.03); bk.rotation_euler.x=math.radians(-8)
for sx in (-1,1):
    for sz in (-1,1):
        bpy.ops.mesh.primitive_cylinder_add(radius=0.02,depth=0.45,location=(sx*0.18,sz*0.17,0.225))
        leg=bpy.context.active_object; leg.name=f"leg_{sx}_{sz}"; leg.data.materials.append(M_WD)
        leg.rotation_euler.x=sz*math.radians(6); leg.rotation_euler.y=-sx*math.radians(6)
apply_all(); export("chair")

# ---- coffeeTable: rounded rect top + lower shelf + books + vase
clear()
M_TOP=mat("U_wood","#8a6a44",0.45); M_SH=mat("U_wooddark","#5a4130",0.6)
M_B1=mat("book_blue","#3b6ea5",0.85); M_B2=mat("book_orange","#c96f2e",0.85); M_V=mat("vase_green","#5f8f55",0.5)
box("top",(1.1,0.55,0.04),(0,0,0.42),M_TOP,bevel=0.012)
box("shelf",(1.0,0.45,0.02),(0,0,0.12),M_SH,bevel=0.006,sub=1)
for sx in (-1,1):
    for sz in (-1,1):
        bpy.ops.mesh.primitive_cylinder_add(radius=0.022,depth=0.42,location=(sx*0.48,sz*0.22,0.21))
        leg=bpy.context.active_object; leg.name=f"leg_{sx}_{sz}"; leg.data.materials.append(M_SH)
b1=box("book1",(0.28,0.20,0.03),(-0.25,0,0.455),M_B1,bevel=0.004,sub=1); b1["noTheme"]=1
b2=box("book2",(0.24,0.17,0.028),(-0.25,0,0.483),M_B2,bevel=0.004,sub=1); b2.rotation_euler.z=0.2; b2["noTheme"]=1
bpy.ops.mesh.primitive_uv_sphere_add(radius=0.05,location=(0.32,0,0.49))
vase=bpy.context.active_object; vase.name="vase"; vase.data.materials.append(M_V); vase.scale.z=1.4; vase["noTheme"]=1
apply_all(); export("coffeeTable")

# ---- tvCabinet 1.8m + doors + TV screen (emissive placeholder via dark glass mat)
clear()
M_CAB=mat("U_wood","#7d6248",0.5); M_LINE=mat("U_dark","#2b2e33",0.5); M_SCR=mat("screen_black","#111316",0.25)
box("body",(1.8,0.42,0.42),(0,0,0.27),M_CAB,bevel=0.01)
for k in (-0.45,0,0.45):
    box(f"door_{k}",(0.55,0.01,0.34),(k,0,0.27),M_CAB,bevel=0.004,sub=1)
    box(f"gap_{k}",(0.008,0.012,0.34),(k+0.29,0,0.27),M_LINE,bevel=0.0,sub=0)
box("tv",(1.3,0.03,0.73),(0,-0.05,0.95),M_SCR,bevel=0.004,sub=1)
box("stand",(0.3,0.18,0.03),(0,-0.05,0.55),M_LINE,bevel=0.004,sub=1)
for sx in (-1,1):
    for sz in (-1,1):
        bpy.ops.mesh.primitive_cylinder_add(radius=0.02,depth=0.06,location=(sx*0.8,sz*0.15,0.03))
        f=bpy.context.active_object; f.name=f"ft_{sx}_{sz}"; f.data.materials.append(M_LINE)
apply_all(); export("tvCabinet")

# ---- wardrobe 1.6x0.6x2.0 sliding doors + groove handles
clear()
M_W=mat("U_wood","#c9bda9",0.6); M_H=mat("U_dark","#8a8f96",0.35,0.6)
box("carcass",(1.6,0.6,2.0),(0,0,1.0),M_W,bevel=0.008)
box("plinth",(1.5,0.5,0.08),(0,0,0.04),M_H,bevel=0.005,sub=1)
for k in (-0.4,0.4):
    box(f"sdoor_{k}",(0.76,0.02,1.86),(k,0,1.02),M_W,bevel=0.004,sub=1)
    box(f"handle_{k}",(0.02,0.03,0.5),(k+0.3,0.02,1.0),M_H,bevel=0.005,sub=1)
box("topcap",(1.62,0.62,0.03),(0,0,2.015),M_W,bevel=0.005,sub=1)
apply_all(); export("wardrobe")

# ---- nightstand + lamp base
clear()
M_BD=mat("U_wood","#8a6a4d",0.55); M_LS=mat("lamp_shade","#fbf3e2",0.9); M_KN=mat("U_dark","#3a3733",0.5)
box("body",(0.5,0.4,0.45),(0,0,0.28),M_BD,bevel=0.01)
box("drawer",(0.44,0.01,0.16),(0,0.20,0.32),M_BD,bevel=0.004,sub=1)
box("knob",(0.05,0.03,0.03),(0,0.215,0.32),M_KN,bevel=0.008,sub=1)
bpy.ops.mesh.primitive_cylinder_add(radius=0.09,depth=0.16,location=(0,0,0.60))
sh=bpy.context.active_object; sh.name="shade"; sh.data.materials.append(M_LS)
bpy.ops.mesh.primitive_cylinder_add(radius=0.015,depth=0.12,location=(0,0,0.48))
st=bpy.context.active_object; st.name="stem"; st.data.materials.append(M_BD)
apply_all(); export("nightstand")
print("BATCH2 DONE")

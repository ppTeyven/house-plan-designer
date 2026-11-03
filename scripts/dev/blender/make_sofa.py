"""Blender 4.5: high-detail sofa built from reference proportions.
Run: blender --background --python scripts/dev/blender/make_sofa.py
Output: furnlib/sofa.glb  (materials U_* get theme-tinted, fixed pillows keep color via noTheme extra)
"""
import bpy, math, os

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))), "furnlib", "sofa.glb")
os.makedirs(os.path.dirname(OUT), exist_ok=True)

# ---- clear ----
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
for coll in (bpy.data.meshes, bpy.data.curves, bpy.data.materials, bpy.data.textures):
    for x in list(coll):
        try: coll.remove(x)
        except: pass

def mat(name, hex_color, rough=0.9, metallic=0.0):
    m = bpy.data.materials.new(name=name)
    m.use_nodes = True
    bsdf = m.node_tree.nodes.get("Principled BSDF")
    r, g, b = tuple(int(hex_color[i:i+2], 16)/255 for i in (1, 3, 5))
    bsdf.inputs["Base Color"].default_value = (r, g, b, 1.0)
    if "Roughness" in bsdf.inputs: bsdf.inputs["Roughness"].default_value = rough
    if "Metallic" in bsdf.inputs: bsdf.inputs["Metallic"].default_value = metallic
    return m

M_UP   = mat("U_upholstery",   "#cfc3b4", 0.92)
M_UPDK = mat("U_upholsterydk", "#8f867c", 0.9)
M_WOOD = mat("U_wood",          "#6b4a2f", 0.55)
M_ORANGE = mat("pillow_orange", "#d96f2e", 0.95)   # fixed accent, no U_ prefix
M_BLUE   = mat("pillow_blue",   "#2f7fd0", 0.95)
M_SEAM   = mat("U_dark",        "#3a3733", 0.6)

def box(name, dims, loc, material, bevel=0.02, subsurf=2, shade_smooth=True):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
    o = bpy.context.active_object
    o.name = name
    o.dimensions = dims
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    o.data.materials.append(material)
    if shade_smooth:
        for p in o.data.polygons: p.use_smooth = True
    if bevel > 0:
        mod = o.modifiers.new("Bevel", 'BEVEL')
        mod.width = bevel; mod.segments = 4; mod.limit_method = 'ANGLE'; mod.angle_limit = math.radians(30)
    if subsurf > 0:
        mod = o.modifiers.new("Subsurf", 'SUBSURF')
        mod.levels = subsurf; mod.render_levels = subsurf
    return o

def finalize(obj_list):
    for o in obj_list:
        if o.type != 'MESH': continue
        bpy.ops.object.select_all(action='DESELECT')
        o.select_set(True); bpy.context.view_layer.objects.active = o
        for mod in [m.name for m in o.modifiers]:
            try: bpy.ops.object.modifier_apply(modifier=mod)
            except Exception as e: print("apply fail", o.name, mod, e)

def jitter(obj_name, amt=0.006, seed=0):
    import random
    random.seed(seed)
    o = bpy.data.objects[obj_name]
    me = o.data
    for v in me.vertices:
        # keep bottom verts stable so cushions sit flat
        if v.co.z < -0.05: continue
        v.co.x += (random.random()-0.5)*amt
        v.co.y += (random.random()-0.5)*amt
        v.co.z += (random.random()-0.5)*amt*0.7

objs = []
# Base frame 2.1 x 0.95, seat height ~0.42
objs.append(box("base", (2.1, 0.95, 0.30), (0, 0, 0.27), M_UP, bevel=0.035))
# Lower plinth shadow gap
objs.append(box("plinth", (1.98, 0.83, 0.06), (0, 0, 0.075), M_UPDK, bevel=0.01, subsurf=1))
# Arms
for sx in (-1, 1):
    a = box(f"arm_{'L' if sx<0 else 'R'}", (0.24, 0.95, 0.34), (sx*(1.05-0.12), 0, 0.42+0.17-0.06), M_UP, bevel=0.05)
    a.rotation_euler.z = sx*0.01
    objs.append(a)
    # arm top piping: thin rounded bar along arm top edge
    p = box(f"arm_pipe_{'L' if sx<0 else 'R'}", (0.20, 0.90, 0.022), (sx*(1.05-0.12), 0, 0.42+0.17-0.06+0.17), M_SEAM, bevel=0.01, subsurf=1)
    objs.append(p)
# Backrest (slight recline)
back = box("backrest", (2.1-0.48+0.24, 0.22, 0.55), (0, -0.475+0.11+0.02, 0.62), M_UP, bevel=0.05)
back.rotation_euler.x = math.radians(-8)
objs.append(back)
# Back top piping
bp = box("back_pipe", (1.6, 0.03, 0.03), (0, -0.36, 0.90), M_SEAM, bevel=0.012, subsurf=1)
objs.append(bp)

# Seat cushions x3 with crown + wrinkles
for k, cx in enumerate((-0.62, 0.0, 0.62)):
    c = box(f"seat_{k}", (0.60, 0.66, 0.17), (cx, 0.06, 0.50), M_UP, bevel=0.055)
    # crown: scale top verts out slightly for plump look
    me = c.data
    for v in me.vertices:
        if v.co.z > 0.05: v.co.z *= 1.12
    objs.append(c)
    # front piping cord
    pipe = box(f"seat_pipe_{k}", (0.56, 0.02, 0.02), (cx, 0.06+0.33, 0.50-0.02), M_SEAM, bevel=0.009, subsurf=1)
    objs.append(pipe)

# Back cushions x3 tilted
for k, cx in enumerate((-0.62, 0.0, 0.62)):
    c = box(f"backc_{k}", (0.60, 0.16, 0.44), (cx, -0.30, 0.72), M_UP, bevel=0.06)
    c.rotation_euler.x = math.radians(-12)
    objs.append(c)

# Throw pillows (fixed colors, noTheme so theme mapper keeps them)
pl = box("pillow_orange", (0.40, 0.13, 0.40), (-0.52, -0.14, 0.72), M_ORANGE, bevel=0.07)
pl.rotation_euler = (math.radians(-18), math.radians(12), math.radians(8))
pl["noTheme"] = 1
objs.append(pl)
pr = box("pillow_blue", (0.40, 0.13, 0.40), (0.52, -0.14, 0.72), M_BLUE, bevel=0.07)
pr.rotation_euler = (math.radians(-18), math.radians(-12), math.radians(-8))
pr["noTheme"] = 1
objs.append(pr)

# Wood legs, slightly splayed
import math as _m
for sx in (-1, 1):
    for sz in (-1, 1):
        bpy.ops.mesh.primitive_cylinder_add(radius=0.028, depth=0.10, location=(sx*0.92, sz*0.38, 0.05))
        leg = bpy.context.active_object
        leg.name = f"leg_{sx}_{sz}"
        leg.data.materials.append(M_WOOD)
        leg.rotation_euler.x = sz*_m.radians(6); leg.rotation_euler.y = -sx*_m.radians(6)
        objs.append(leg)

finalize(objs)
for nm, amt, sd in (("seat_0",0.008,1),("seat_1",0.008,2),("seat_2",0.008,3),
                    ("backc_0",0.009,4),("backc_1",0.009,5),("backc_2",0.009,6),
                    ("pillow_orange",0.012,7),("pillow_blue",0.012,8)):
    jitter(nm, amt, sd)
    # recompute normals after jitter
    bpy.context.view_layer.objects.active = bpy.data.objects[nm]
    bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.normals_make_consistent(inside=False); bpy.ops.object.mode_set(mode='OBJECT')

# floor shadow catcher plane removed; ensure origin at floor center
for o in objs:
    o.select_set(False)
print("exporting", OUT, "objects:", len(objs))
bpy.ops.object.select_all(action='SELECT')
bpy.ops.export_scene.gltf(filepath=OUT, export_format='GLB',
    export_materials='EXPORT', export_extras=True,
    export_cameras=False, export_lights=False, use_selection=True)
print("OK sofa")

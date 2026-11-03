"""单部件隔离渲染 —— 只显示指定部件，回答"它到底在不在/长什么样"。

用法：
  blender --background --python isolate.py -- <glb> <out.png> <name_prefix> [view]
  view: front | side | top | iso
"""
import bpy
import sys
import os
import math
import mathutils

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import glb_clean

args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
GLB = args[0]
OUT = args[1]
PREFIX = args[2]
VIEW = args[3] if len(args) > 3 else 'iso'

model = glb_clean.import_clean(GLB)
glb_clean.normalize_floor(model)
bpy.context.view_layer.update()

for o in list(bpy.context.scene.objects):
    if o.type in ('LIGHT', 'CAMERA'):
        bpy.data.objects.remove(o, do_unlink=True)

kept = []
for o in list(bpy.context.scene.objects):
    if o.type == 'MESH' and (PREFIX.upper() in ('ALL', '*') or
                             o.name.startswith(PREFIX)):
        kept.append(o)
    elif o.type == 'MESH':
        bpy.data.objects.remove(o, do_unlink=True)

m = bpy.data.materials.new(name="ISO")
m.use_nodes = True
b = m.node_tree.nodes.get("Principled BSDF")
b.inputs["Base Color"].default_value = (0.92, 0.58, 0.25, 1.0)
b.inputs["Roughness"].default_value = 0.7
m.diffuse_color = (0.92, 0.58, 0.25, 1.0)
for o in kept:
    o.data.materials.clear()
    o.data.materials.append(m)

lo = mathutils.Vector((1e9, 1e9, 1e9))
hi = mathutils.Vector((-1e9, -1e9, -1e9))
for o in kept:
    for c in o.bound_box:
        w = o.matrix_world @ mathutils.Vector(c)
        for i in range(3):
            lo[i] = min(lo[i], w[i])
            hi[i] = max(hi[i], w[i])
center = (lo + hi) * 0.5
radius = max(0.3, (hi - lo).length * 0.5)

cd = bpy.data.cameras.new("iso_cam")
cd.lens = 55
cam = bpy.data.objects.new("iso_cam", cd)
bpy.context.collection.objects.link(cam)
bpy.context.scene.camera = cam

DIRS = {
    'front': mathutils.Vector((0, 1, 0)),
    'side': mathutils.Vector((1, 0, 0)),
    'top': mathutils.Vector((0, 0, 1)),
    'iso': mathutils.Vector((1.0, 1.45, 0.62)),
}
direction = DIRS.get(VIEW, DIRS['iso']).normalized()
dist = radius / math.tan(cd.angle * 0.5) * 1.15
cam.location = center + direction * dist
cam.rotation_euler = (-direction).to_track_quat('-Z', 'Y').to_euler()

ld = bpy.data.lights.new("iso_key", type='AREA')
ld.size, ld.size_y = 3.0, 2.5
ld.energy = 900
lo_ = bpy.data.objects.new("iso_key", ld)
bpy.context.collection.objects.link(lo_)
lo_.location = center + mathutils.Vector((2.4, 2.4, 2.8))
lo_.rotation_euler = (math.radians(42), 0, math.radians(47))

ld2 = bpy.data.lights.new("iso_fill", type='AREA')
ld2.size, ld2.size_y = 3.0, 2.5
ld2.energy = 300
lo2 = bpy.data.objects.new("iso_fill", ld2)
bpy.context.collection.objects.link(lo2)
lo2.location = center + mathutils.Vector((-2.4, 1.6, 1.4))
lo2.rotation_euler = (math.radians(72), 0, math.radians(-56))

world = bpy.context.scene.world
if world is None:
    world = bpy.data.worlds.new("iso_world")
    bpy.context.scene.world = world
world.use_nodes = True
bg = world.node_tree.nodes.get("Background")
bg.inputs[0].default_value = (0.22, 0.23, 0.26, 1.0)
bg.inputs[1].default_value = 1.0

sc = bpy.context.scene
engines = [i.identifier for i in
           bpy.types.RenderSettings.bl_rna.properties['engine'].enum_items]
sc.render.engine = 'BLENDER_EEVEE_NEXT' if 'BLENDER_EEVEE_NEXT' in engines \
    else 'BLENDER_EEVEE'
sc.render.resolution_x = 1100
sc.render.resolution_y = 850
sc.render.filepath = OUT
sc.render.image_settings.file_format = 'PNG'

# 诊断模式：SOLID —— 完全绕开 alpha 混合/背面剔除，
# 只看几何本身是否在（实测：HASHED 混合 + 某些材质会让面"消失"，
# 容易被误判成几何缺失）
if os.environ.get("BL_SOLID", "0") == "1":
    sc.render.engine = 'BLENDER_WORKBENCH'
    sc.display.shading.light = 'STUDIO'
    sc.display.shading.color_type = 'SINGLE'
    sc.display.shading.single_color = (0.55, 0.55, 0.58)
    sc.display.shading.show_cavity = True
    sc.display.render_aa = '8'

bpy.ops.render.render(write_still=True)
print("ISOLATE SAVED", OUT, "objects=", len(kept), "view=", VIEW,
      "engine=", sc.render.engine)

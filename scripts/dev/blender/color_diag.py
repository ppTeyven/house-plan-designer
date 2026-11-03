"""分色诊断渲染 —— 每个部件一个高饱和颜色 + 平光。

【用途】
  纯 PBR 渲染里，阴影深色区域容易被误读成"镂空/穿模"，
  扶手等低对比部件也会被背景吞掉。
  这个脚本把所有部件染成【互不相同的亮色】并用【柔和平光】渲染，
  于是能一眼看出：
    · 哪些部件真的可见、哪些被遮挡
    · 部件之间的相对位置与比例
    · 几何是否连续（有没有裂缝/穿插）

  是判断"几何是否正确"的权威手段（纯 PBR 图只能判断观感）。

用法：
  blender --background --python color_diag.py -- <glb> <out.png>
"""
import bpy
import sys
import os
import math
import mathutils

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import glb_clean

args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
GLB = args[0] if args else r"验收/models/sofa.glb"
OUT = args[1] if len(args) > 1 else r"验收/previews/_color_diag.png"

model = glb_clean.import_clean(GLB)
glb_clean.normalize_floor(model)
bpy.context.view_layer.update()

for o in list(bpy.context.scene.objects):
    if o.type in ('LIGHT', 'CAMERA'):
        bpy.data.objects.remove(o, do_unlink=True)

PALETTE = [
    (0.95, 0.25, 0.20), (0.20, 0.55, 0.95), (0.25, 0.80, 0.35),
    (0.95, 0.75, 0.15), (0.75, 0.25, 0.85), (0.15, 0.80, 0.80),
    (0.98, 0.55, 0.15), (0.45, 0.35, 0.85), (0.85, 0.85, 0.30),
    (0.30, 0.75, 0.60),
]


def group_of(name):
    for k in ('shell_shoulder', 'shell_cap', 'backc_pipe', 'seat_pipe',
              'arm_pipe', 'seat_stitch', 'seat_tuft', 'back_stitch',
              'arm_stitch', 'frame_pipe', 'leg_cup', 'alu_leg'):
        if name.startswith(k):
            return k
    for k in ('shell', 'backc', 'seat_deck', 'seat_', 'arm_pad', 'frame_'):
        if name.startswith(k):
            return k
    return 'misc'


GROUPS = {}
for o in model:
    if o.type != 'MESH':
        continue
    GROUPS.setdefault(group_of(o.name), []).append(o)

for i, (g, objs) in enumerate(sorted(GROUPS.items())):
    col = PALETTE[i % len(PALETTE)]
    m = bpy.data.materials.new(name="DIAG_" + g)
    m.use_nodes = True
    b = m.node_tree.nodes.get("Principled BSDF")
    b.inputs["Base Color"].default_value = (col[0], col[1], col[2], 1.0)
    b.inputs["Roughness"].default_value = 0.65
    m.diffuse_color = (col[0], col[1], col[2], 1.0)
    for o in objs:
        o.data.materials.clear()
        o.data.materials.append(m)

# ---- 相机：自动包围盒取景，3/4 视角 ----
lo = mathutils.Vector((1e9, 1e9, 1e9))
hi = mathutils.Vector((-1e9, -1e9, -1e9))
for o in model:
    if o.type != 'MESH':
        continue
    for c in o.bound_box:
        w = o.matrix_world @ mathutils.Vector(c)
        for i in range(3):
            lo[i] = min(lo[i], w[i])
            hi[i] = max(hi[i], w[i])
center = (lo + hi) * 0.5
radius = max(0.3, (hi - lo).length * 0.5)

cd = bpy.data.cameras.new("diag_cam")
cd.lens = 55
cam = bpy.data.objects.new("diag_cam", cd)
bpy.context.collection.objects.link(cam)
bpy.context.scene.camera = cam
direction = mathutils.Vector((1.0, 1.45, 0.62)).normalized()
dist = radius / math.tan(cd.angle * 0.5) * 1.12
cam.location = center + direction * dist
cam.rotation_euler = (-direction).to_track_quat('-Z', 'Y').to_euler()

# ---- 柔和三点光 ----
def _area(name, loc, rot, size, energy):
    ld = bpy.data.lights.new(name, type='AREA')
    ld.shape = 'RECTANGLE'
    ld.size, ld.size_y = size
    ld.energy = energy
    ob = bpy.data.objects.new(name, ld)
    bpy.context.collection.objects.link(ob)
    ob.location = loc
    ob.rotation_euler = rot


_area("diag_key", (2.6, 2.4, 3.0), (math.radians(42), 0, math.radians(47)),
      (3.2, 2.4), 900.0)
_area("diag_fill", (-2.8, 1.8, 1.6), (math.radians(72), 0, math.radians(-56)),
      (3.0, 2.6), 320.0)

world = bpy.context.scene.world
if world is None:
    world = bpy.data.worlds.new("diag_world")
    bpy.context.scene.world = world
world.use_nodes = True
bg = world.node_tree.nodes.get("Background")
bg.inputs[0].default_value = (0.20, 0.21, 0.24, 1.0)
bg.inputs[1].default_value = 1.0

sc = bpy.context.scene
engines = [i.identifier for i in
           bpy.types.RenderSettings.bl_rna.properties['engine'].enum_items]
sc.render.engine = 'BLENDER_EEVEE_NEXT' if 'BLENDER_EEVEE_NEXT' in engines \
    else 'BLENDER_EEVEE'
sc.render.resolution_x = 1280
sc.render.resolution_y = 960
sc.render.filepath = OUT
sc.render.image_settings.file_format = 'PNG'

bpy.ops.render.render(write_still=True)
print("COLOR_DIAG SAVED", OUT)
for i, (g, objs) in enumerate(sorted(GROUPS.items())):
    print("  %-16s n=%-3d color=%s" % (g, len(objs),
                                       tuple(round(v, 2) for v in PALETTE[i % len(PALETTE)])))

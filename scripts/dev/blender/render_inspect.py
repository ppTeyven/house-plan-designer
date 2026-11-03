"""专项验收渲染 —— 从多个角度检查沙发坐垫是否平、缝隙是否消除、有没有上色。

用法：
  blender --background --python render_inspect.py -- <glb> <outdir>

输出：
  inspect_front.png   正视图（看坐垫之间的缝、靠垫缝）
  inspect_top.png     俯视图（看坐面是否连续平整、有没有 3 个突起）
  inspect_3q.png      45° 视角（看整体造型、扶手、配色）
"""
import bpy
import os
import sys
import math
import mathutils

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import glb_clean

args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
GLB = args[0]
OUTDIR = args[1] if len(args) > 1 else os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "验收", "previews")
os.makedirs(OUTDIR, exist_ok=True)

bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)

model = glb_clean.import_clean(GLB)

# 归一化
mn = [1e9] * 3
mx = [-1e9] * 3
for o in model:
    if o.type != 'MESH':
        continue
    for c in o.bound_box:
        w = o.matrix_world @ mathutils.Vector(c)
        for i in range(3):
            mn[i] = min(mn[i], w[i])
            mx[i] = max(mx[i], w[i])
for o in model:
    if o.type == 'MESH':
        o.location.x -= (mn[0] + mx[0]) / 2
        o.location.y -= (mn[1] + mx[1]) / 2
        o.location.z -= mn[2]

W = mx[0] - mn[0]
D = mx[1] - mn[1]
H = mx[2] - mn[2]
print("MODEL bbox W=%.3f D=%.3f H=%.3f" % (W, D, H))

# ---- 地面 ----
bpy.ops.mesh.primitive_plane_add(size=40, location=(0, 0, 0))
g = bpy.context.active_object
gm = bpy.data.materials.new("ground")
gm.use_nodes = True
bsdf = gm.node_tree.nodes.get("Principled BSDF")
bsdf.inputs["Base Color"].default_value = (0.028, 0.030, 0.034, 1)
bsdf.inputs["Roughness"].default_value = 0.70
g.data.materials.append(gm)

# ---- 世界 ----
world = bpy.data.worlds[0] if bpy.data.worlds else bpy.data.worlds.new("W")
bpy.context.scene.world = world
world.use_nodes = True
bg = world.node_tree.nodes.get("Background")
bg.inputs["Color"].default_value = (0.05, 0.055, 0.065, 1)
bg.inputs["Strength"].default_value = 0.55

# ---- 灯光：三点布光 + 柔和顶光（让布料质感出来）----
def add_area(name, loc, rot, size, energy, color=(1, 1, 1)):
    ld = bpy.data.lights.new(name, 'AREA')
    ld.energy = energy
    ld.size = size
    ld.color = color
    ob = bpy.data.objects.new(name, ld)
    bpy.context.collection.objects.link(ob)
    ob.location = loc
    ob.rotation_euler = rot
    return ob

add_area("key", (2.2, -2.6, 2.6), (math.radians(52), 0, math.radians(140)),
         2.4, 420)
add_area("fill", (-2.8, -2.2, 1.5), (math.radians(72), 0, math.radians(-125)),
         3.0, 140, (0.92, 0.95, 1.0))
add_area("rim", (-1.2, 3.2, 2.0), (math.radians(115), 0, math.radians(200)),
         2.0, 260, (1.0, 0.94, 0.86))
add_area("top", (0, -0.4, 3.4), (0, 0, 0), 3.6, 180)

# ---- 相机 ----
cam_data = bpy.data.cameras.new("cam")
cam = bpy.data.objects.new("cam", cam_data)
bpy.context.collection.objects.link(cam)
bpy.context.scene.camera = cam
cam_data.lens = 70

sc = bpy.context.scene
sc.render.engine = 'BLENDER_EEVEE_NEXT'
sc.render.resolution_x = 1400
sc.render.resolution_y = 900
sc.render.film_transparent = False
try:
    sc.eevee.use_raytracing = True
    sc.eevee.taa_render_samples = 96
except Exception:
    pass
try:
    sc.view_settings.view_transform = 'AgX'
    sc.view_settings.look = 'AgX - Medium Contrast'
except Exception:
    pass


def aim(target):
    d = (mathutils.Vector(target) - cam.location)
    cam.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()


def shoot(name, loc, target, lens=70):
    cam.location = loc
    cam_data.lens = lens
    aim(target)
    sc.render.filepath = os.path.join(OUTDIR, name)
    bpy.ops.render.render(write_still=True)
    print("saved", name)


cy = 0.0
# 正面：沙发正面朝 +Y（相机在 +Y 侧）
shoot("inspect_front.png", (0, D * 2.3, H * 0.62), (0, 0, H * 0.42), 62)
# 俯视：正上方，略微前倾，看坐面连续性
shoot("inspect_top.png", (0, -D * 0.35, D * 3.4), (0, 0, H * 0.35), 58)
# 45°
shoot("inspect_3q.png", (W * 1.15, D * 1.55, H * 1.05), (0, 0, H * 0.40), 68)
# 坐垫特写（低角度平视，正面）—— 看坐面是否连续
shoot("inspect_seat.png", (0, D * 1.5, H * 0.44), (0, 0, H * 0.38), 85)

print("DONE")

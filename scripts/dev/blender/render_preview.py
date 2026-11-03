"""渲染验收站预览图：棚拍布光 + 环境，直接给验收台用。
参数用环境变量传（Blender 的 -- 传参在部分版本里进不了 sys.argv）：
  BL_IN  = 输入 GLB 路径
  BL_OUT = 输出 PNG 路径
"""
import bpy, os, sys, math, mathutils

path = os.environ.get("BL_IN") or (sys.argv[sys.argv.index("--") + 1] if "--" in sys.argv else "")
out = os.environ.get("BL_OUT") or (sys.argv[sys.argv.index("--") + 2] if "--" in sys.argv and len(sys.argv) > sys.argv.index("--") + 2 else "")
if not path or not out:
    print("NEED_ARGS BL_IN/BL_OUT")
    raise SystemExit(1)

bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete(use_global=False)

bpy.ops.import_scene.gltf(filepath=path)

# 归一化：落地 + 居中
mn = [1e9] * 3; mx = [-1e9] * 3
for o in bpy.context.scene.objects:
    if o.type != 'MESH':
        continue
    for c in o.bound_box:
        w = o.matrix_world @ mathutils.Vector(c)
        for i in range(3):
            mn[i] = min(mn[i], w[i]); mx[i] = max(mx[i], w[i])
size = [mx[i] - mn[i] for i in range(3)]
cx = (mn[0] + mx[0]) / 2; cy = (mn[1] + mx[1]) / 2
for o in bpy.context.scene.objects:
    if o.type == 'MESH':
        o.location.x -= cx; o.location.y -= cy; o.location.z -= mn[2]

# 背景：深色棚拍背景（渐变球），避免画面整体被亮背景吃掉
bpy.ops.mesh.primitive_plane_add(size=40, location=(0, 0, 0))
g = bpy.context.active_object
gm = bpy.data.materials.new("ground"); gm.use_nodes = True
b = gm.node_tree.nodes.get("Principled BSDF")
b.inputs["Base Color"].default_value = (0.022, 0.026, 0.030, 1)
b.inputs["Roughness"].default_value = 0.62
g.data.materials.append(gm)

# 世界背景：深色（EEVEE 下世界色会整体提亮画面）
world = bpy.data.worlds[0] if bpy.data.worlds else bpy.data.worlds.new("W")
bpy.context.scene.world = world
world.use_nodes = True
bg = world.node_tree.nodes.get("Background")
bg.inputs["Color"].default_value = (0.012, 0.015, 0.020, 1)
bg.inputs["Strength"].default_value = 1.0

# 灯
def area(name, loc, energy, size, color=(1, 1, 1)):
    ld = bpy.data.lights.new(name, 'AREA')
    ld.energy = energy
    ld.shape = 'SQUARE'
    ld.size = size
    ld.color = color
    ld.normalize = True      # 按面积归一化，亮度可控
    ld.use_shadow = True
    ob = bpy.data.objects.new(name, ld)
    bpy.context.collection.objects.link(ob)
    ob.location = loc
    d = mathutils.Vector((0, 0, size * 0.45)) - ob.location
    ob.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
    return ob


# ================= 布光与相机 =================
# 关键设计：灯位固定在世界坐标的「绝对位置」（不随家具尺寸缩放），
# 功率固定。这样所有家具的照度天然一致，
# 只有相机距离/焦距随尺寸变化来取景 —— 避免大件全黑、小件过曝。
# （实测：按尺寸缩放灯距 + 功率补偿仍不一致，wardrobe mean=0.19 vs sofa 过曝 46%）
STUDIO_D = 4.2          # 棚拍距离基准（米）
STUDIO_H = 3.0          # 主灯高度


def aim(ob, target):
    ob.rotation_euler = (target - ob.location).to_track_quat('-Z', 'Y').to_euler()


def frame(cam_obj, lens, target, radius):
    """按包围球半径设定相机距离，保证整件家具都在画面内"""
    fov = 2 * math.atan(18.0 / lens)      # 18mm 半高传感器
    dist = radius / math.tan(fov / 2) * 1.18
    cam_obj.data.lens = lens
    aim(cam_obj, target)
    return dist



cz = size[2] / 2          # 归一化后底面贴地，中心高度即尺寸一半
center = mathutils.Vector((cx, cy, cz))
radius = max(size) * 0.62

# 灯（固定世界位置，固定功率）
area("key", (cx + 2.6, cy - 3.0, cz + 2.4), 190, 2.6, (1.0, 0.985, 0.96))
area("fill", (cx - 3.2, cy - 1.6, cz + 1.2), 80, 3.0, (0.90, 0.94, 1.0))
area("rim", (cx + 0.6, cy + 3.4, cz + 2.0), 130, 2.4, (1.0, 0.99, 0.97))
area("top", (cx, cy, cz + 3.4), 90, 3.4, (1.0, 1.0, 1.0))

# 相机
cam_d = bpy.data.cameras.new("cam")
cam = bpy.data.objects.new("cam", cam_d)
bpy.context.collection.objects.link(cam)
bpy.context.scene.camera = cam

VIEW = os.environ.get("BL_VIEW", "studio")
if VIEW == "front":
    cam.data.lens = 60
    d = radius / math.tan(2 * math.atan(18.0 / 60) / 2) * 1.12
    cam.location = center + mathutils.Vector((0, -d, 0))
    aim(cam, center)
elif VIEW == "side":
    cam.data.lens = 60
    d = radius / math.tan(2 * math.atan(18.0 / 60) / 2) * 1.12
    cam.location = center + mathutils.Vector((d, 0, 0))
    aim(cam, center)
elif VIEW == "top":
    cam.data.lens = 55
    d = radius / math.tan(2 * math.atan(18.0 / 55) / 2) * 1.12
    cam.location = center + mathutils.Vector((0.001, 0, d))
    aim(cam, center)
elif VIEW == "detail":
    # 细节特写：靠近前沿，看滚边/针脚/拼缝
    lens = 85
    cam.data.lens = lens
    target = mathutils.Vector((cx, cy - size[1] * 0.42, cz + size[2] * 0.10))
    cam.location = target + mathutils.Vector((size[0] * 0.14, -radius * 1.9, size[2] * 0.34))
    aim(cam, target)
else:  # studio 三分之四
    lens = 55
    cam.data.lens = lens
    d = radius / math.tan(2 * math.atan(18.0 / lens) / 2) * 1.15
    cam.location = center + mathutils.Vector((d * 0.62, -d * 0.80, d * 0.42))
    aim(cam, center)

sc = bpy.context.scene
try:
    sc.render.engine = 'BLENDER_EEVEE_NEXT'
    sc.eevee.taa_render_samples = 64
    sc.eevee.use_raytracing = True
except Exception:
    sc.render.engine = 'BLENDER_EEVEE'
sc.render.resolution_x = 1280
sc.render.resolution_y = 960
sc.render.film_transparent = False
sc.render.image_settings.file_format = 'PNG'
sc.render.filepath = out
try:
    # Standard 保留材质本来的饱和度（AgX 会把抱枕的橙/蓝压成灰）
    sc.view_settings.view_transform = 'Standard'
except Exception:
    pass
sc.view_settings.look = 'None'
sc.view_settings.exposure = 0.05
sc.view_settings.gamma = 1.0
bpy.ops.render.render(write_still=True)
print("RENDERED", out, "size=", [round(v, 3) for v in size])
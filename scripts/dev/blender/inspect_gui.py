"""打开 GLB 到 GUI Blender，并配置成【可审阅】的视图。

【为什么需要】
  用户要求"我需要能实时观测你建模的过程，你看到的我也要看到"。
  纯后台渲染 + 截图的流程里，用户看不到过程，
  且我与用户看到的画面可能不一致（视口 vs 渲染图），
  导致"我以为好了，用户看到的是另一个东西"。

  这个脚本：
    1. 打开 GUI Blender
    2. 导入 GLB
    3. 视口设成【实体着色 + X-Ray 半透明】，能直接看穿软包看到内部结构
    4. 布好三点光 + 相机
    5. 保持窗口打开，用户可自由旋转/缩放

用法：
  blender --python inspect_gui.py -- <glb>
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

# ---- 清场 ----
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
for o in list(bpy.data.objects):
    if o.type in ('LIGHT', 'CAMERA'):
        bpy.data.objects.remove(o, do_unlink=True)

# 【v19】导入后清掉 Blender 默认 Cube —— 它会罩住整个模型
model = glb_clean.import_clean(GLB)
glb_clean.normalize_floor(model)
bpy.context.view_layer.update()

# ---- 包围盒 ----
lo = mathutils.Vector((1e9, 1e9, 1e9))
hi = mathutils.Vector((-1e9, -1e9, -1e9))
for o in bpy.context.scene.objects:
    if o.type != 'MESH':
        continue
    for c in o.bound_box:
        w = o.matrix_world @ mathutils.Vector(c)
        for i in range(3):
            lo[i] = min(lo[i], w[i])
            hi[i] = max(hi[i], w[i])
center = (lo + hi) * 0.5
radius = max(0.3, (hi - lo).length * 0.5)

# ---- 相机 ----
cd = bpy.data.cameras.new("insp_cam")
cd.lens = 55
cam = bpy.data.objects.new("insp_cam", cd)
bpy.context.collection.objects.link(cam)
bpy.context.scene.camera = cam
direction = mathutils.Vector((1.0, 1.45, 0.62)).normalized()
dist = radius / math.tan(cd.angle * 0.5) * 1.12
cam.location = center + direction * dist
cam.rotation_euler = (-direction).to_track_quat('-Z', 'Y').to_euler()

# ---- 三点光（用 aim 明确指向，避免照错方向）----
def _area(name, loc, size, energy, aim=(0, 0, 0.45)):
    ld = bpy.data.lights.new(name, type='AREA')
    ld.shape = 'RECTANGLE'
    ld.size, ld.size_y = size
    ld.energy = energy
    ob = bpy.data.objects.new(name, ld)
    bpy.context.collection.objects.link(ob)
    ob.location = loc
    d = mathutils.Vector(aim) - mathutils.Vector(loc)
    ob.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()


_area("insp_key", (2.8, 2.6, 3.2), (3.4, 2.6), 1400)
_area("insp_fill", (-3.0, 2.2, 1.8), (3.2, 2.8), 520)
_area("insp_rim", (-1.4, -3.2, 2.8), (2.6, 2.2), 700)

world = bpy.context.scene.world
if world is None:
    world = bpy.data.worlds.new("insp_world")
    bpy.context.scene.world = world
world.use_nodes = True
bg = world.node_tree.nodes.get("Background")
bg.inputs[0].default_value = (0.18, 0.19, 0.21, 1.0)
bg.inputs[1].default_value = 1.0

# ---- 视口 ----
# 【v19】不用相机视角 —— 实测 view_camera() 在 GUI 启动脚本里经常不生效，
# 视口停在默认视角，模型缩成一小团（用户完全看不到）。
# 改用【view_axis + view_orbit + view_all】：确定性最高。
XRAY = os.environ.get("BL_XRAY", "0") == "1"
for win in bpy.context.window_manager.windows:
    for area in win.screen.areas:
        if area.type != 'VIEW_3D':
            continue
        sp = area.spaces.active
        sp.shading.type = 'MATERIAL'
        sp.shading.use_scene_lights = True
        sp.shading.use_scene_world = True
        sp.shading.show_xray = XRAY
        sp.shading.xray_alpha = 0.42
        sp.overlay.show_overlays = False
        sp.region_3d.view_perspective = 'PERSP'
        for region in area.regions:
            if region.type == 'WINDOW':
                with bpy.context.temp_override(window=win, area=area,
                                             region=region):
                    try:
                        # 从【正前方 +Y】看，再绕 Z 转 -55°、绕 X 俯 26°
                        bpy.ops.view3d.view_axis(type='FRONT')
                        bpy.ops.view3d.view_orbit(
                            angle=math.radians(-55.0), type='ORBITRIGHT')
                        bpy.ops.view3d.view_orbit(
                            angle=math.radians(26.0), type='ORBITDOWN')
                        bpy.ops.view3d.view_all()
                        bpy.ops.view3d.zoom(delta=-1)
                    except Exception as e:
                        print("[inspect_gui] view warn:", e)
                break
        break
    break

# ---- 最大化窗口（用户要能看清）----
try:
    import ctypes
    ctypes.windll.user32.ShowWindow(
        ctypes.windll.user32.GetForegroundWindow(), 3)
except Exception:
    pass

for area in bpy.context.screen.areas:
    area.tag_redraw()

print("INSPECT_GUI READY", GLB, "xray=", XRAY,
      "center=", tuple(round(v, 3) for v in center))

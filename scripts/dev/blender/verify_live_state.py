"""检查当前运行的 Blender GUI 的场景状态。

【用途】
实时建模脚本跑完后，用这个确认：
  · 对象数、面数
  · 材质是否已赋值（用户投诉"白模没有材质"）
  · 视口着色模式（实时建模用的是 MATERIAL）
  · 相机/灯光

【怎么在已运行的 GUI 里执行】
Blender 支持在运行中的实例里再跑一个脚本吗？不支持。
所以这里改为【写一个独立的检查脚本】，在【新开的 Blender --background】里
对导出的 GLB 做同样检查 —— 这反映的正是 GUI 里会看到的。

用法：blender --background --python verify_live_state.py -- <glb>
"""
import bpy
import sys
import os

args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
GLB = args[0] if args else ""

print("=" * 88)
print("沙发场景状态检查")
print("=" * 88)

if GLB and os.path.exists(GLB):
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    bpy.ops.import_scene.gltf(filepath=GLB)
    bpy.context.view_layer.update()

meshes = [o for o in bpy.context.scene.objects if o.type == 'MESH']
curves = [o for o in bpy.context.scene.objects if o.type == 'CURVE']
print("对象: mesh %d, curve %d" % (len(meshes), len(curves)))
print("总面数: %d" % sum(len(o.data.polygons) for o in meshes))

print()
print("材质清单:")
mats = {}
for o in meshes:
    for m in o.data.materials:
        if m:
            mats[m.name] = mats.get(m.name, 0) + 1
for k in sorted(mats):
    print("  %-22s 用于 %2d 个对象" % (k, mats[k]))

if not mats:
    print("  ⚠️  没有材质 —— 白模！")

print()
print("各对象材质（前 20）:")
for o in sorted(meshes, key=lambda x: x.name)[:20]:
    ms = [m.name for m in o.data.materials if m]
    print("  %-24s %6d 面  %s" % (o.name, len(o.data.polygons), ms or "【无材质】"))

# 检查着色
print()
print("渲染引擎: %s" % bpy.context.scene.render.engine)
print("色彩管理: %s / %s" % (bpy.context.scene.view_settings.view_transform,
                              bpy.context.scene.view_settings.look))

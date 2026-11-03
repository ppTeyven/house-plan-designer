"""查询当前 Blender GUI 的场景状态 —— 验证实时建模进度与材质。

通过 MCP addon 不可用时，直接用 GUI 进程检查不方便。
本脚本改用：读取 Blender 的 autosave / 查询当前场景。

【实际用途】
在 GUI 里执行时打印当前场景对象数、材质、视口着色模式。
用法：blender --background --python probe_scene.py
"""
import bpy
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("=" * 80)
print("场景状态")
print("=" * 80)
print("对象数:", len(bpy.context.scene.objects))
meshes = [o for o in bpy.context.scene.objects if o.type == 'MESH']
curves = [o for o in bpy.context.scene.objects if o.type == 'CURVE']
print("  mesh: %d   curve: %d" % (len(meshes), len(curves)))
print("  总面数:", sum(len(o.data.polygons) for o in meshes))

mats = {}
for o in meshes:
    for m in o.data.materials:
        if m:
            mats[m.name] = mats.get(m.name, 0) + 1
print("  材质:", mats if mats else "（无）")

print()
print("  对象列表:")
for o in sorted(bpy.context.scene.objects, key=lambda x: x.name):
    if o.type == 'MESH':
        print("    %-24s 面 %6d  材质 %s" %
              (o.name, len(o.data.polygons),
               [m.name for m in o.data.materials if m]))

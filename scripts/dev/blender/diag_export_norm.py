"""决定性测试 —— pipe_mesh 的法线在【导出 GLB】时是否被破坏。

【关键现象】
内存里 pipe_mesh：法线反向(dot<0) = 0  ✔
导出 GLB 后：法线反向 = 10250  ✘

两个嫌疑人：
  ① glTF 导出器（三角化/拆分顶点时改了绕序）
  ② 我加在 export() 里的 fix_all_normals（阈值改成 -0.85 后翻转了 6620 个面，
     很可能把原本正确的面翻转坏了）

【测试矩阵】
  A. pipe_mesh → 内存检查 → 导出 → 导入检查
  B. 同上，但导出【前】手动跑 fix_all_normals
  C. 同上，但导出【前】跳过 fix_all_normals（临时改 export 行为）

【判据】每一步的法线反向数

用法：blender --background --python diag_export_norm.py
"""
import bpy
import sys
import os
import math
import bmesh
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bl_lib as B


def rev_count(objs):
    n = 0
    for o in objs:
        bm = bmesh.new()
        bm.from_mesh(o.data)
        bm.normal_update()
        for e in bm.edges:
            if len(e.link_faces) == 2:
                if e.link_faces[0].normal.dot(e.link_faces[1].normal) < -0.85:
                    n += 1
        bm.free()
    return n


def face_rev(ob):
    """面级：法线朝内的面（相对轴心）"""
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bm.normal_update()
    return len(bm.faces)


tmp = os.path.join(tempfile.gettempdir(), "pn.glb")

print("=" * 92)
print("pipe_mesh 导出法线完整性测试")
print("=" * 92)

# ---- A. 纯导出（不跑 fix_all_normals）----
B.wipe()
pts = [(0.3 * math.cos(a), 0.3 * math.sin(a), 0)
       for a in [i * math.pi / 8 for i in range(16)]]
ob = B.pipe_mesh("p", pts, None, r=0.0055, closed=True, sides=20)
print("A. 内存: 面 %d  反向 %d" % (len(ob.data.polygons), rev_count([ob])))

# 手动导出（不走 B.export，避免触发 fix_all_normals）
bpy.ops.object.select_all(action='SELECT')
bpy.ops.export_scene.gltf(filepath=tmp, export_format='GLB',
                          export_materials='EXPORT', use_selection=True,
                          export_apply=True)

bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
bpy.ops.import_scene.gltf(filepath=tmp)
bpy.context.view_layer.update()
objs = [o for o in bpy.context.scene.objects if o.type == 'MESH' and o.data.polygons]
print("   导出后: 面 %d  反向 %d" %
      (sum(len(o.data.polygons) for o in objs), rev_count(objs)))

# ---- B. 跑 fix_all_normals 后再导出 ----
B.wipe()
pts2 = [(0.3 * math.cos(a), 0.3 * math.sin(a), 0)
        for a in [i * math.pi / 8 for i in range(16)]]
ob2 = B.pipe_mesh("p", pts2, None, r=0.0055, closed=True, sides=20)
print()
print("B. 内存(修前): 反向 %d" % rev_count([ob2]))
B.fix_all_normals([ob2])
print("   内存(修后): 反向 %d" % rev_count([ob2]))

bpy.ops.object.select_all(action='SELECT')
bpy.ops.export_scene.gltf(filepath=tmp, export_format='GLB',
                          export_materials='EXPORT', use_selection=True,
                          export_apply=True)
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
bpy.ops.import_scene.gltf(filepath=tmp)
bpy.context.view_layer.update()
objs = [o for o in bpy.context.scene.objects if o.type == 'MESH' and o.data.polygons]
print("   导出后: 反向 %d" % rev_count(objs))

print()
print("判读：")
print("  A 的导出后反向 > 0  → glTF 导出器破坏了绕序")
print("  A=0 但 B>0          → fix_all_normals 破坏了原本正确的面")
print("  A=0 且 B=0          → 导出无问题，问题在别处")

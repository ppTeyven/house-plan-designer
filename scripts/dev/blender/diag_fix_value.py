"""决定性对比 —— fix_all_normals 到底是在帮忙还是在破坏？

【背景】
经过多轮修复，沙发导出后仍有 1108~1273 处法线反向。
修复过程却"翻转了 5923 个面"—— 这个数字远大于冲突数，
强烈暗示 BFS 在【反复翻转同一区域】（震荡），修完还是坏。

【实验】
  A. 完整流程（含 fix_all_normals）→ 导出 → 检测
  B. 完全跳过 fix_all_normals       → 导出 → 检测

【判据】谁的反向数更少

用法：blender --background --python diag_fix_value.py
"""
import bpy
import sys
import os
import math
import bmesh
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bl_lib as B

tmp = os.path.join(tempfile.gettempdir(), "fv.glb")


def rev_count(objs):
    n = 0
    per = {}
    for o in objs:
        c = 0
        bm = bmesh.new()
        bm.from_mesh(o.data)
        bm.normal_update()
        for e in bm.edges:
            if len(e.link_faces) == 2:
                if e.link_faces[0].normal.dot(e.link_faces[1].normal) < -0.85:
                    c += 1
        bm.free()
        per[o.name] = c
        n += c
    return n, per


def export_and_check(tag):
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.export_scene.gltf(filepath=tmp, export_format='GLB',
                              export_materials='EXPORT', use_selection=True,
                              export_apply=True)
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    bpy.ops.import_scene.gltf(filepath=tmp)
    bpy.context.view_layer.update()
    objs = [o for o in bpy.context.scene.objects
            if o.type == 'MESH' and o.data.polygons]
    n, per = rev_count(objs)
    print("  %s 导出后反向总数 %d" % (tag, n))
    worst = sorted(per.items(), key=lambda kv: -kv[1])[:8]
    for k, v in worst:
        if v:
            print("      %-24s %d" % (k, v))
    return n


print("=" * 88)
print("fix_all_normals 的价值对比")
print("=" * 88)

# ---------- A. 含 fix_all_normals ----------
B.wipe()
cush = B.soft_slab("cush", (0.589, 0.52, 0.14), (0, 0, 0.35), res_u=96, res_v=40)
shell = B.soft_slab("shell", (2.0, 0.9, 0.6), (0, 0, 0.3), res_u=64, res_v=32)
import mathutils
pts = []
for i in range(89):
    a = 2 * math.pi * i / 88
    cs, sn = math.cos(a), math.sin(a)
    px = (0.589 / 2 - 0.016) * math.copysign(abs(cs) ** 0.62, cs)
    py = (0.52 / 2 - 0.016) * math.copysign(abs(sn) ** 0.62, sn)
    pts.append((px, py, 0.401))
pipe = B.pipe_on_surface("pipe", pts, cush, None, r=0.010, lift=0.0036)
bpy.context.view_layer.update()

objs = [o for o in bpy.context.scene.objects if o.type == 'MESH']
n_mem, _ = rev_count(objs)
print("\nA. 修复前（内存）: 反向 %d" % n_mem)
B.fix_all_normals(objs)
objs = [o for o in bpy.context.scene.objects if o.type == 'MESH']
n_mem2, _ = rev_count(objs)
print("   修复后（内存）: 反向 %d" % n_mem2)
export_and_check("A")

# ---------- B. 跳过 fix_all_normals ----------
B.wipe()
cush = B.soft_slab("cush", (0.589, 0.52, 0.14), (0, 0, 0.35), res_u=96, res_v=40)
shell = B.soft_slab("shell", (2.0, 0.9, 0.6), (0, 0, 0.3), res_u=64, res_v=32)
pts = []
for i in range(89):
    a = 2 * math.pi * i / 88
    cs, sn = math.cos(a), math.sin(a)
    px = (0.589 / 2 - 0.016) * math.copysign(abs(cs) ** 0.62, cs)
    py = (0.52 / 2 - 0.016) * math.copysign(abs(sn) ** 0.62, sn)
    pts.append((px, py, 0.401))
pipe = B.pipe_on_surface("pipe", pts, cush, None, r=0.010, lift=0.0036)
bpy.context.view_layer.update()
objs = [o for o in bpy.context.scene.objects if o.type == 'MESH']
n_mem3, _ = rev_count(objs)
print("\nB. 未修复（内存）: 反向 %d" % n_mem3)
export_and_check("B")

print()
print("判读：若 B 明显优于 A → fix_all_normals 有害，应移除或改判据")

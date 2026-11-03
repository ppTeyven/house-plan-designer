"""管件法线修复 —— 验证"按连通分量 recalc"能否清零剩余 373 处。

【背景】
BFS 二染色把硬棱 797 → 373，剩余全在滚边管件上。
原因：三角形管的接缝形成【奇环】（三个面两两矛盾），
BFS 二染色在奇环处无法收敛（会有一处永远矛盾）。

【候选方案】
  A. 现状（BFS 二染色）                      → 373
  B. 逐【连通分量】做 recalc_face_normals
     —— recalc 是按分量整体重算，对奇环天然健壮（不要求二染色）
  C. BFS + 逐分量 recalc
  D. BFS + 逐分量 recalc + 再次 BFS（收敛）

【判据】硬棱数（dot < -0.985 的相邻边）+ 耗时

用法：blender --background --python test_pipe_normals.py -- <glb>
"""
import bpy
import sys
import os
import time
import bmesh

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bl_lib as B

args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
GLB = args[0]


def load():
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    bpy.ops.import_scene.gltf(filepath=GLB)
    bpy.context.view_layer.update()
    return [o for o in bpy.context.scene.objects if o.type == 'MESH' and o.data.polygons]


def count_rev(objs):
    n = 0
    for o in objs:
        bm = bmesh.new()
        bm.from_mesh(o.data)
        bm.normal_update()
        for e in bm.edges:
            if len(e.link_faces) == 2:
                if e.link_faces[0].normal.dot(e.link_faces[1].normal) < -0.985:
                    n += 1
        bm.free()
    return n


def recalc_per_component(ob):
    """把网格拆成连通分量，逐个 recalc_face_normals。
    Blender 的 recalc 对每个【独立连通分量】整体定向，
    对奇环健壮（不要求二染色可解）。"""
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bm.normal_update()

    # 用 bm 自己的连通分量划分
    seen = set()
    groups = []
    for f in bm.faces:
        if f.index in seen:
            continue
        # BFS 收集连通的面
        comp = []
        stack = [f]
        seen.add(f.index)
        while stack:
            cur = stack.pop()
            comp.append(cur)
            for e in cur.edges:
                for nf in e.link_faces:
                    if nf.index not in seen:
                        seen.add(nf.index)
                        stack.append(nf)
        groups.append(comp)

    for comp in groups:
        if len(comp) < 2:
            continue
        bmesh.ops.recalc_face_normals(bm, faces=comp)
    bm.to_mesh(ob.data)
    ob.data.update()
    bm.free()
    return len(groups)


print("=" * 84)
print("管件法线修复方案对比")
print("=" * 84)

t0 = time.time()
objs = load()
print("baseline           硬棱 %5d  (%.1fs)" % (count_rev(objs), time.time() - t0))

t0 = time.time()
objs = load()
B.fix_all_normals(objs)
print("A. BFS 二染色      硬棱 %5d  (%.1fs)" % (count_rev(objs), time.time() - t0))

t0 = time.time()
objs = load()
for o in objs:
    recalc_per_component(o)
print("B. 逐分量 recalc   硬棱 %5d  (%.1fs)" % (count_rev(objs), time.time() - t0))

t0 = time.time()
objs = load()
B.fix_all_normals(objs)
for o in objs:
    recalc_per_component(o)
print("C. BFS→分量recalc  硬棱 %5d  (%.1fs)" % (count_rev(objs), time.time() - t0))

t0 = time.time()
objs = load()
B.fix_all_normals(objs)
for o in objs:
    recalc_per_component(o)
B.fix_all_normals(objs)
print("D. BFS→recalc→BFS  硬棱 %5d  (%.1fs)" % (count_rev(objs), time.time() - t0))

t0 = time.time()
objs = load()
for o in objs:
    recalc_per_component(o)
B.fix_all_normals(objs)
print("E. 分量recalc→BFS  硬棱 %5d  (%.1fs)" % (count_rev(objs), time.time() - t0))

"""定位 BFS 修复为何不彻底 —— 逐步拆解每个环节的影响。

【假设】
fix_inconsistent_normals 的第④步"整体朝外（按有向体积/参考面）"
可能把 BFS 刚修好的朝向又整体翻转回去。
（对比实验已证实：recalc_face_normals 会把 412 撤销回 1088）

【本脚本】
逐步施加各环节，每步测硬棱数：
  0. baseline
  1. + recalc_face_normals
  2. + BFS 连通分量定向（不翻转）
  3. + 少数派翻转
  4. + 整体朝外（参考面）
  5. + 整体朝外（有向体积）

另外对比两种 BFS 邻接定义：
  · 仅用硬矛盾边建图（当前实现）
  · 用【全部共享边】建图做二染色（更稳，能处理奇环）

用法：blender --background --python diag_bfs_steps.py -- <glb>
"""
import bpy
import sys
import os
import math
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


def bfs_component(ob, use_all_edges):
    """对单个物体做 BFS 定向 + 少数派翻转。
    use_all_edges=True → 用全部共享边建图（能处理奇环）
    """
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bm.normal_update()
    bm.faces.ensure_lookup_table()

    adj = {f.index: [] for f in bm.faces}
    for e in bm.edges:
        if len(e.link_faces) != 2:
            continue
        a, b = e.link_faces[0].index, e.link_faces[1].index
        d = bm.faces[a].normal.dot(bm.faces[b].normal)
        if use_all_edges or d < -0.985:
            adj[a].append(b)
            adj[b].append(a)

    sign = {}
    flips = set()
    for seed in bm.faces:
        if seed.index in sign:
            continue
        sign[seed.index] = 1
        stack = [seed.index]
        comp = []
        while stack:
            fi = stack.pop()
            comp.append(fi)
            for fj in adj[fi]:
                if fj not in sign:
                    sign[fj] = -sign[fi]
                    stack.append(fj)
        pos = sum(1 for i in comp if sign[i] > 0)
        neg = len(comp) - pos
        if neg > pos:
            flips.update(i for i in comp if sign[i] > 0)
        else:
            flips.update(i for i in comp if sign[i] < 0)

    if flips:
        bmesh.ops.reverse_faces(bm, faces=[bm.faces[i] for i in flips])
        bm.to_mesh(ob.data)
        ob.data.update()
    bm.free()
    return len(flips)


print("=" * 80)
print("BFS 修复环节拆解")
print("=" * 80)

for tag, use_all in (("仅硬矛盾边建图", False), ("全部共享边建图", True)):
    print("\n### 邻接定义：%s" % tag)
    objs = load()
    print("  0. baseline            硬棱 %5d" % count_rev(objs))

    # 1. recalc
    for o in objs:
        bm = bmesh.new()
        bm.from_mesh(o.data)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        bm.to_mesh(o.data)
        o.data.update()
        bm.free()
    print("  1. + recalc            硬棱 %5d" % count_rev(objs))

    # 2+3. BFS
    nf = sum(bfs_component(o, use_all) for o in objs)
    print("  2+3. + BFS(翻转 %4d) 硬棱 %5d" % (nf, count_rev(objs)))

    # 4. 整体朝外（参考面）
    for o in objs:
        bm = bmesh.new()
        bm.from_mesh(o.data)
        bm.normal_update()
        if objs and o.data.vertices:
            far = max(o.data.vertices, key=lambda v: v.co.length)
            ref = None
            for f in bm.faces:
                if far in f.verts:
                    ref = f
                    break
            if ref:
                best, bestd = None, -1e9
                for f in bm.faces:
                    d = f.calc_center_median().dot(ref.normal)
                    if d > bestd:
                        bestd, best = d, f
                if best and best.normal.dot(ref.normal) < 0:
                    bmesh.ops.reverse_faces(bm, faces=bm.faces[:])
                    bm.to_mesh(o.data)
                    o.data.update()
        bm.free()
    print("  4. + 整体朝外(参考面) 硬棱 %5d" % count_rev(objs))

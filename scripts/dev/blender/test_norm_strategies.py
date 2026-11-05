"""对比三种法线修复策略 —— 找出对"曲线转网格的管件"最有效的一种。

【背景】
fix_inconsistent_normals（BFS 定向 + 少数派翻转）把硬棱从 1089 降到 412，
但没清零。剩下的 412 处几乎全在【曲线 bevel 转网格的管件】上
（seat_pipe / arm_pipe / pillow_pipe 等），特征是三角形、
法线与相邻面完全反向。

【要对比的策略】
  A. baseline            —— 不动
  B. recalc_face_normals —— Blender 内置：按连通分量重算法线
  C. BFS + recalc        —— 先局部修，再整体重算
  D. 自定义"投票 + 单面修复"

【判据】
· 硬棱数（dot < -0.985 的相邻边）
· 有向体积符号（>0 = 法线朝外）
· 面数变化（重算法线不应改变拓扑）

用法：blender --background --python test_norm_strategies.py -- <glb>
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


def measure(objs):
    rev = 0
    inward = 0
    for o in objs:
        bm = bmesh.new()
        bm.from_mesh(o.data)
        bm.normal_update()
        for e in bm.edges:
            if len(e.link_faces) == 2:
                if e.link_faces[0].normal.dot(e.link_faces[1].normal) < -0.985:
                    rev += 1
        v = bm.calc_volume(signed=True)
        if v < -1e-9:
            inward += 1
        bm.free()
    return rev, inward


def apply_recalc(objs):
    for o in objs:
        bm = bmesh.new()
        bm.from_mesh(o.data)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        bm.to_mesh(o.data)
        o.data.update()
        bm.free()


def apply_vote(objs):
    """投票法：每个面看邻面多数派，少数派翻转。迭代到收敛。"""
    for o in objs:
        for _ in range(12):
            bm = bmesh.new()
            bm.from_mesh(o.data)
            bm.normal_update()
            bm.faces.ensure_lookup_table()
            adj = {f.index: [] for f in bm.faces}
            for e in bm.edges:
                if len(e.link_faces) == 2:
                    adj[e.link_faces[0].index].append(e.link_faces[1].index)
                    adj[e.link_faces[1].index].append(e.link_faces[0].index)
            flips = []
            for f in bm.faces:
                nb = adj[f.index]
                if not nb:
                    continue
                agree = sum(1 for j in nb
                            if bm.faces[f.index].normal.dot(bm.faces[j].normal) > 0)
                dis = len(nb) - agree
                # 只有当"反向邻面"明显占少数时才翻转（保守）
                if dis > 0 and agree >= dis * 2:
                    flips.append(f)
            if not flips:
                bm.free()
                break
            bmesh.ops.reverse_faces(bm, faces=flips)
            bm.to_mesh(o.data)
            o.data.update()
            bm.free()


def report(tag, objs):
    rev, inward = measure(objs)
    print("  %-28s 硬棱 %5d   法线朝内件 %3d" % (tag, rev, inward))
    return rev, inward


print("=" * 78)
print("法线修复策略对比")
print("=" * 78)

# ---- A. baseline ----
objs = load()
print("\n[A] baseline")
report("不改", objs)

# ---- B. 仅 recalc ----
objs = load()
print("\n[B] recalc_face_normals")
apply_recalc(objs)
report("仅 recalc", objs)

# ---- C. BFS 修复 + recalc ----
objs = load()
print("\n[C] BFS(局部) + recalc(整体)")
B.fix_all_normals(objs)
report("BFS 后", objs)
apply_recalc(objs)
report("BFS + recalc 后", objs)

# ---- D. 投票法 ----
objs = load()
print("\n[D] 投票法（迭代）")
apply_vote(objs)
report("投票法后", objs)

# ---- E. 投票 + recalc ----
objs = load()
print("\n[E] 投票法 + recalc")
apply_vote(objs)
apply_recalc(objs)
report("投票 + recalc", objs)

# ---- F. BFS + 投票 + recalc ----
objs = load()
print("\n[F] BFS + 投票 + recalc")
B.fix_all_normals(objs)
apply_vote(objs)
apply_recalc(objs)
report("三者串联", objs)

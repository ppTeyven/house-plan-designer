"""决定性实验 —— 滚边管件残留硬棱：顶点合并能否解决？

【背景】
BFS 法线修复后：主体软包（坐垫/靠垫/扶手/抱枕）硬棱已清零 ✔
残留全在【滚边管件】（半径 5~10mm 的细管）上，394 处。

【怀疑】
Blender 的 curve bevel 转网格时，若路径上有【几乎重合但不精确重合】的点，
会生成【重合顶点 + 退化三角形】。
这些碎面是独立连通块，法线朝向互相矛盾 → BFS 修不干净（因为它们之间不共享边）。

【实验】
  A. 现状
  B. merge_by_distance(0.5mm) 后再 BFS
  C. merge_by_distance(0.05mm) 后再 BFS
  D. merge 后 + 删零面积面 + BFS

【判据】硬棱数 + 连通块数

用法：blender --background --python test_merge_normals.py -- <glb>
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


def count_parts(objs):
    """统计独立连通块数 —— 碎面数量的代理指标"""
    n = 0
    for o in objs:
        bm = bmesh.new()
        bm.from_mesh(o.data)
        seen = set()
        for f in bm.faces:
            if f.index in seen:
                continue
            n += 1
            stack = [f]
            seen.add(f.index)
            while stack:
                cur = stack.pop()
                for e in cur.edges:
                    for nf in e.link_faces:
                        if nf.index not in seen:
                            seen.add(nf.index)
                            stack.append(nf)
        bm.free()
    return n


def merge(objs, dist):
    for o in objs:
        bm = bmesh.new()
        bm.from_mesh(o.data)
        bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=dist)
        bm.to_mesh(o.data)
        o.data.update()
        bm.free()


def strip_degenerate(objs):
    for o in objs:
        bm = bmesh.new()
        bm.from_mesh(o.data)
        deg = [f for f in bm.faces if f.calc_area() < 1e-9]
        if deg:
            bmesh.ops.delete(bm, geom=deg, context='FACES_ONLY')
            bm.to_mesh(o.data)
            o.data.update()
        bm.free()


print("=" * 88)
print("滚边管件硬棱：顶点合并实验")
print("=" * 88)

objs = load()
print("baseline       硬棱 %5d  连通块 %6d" % (count_rev(objs), count_parts(objs)))

objs = load()
B.fix_all_normals(objs)
print("A. BFS         硬棱 %5d  连通块 %6d" % (count_rev(objs), count_parts(objs)))

for dist in (0.0005, 0.00005):
    objs = load()
    merge(objs, dist)
    B.fix_all_normals(objs)
    print("B. merge%.2fmm+BFS  硬棱 %5d  连通块 %6d"
          % (dist * 1000, count_rev(objs), count_parts(objs)))

objs = load()
merge(objs, 0.0005)
strip_degenerate(objs)
B.fix_all_normals(objs)
print("C. merge+删退化+BFS 硬棱 %5d  连通块 %6d"
      % (count_rev(objs), count_parts(objs)))

objs = load()
merge(objs, 0.0005)
B.fix_all_normals(objs)
strip_degenerate(objs)
B.fix_all_normals(objs)
print("D. merge+BFS+删+BFS 硬棱 %5d  连通块 %6d"
      % (count_rev(objs), count_parts(objs)))

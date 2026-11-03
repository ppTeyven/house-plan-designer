"""检查网格碎片 —— 18825 个独立连通块到底是什么？

【重大发现】
merge_by_distance(0.5mm) 把连通块从 18825 降到 369。
说明导出后的网格被切成了上万个碎片。

【怀疑】
① Blender 的 curve bevel + glTF 导出时，【自相交】的路径被切成碎片
② 顶点位置有微小差异（浮点精度），导致本应共享的顶点没合并
③ 材质/分组导致 exporter 分裂成多个 primitive

【检查】
对 seat_pipe_1（残留最多的件之一）：
  · 连通块的顶点数分布
  · 碎片之间的空间位置关系（是否互相重叠）
  · 碎片是否都贴在同一路径上
  · 检查是否有【完全重合的碎片】（同一段管子被导出两次）

用法：blender --background --python diag_fragments.py -- <glb> <obj>
"""
import bpy
import sys
import os
import math
import bmesh
from collections import Counter
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
GLB = args[0]
ONLY = args[1] if len(args) > 1 else None

bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
bpy.ops.import_scene.gltf(filepath=GLB)
bpy.context.view_layer.update()

print("=" * 96)
print("网格碎片分析")
print("=" * 96)

total_parts = 0
total_faces = 0
for o in sorted(bpy.context.scene.objects, key=lambda x: x.name):
    if o.type != 'MESH' or not o.data.polygons:
        continue

    bm = bmesh.new()
    bm.from_mesh(o.data)
    seen = set()
    parts = []
    for f in bm.faces:
        if f.index in seen:
            continue
        stack = [f]
        seen.add(f.index)
        comp = []
        while stack:
            cur = stack.pop()
            comp.append(cur)
            for e in cur.edges:
                for nf in e.link_faces:
                    if nf.index not in seen:
                        seen.add(nf.index)
                        stack.append(nf)
        parts.append(comp)

    total_parts += len(parts)
    total_faces += len(bm.faces)

    if len(parts) <= 2:
        bm.free()
        continue

    # 碎片规模分布
    sizes = Counter(len(c) for c in parts)
    # 碎片中心点分布（判断是否互相重叠）
    centers = []
    for c in parts:
        cen = sum((v.co for v in c[0].verts), Vector()) / len(c[0].verts)
        centers.append(cen)

    # 找【几乎重合】的碎片对
    dup_pairs = 0
    for i in range(len(centers)):
        for j in range(i + 1, len(centers)):
            if (centers[i] - centers[j]).length < 0.0005:
                dup_pairs += 1
                if dup_pairs > 5:
                    break
        if dup_pairs > 5:
            break

    print("\n### %-20s 碎片 %5d  面数 %6d  规模分布 %s  重合碎片对 %d"
          % (o.name, len(parts), len(bm.faces),
             dict(sorted(sizes.items())[:6]), dup_pairs))

    if ONLY and o.name == ONLY:
        # 打印前 5 个碎片的详情
        for idx, c in enumerate(parts[:5]):
            vs = set()
            for f in c:
                for v in f.verts:
                    vs.add(v)
            cen = sum((v.co for v in vs), Vector()) / len(vs)
            print("   碎片%d: 面 %3d 顶点 %3d 中心 (%.4f, %.4f, %.4f)"
                  % (idx, len(c), len(vs), cen.x, cen.y, cen.z))
    bm.free()

print()
print("总碎片数 %d / 总面数 %d" % (total_parts, total_faces))

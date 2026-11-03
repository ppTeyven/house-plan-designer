"""最终兜底 —— 射线一致性定向法（无歧义）。

【原理】
对每个连通分量：
  ① 从分量包围盒的【六个面】各取若干个朝外的射线
  ② 射线打向分量，命中【第一个】面
  ③ 若该面的法线与射线方向同向（dot > 0）→ 说明它朝外 ✔
     若反向 → 整个分量可能翻反了
  ④ 统计"朝外的命中面"比例 → 决定该分量是否需要整体翻转

【为什么可靠】
从一个外部点沿射线打进去，命中的第一个面一定是【朝外】的面
（否则射线会先穿过背面）。这与"离中心距离""有向体积"都不同 ——
对 U 形开口壳体这类几何依然有效（只要射线从实体外侧打进去）。

【用法】blender --background --python test_ray_fix.py -- <glb>
"""
import bpy
import sys
import os
import math
import bmesh
from mathutils import Vector

args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
GLB = args[0]

bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
bpy.ops.import_scene.gltf(filepath=GLB)
bpy.context.view_layer.update()


def count_rev(ob, thresh=-0.85):
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bm.normal_update()
    n = 0
    for e in bm.edges:
        if len(e.link_faces) == 2:
            if e.link_faces[0].normal.dot(e.link_faces[1].normal) < thresh:
                n += 1
    bm.free()
    return n


def ray_fix(ob, samples=7):
    """射线一致性定向：把明显翻反的连通分量整体翻正。
    返回 (翻转的面数, 处理的分量数)"""
    import mathutils
    from mathutils.bvhtree import BVHTree

    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bm.normal_update()
    bm.verts.ensure_lookup_table()
    bm.faces.ensure_lookup_table()

    # 连通分量（按顶点连通）
    seen_v = set()
    comps = []
    for v in bm.verts:
        if v.index in seen_v:
            continue
        stack = [v]
        seen_v.add(v.index)
        comp_v = []
        while stack:
            cur = stack.pop()
            comp_v.append(cur)
            for e in cur.link_edges:
                ov = e.other_vert(cur)
                if ov.index not in seen_v:
                    seen_v.add(ov.index)
                    stack.append(ov)
        comps.append(comp_v)

    flips = 0
    done = 0
    for comp_v in comps:
        if len(comp_v) < 4:
            continue
        # 该分量的面
        comp_faces = set()
        for v in comp_v:
            for f in v.link_faces:
                comp_faces.add(f.index)
        if len(comp_faces) < 2:
            continue

        # 单独建这个分量的 BVH
        sub = bmesh.new()
        for v in comp_v:
            sub.verts.new(v.co)
        sub.verts.ensure_lookup_table()
        remap = {}
        for i, v in enumerate(comp_v):
            remap[v.index] = sub.verts[i]
        for fi in comp_faces:
            f = bm.faces[fi]
            try:
                sub.faces.new([remap[v.index] for v in f.verts])
            except Exception:
                pass
        sub.faces.ensure_lookup_table()
        try:
            bvh = BVHTree.FromBMesh(sub)
        except Exception:
            sub.free()
            continue

        # 包围盒
        xs = [v.co for v in comp_v]
        mn = Vector((min(p.x for p in xs), min(p.y for p in xs),
                     min(p.z for p in xs)))
        mx = Vector((max(p.x for p in xs), max(p.y for p in xs),
                     max(p.z for p in xs)))
        ctr = (mn + mx) * 0.5
        half = (mx - mn) * 0.5
        span = max(half.x, half.y, half.z)
        if span < 1e-6:
            sub.free()
            continue

        out_cnt = 0
        in_cnt = 0
        for axis in range(3):
            for k in range(samples):
                # 在两个正交方向上取样
                if axis == 0:
                    o = Vector((ctr.x + half.x * 1.6,
                                ctr.y - half.y + (2 * half.y) * k / max(samples - 1, 1),
                                ctr.z - half.z + (2 * half.z) * k / max(samples - 1, 1)))
                    d = Vector((-1, 0, 0))
                elif axis == 1:
                    o = Vector((ctr.x - half.x + (2 * half.x) * k / max(samples - 1, 1),
                                ctr.y + half.y * 1.6,
                                ctr.z - half.z + (2 * half.z) * k / max(samples - 1, 1)))
                    d = Vector((0, -1, 0))
                else:
                    o = Vector((ctr.x - half.x + (2 * half.x) * k / max(samples - 1, 1),
                                ctr.y - half.y + (2 * half.y) * k / max(samples - 1, 1),
                                ctr.z + half.z * 1.6))
                    d = Vector((0, 0, -1))

                hit = bvh.ray_cast(o, d)
                if hit[0] is None:
                    continue
                loc, nor, idx, dist = hit
                if nor.dot(d) > 0:
                    out_cnt += 1
                else:
                    in_cnt += 1

        sub.free()

        if out_cnt + in_cnt < 4:
            continue
        done += 1
        # 多数命中面的法线【背对射线】 → 整个分量翻反了 → 翻转
        if in_cnt > out_cnt * 2:
            bmesh.ops.reverse_faces(bm, faces=[bm.faces[i] for i in comp_faces])
            flips += len(comp_faces)

    bm.to_mesh(ob.data)
    ob.data.update()
    bm.free()
    return flips, done


print("=" * 88)
print("射线一致性定向法")
print("=" * 88)

objs = [o for o in bpy.context.scene.objects if o.type == 'MESH' and o.data.polygons]
before = sum(count_rev(o) for o in objs)
print("修复前总反向: %d" % before)

for o in objs:
    f, d = ray_fix(o)
    if f:
        print("  %-24s 翻转 %d 面（%d 个分量）" % (o.name, f, d))

objs = [o for o in bpy.context.scene.objects if o.type == 'MESH' and o.data.polygons]
after = sum(count_rev(o) for o in objs)
print("修复后总反向: %d" % after)
print()
if after == 0:
    print("✅ 完全清零")
else:
    print("改善 %d 处" % (before - after))

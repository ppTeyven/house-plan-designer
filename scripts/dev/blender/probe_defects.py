"""定位两类具体缺陷的位置（不猜）：
  ① shell 的 230 条边界边（网格破洞）到底在哪
  ② shell ↔ arm_pad_L 的 11.9mm 穿模发生在哪里
  ③ back_stitch 是否埋在靠背板内部（不可见）还是浮在外面（穿模）

用法：blender --background --python probe_defects.py
"""
import bpy
import sys
import os
import math
import bmesh
import mathutils

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import make_sofa_v18 as MS   # noqa

print("=" * 90)
print("① shell 边界边定位")
print("=" * 90)
shell = bpy.data.objects.get("shell")
bm = bmesh.new()
bm.from_mesh(shell.data)
bm.edges.ensure_lookup_table()
bm.verts.ensure_lookup_table()

bnd = [e for e in bm.edges if len(e.link_faces) == 1]
print("边界边数:", len(bnd))
# 归类：按 z 高度分组
byz = {}
for e in bnd:
    z = (e.verts[0].co.z + e.verts[1].co.z) / 2
    k = round(z, 2)
    byz.setdefault(k, []).append(e)
print("\n按 z 分布:")
for k in sorted(byz):
    es = byz[k]
    xs = [(e.verts[0].co.x + e.verts[1].co.x) / 2 for e in es]
    ys = [(e.verts[0].co.y + e.verts[1].co.y) / 2 for e in es]
    print("  z=%-6.2f  n=%-4d  x[%7.3f..%7.3f] y[%7.3f..%7.3f]"
          % (k, len(es), min(xs), max(xs), min(ys), max(ys)))

# 打印前 12 条边
print("\n前 12 条边界边:")
for i, e in enumerate(bnd[:12]):
    a, b = e.verts[0].co, e.verts[1].co
    print("  %2d  (%.3f,%.3f,%.3f) - (%.3f,%.3f,%.3f)"
          % (i, a.x, a.y, a.z, b.x, b.y, b.z))
bm.free()

print()
print("=" * 90)
print("② shell ↔ arm_pad_L 穿模定位")
print("=" * 90)
from mathutils.bvhtree import BVHTree
arm = bpy.data.objects.get("arm_pad_L")
bmA = bmesh.new(); bmA.from_mesh(arm.data)
bvhA = BVHTree.FromBMesh(bmA); bmA.free()
bmS = bmesh.new(); bmS.from_mesh(shell.data)
bvhS = BVHTree.FromBMesh(bmS); bmS.free()

hits = []
for v in arm.data.vertices:
    p = arm.matrix_world @ v.co
    loc, nor, idx, dist = bvhS.find_nearest(p)
    if loc is None:
        continue
    n = shell.matrix_world.to_3x3() @ nor
    n.normalize()
    d = (p - loc).dot(n)
    if d < -0.002:
        hits.append((p.copy(), -d, loc.copy()))

print("穿入顶点:", len(hits))
if hits:
    hits.sort(key=lambda x: -x[1])
    print("最深 10 个:")
    for p, d, loc in hits[:10]:
        print("  顶点(%.3f,%.3f,%.3f)  穿入 %5.1f mm  最近面(%.3f,%.3f,%.3f)"
              % (p.x, p.y, p.z, d * 1000, loc.x, loc.y, loc.z))
    zs = [p.z for p, d, loc in hits]
    ys = [p.y for p, d, loc in hits]
    xs = [p.x for p, d, loc in hits]
    print("穿入区域: x[%.3f..%.3f] y[%.3f..%.3f] z[%.3f..%.3f]"
          % (min(xs), max(xs), min(ys), max(ys), min(zs), max(zs)))
    # 按 y 分桶
    print("按 y 分布(50mm 一桶):")
    buckets = {}
    for p, d, loc in hits:
        k = int(p.y * 20) / 20.0
        buckets.setdefault(k, []).append(d)
    for k in sorted(buckets):
        print("   y=%+.2f  n=%-4d 最深 %5.1f mm"
              % (k, len(buckets[k]), max(buckets[k]) * 1000))

print()
print("=" * 90)
print("③ back_stitch 是否埋在靠背板内")
print("=" * 90)
print("靠背板外壳: y 从 BACK_OUT=%.3f 到 BACK_IN=%.3f" % (MS.BACK_OUT, MS.BACK_IN))
bs = bpy.data.objects.get("back_stitch")
co = [v.co for v in bs.data.vertices]
print("back_stitch: y[%.3f..%.3f] z[%.3f..%.3f] x[%.3f..%.3f]"
      % (min(c.y for c in co), max(c.y for c in co),
         min(c.z for c in co), max(c.z for c in co),
         min(c.x for c in co), max(c.x for c in co)))
# 射线：从靠背正面(y=BACK_IN)往 -Y 打，看是否先命中 shell
import mathutils
hit_count = 0
inside = 0
for i in range(0, len(co), 37):
    p = co[i]
    origin = mathutils.Vector((p.x, MS.BACK_IN + 0.05, p.z))
    direction = mathutils.Vector((0, -1, 0))
    loc, nor, idx, dist = bvhS.ray_cast(origin, direction)
    if loc is not None:
        hit_count += 1
        # 命中点在 back_stitch 的 y 之前（更靠外）→ 说明线在壳体内部
        if loc.y > p.y + 0.001:
            inside += 1
print("采样 %d 点: 射线命中壳体 %d, 其中线在壳内(被遮挡) %d"
      % (len(co[::37]), hit_count, inside))
print("=" * 90)

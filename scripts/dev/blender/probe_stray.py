"""锁定用户截图中【穿过沙发的怪异线条】与【凹陷】的具体物体。

用户截图 2（原话）：
  "第二张图上方那个穿过沙发的线是什么，很怪而且这里像是凹进去了一样"

【排查思路】
 不猜。把所有细长/线状物体的包围盒、长度、走向全部列出来，
 跟沙发的关键高度（坐面 0.42 / 扶手段顶 0.505 / 扶手顶 0.62 / 靠背顶 0.82）
 对照，找出"横穿靠背上部"的那一条。

用法：blender --background --python probe_stray.py
"""
import bpy
import sys
import os
import math
import mathutils

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import make_sofa_v18 as MS   # noqa

print("=" * 100)
print("线状/细长物体排查")
print("=" * 100)

KEY_Z = [("坐面", 0.420), ("座板顶", 0.169), ("扶手段顶", 0.505),
         ("扶手顶", 0.620), ("靠背顶", 0.820)]

rows = []
for o in bpy.context.scene.objects:
    if o.type != 'MESH':
        continue
    bb = [o.matrix_world @ mathutils.Vector(c) for c in o.bound_box]
    mn = [min(p[i] for p in bb) for i in range(3)]
    mx = [max(p[i] for p in bb) for i in range(3)]
    size = [mx[i] - mn[i] for i in range(3)]
    diag = math.sqrt(sum(s * s for s in size))
    rows.append((o.name, mn, mx, size, diag, len(o.data.vertices)))

# 只看"线状"的：最长边 > 0.25m，且第二长边 < 0.05m
print("\n【线状物体】最长边>250mm 且 次长边<50mm")
print("%-24s %-26s %-26s %-22s" % ("名称", "min", "max", "尺寸mm"))
for name, mn, mx, size, diag, nv in rows:
    srt = sorted(size, reverse=True)
    if srt[0] > 0.25 and srt[1] < 0.05:
        print("%-24s (%6.3f,%6.3f,%6.3f)  (%6.3f,%6.3f,%6.3f)  %6.0f×%5.0f×%5.0f  v%d"
              % (name, mn[0], mn[1], mn[2], mx[0], mx[1], mx[2],
                 size[0] * 1000, size[1] * 1000, size[2] * 1000, nv))

print("\n【所有 z 范围跨越靠背区(0.55~0.80)的物体】")
for name, mn, mx, size, diag, nv in rows:
    if mn[2] < 0.78 and mx[2] > 0.56:
        print("  %-24s z[%.3f .. %.3f]  x[%.3f..%.3f] y[%.3f..%.3f]"
              % (name, mn[2], mx[2], mn[0], mx[0], mn[1], mx[1]))

print("\n【shell_shoulder_pipe 专项】")
for tag in ("L", "R"):
    n = "shell_shoulder_pipe_%s" % tag
    o = bpy.data.objects.get(n)
    if not o:
        print("  缺失", n)
        continue
    co = [v.co for v in o.data.vertices]
    mn = [min(c[i] for c in co) for i in range(3)]
    mx = [max(c[i] for c in co) for i in range(3)]
    # 中心线长度
    import bmesh
    bm = bmesh.new()
    bm.from_mesh(o.data)
    bm.verts.ensure_lookup_table()
    SIDES = 20
    nring = len(bm.verts) // SIDES
    cen = []
    for i in range(nring):
        vs = [bm.verts[i * SIDES + j] for j in range(SIDES)]
        cen.append(sum((v.co for v in vs), mathutils.Vector()) / SIDES)
    bm.free()
    L = sum((cen[i + 1] - cen[i]).length for i in range(len(cen) - 1))
    print("  %s: v%d 环%d  中心线长 %.1f mm" % (n, len(o.data.vertices), nring, L * 1000))
    print("      x[%.3f..%.3f] y[%.3f..%.3f] z[%.3f..%.3f]"
          % (mn[0], mx[0], mn[1], mx[1], mn[2], mx[2]))
    print("      前 8 个中心点:")
    for i in range(min(8, len(cen))):
        print("        %2d  (%.3f, %.3f, %.3f)" % (i, cen[i].x, cen[i].y, cen[i].z))
    print("      后 5 个中心点:")
    for i in range(max(0, len(cen) - 5), len(cen)):
        print("        %2d  (%.3f, %.3f, %.3f)" % (i, cen[i].x, cen[i].y, cen[i].z))

print("\n【back_stitch / arm_stitch 专项】")
for n in ("back_stitch", "arm_stitch_L", "arm_stitch_R", "seat_stitch_0"):
    o = bpy.data.objects.get(n)
    if not o:
        print("  缺失", n)
        continue
    bb = [o.matrix_world @ mathutils.Vector(c) for c in o.bound_box]
    mn = [min(p[i] for p in bb) for i in range(3)]
    mx = [max(p[i] for p in bb) for i in range(3)]
    print("  %-16s x[%.3f..%.3f] y[%.3f..%.3f] z[%.3f..%.3f]  v%d"
          % (n, mn[0], mx[0], mn[1], mx[1], mn[2], mx[2], len(o.data.vertices)))

print("\n【关键高度参照】")
for nm, z in KEY_Z:
    print("   %-8s z = %.3f" % (nm, z))
print("=" * 100)

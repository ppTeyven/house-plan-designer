"""定位 soft_slab 内部 482 处法线反向的确切位置与成因。

【已知】
seat_seam_0 / seat_seam_1 各有 ~482 处法线反向（占其边的 9.97%）。
这两个是 soft_slab 生成的软包条。

【要找】
反向边的位置分布（在网格的哪个区域）+ 相邻面夹角 + 边长
→ 判断是【底面封盖环序】、【顶面封盖环序】、还是【侧壁接缝】

用法：blender --background --python diag_seam_rev.py -- <glb>
"""
import bpy
import sys
import os
import math
import bmesh

args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
GLB = args[0]

bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
bpy.ops.import_scene.gltf(filepath=GLB)
bpy.context.view_layer.update()

for name in ("seat_seam_0", "shell"):
    ob = bpy.data.objects.get(name)
    if ob is None:
        continue
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bm.normal_update()

    revs = []
    for e in bm.edges:
        if len(e.link_faces) != 2:
            continue
        d = e.link_faces[0].normal.dot(e.link_faces[1].normal)
        if d < -0.85:
            f0, f1 = e.link_faces
            cen = (f0.calc_center_median() + f1.calc_center_median()) / 2
            revs.append((cen, d, e.calc_length(),
                         f0.calc_area(), f1.calc_area()))

    print("\n" + "=" * 92)
    print("### %s  反向边 %d / 总边 %d" % (name, len(revs), len(bm.edges)))
    print("=" * 92)
    if not revs:
        bm.free()
        continue

    # 按 z 分层
    zs = sorted(r[0].z for r in revs)
    print("  z 范围: %.4f ~ %.4f   (对象 z 范围 %.4f ~ %.4f)"
          % (zs[0], zs[-1],
             min(v.co.z for v in bm.verts), max(v.co.z for v in bm.verts)))

    # 按 z 直方图
    zmin, zmax = zs[0], zs[-1]
    bins = 10
    hist = [0] * bins
    for r in revs:
        k = int((r[0].z - zmin) / max(zmax - zmin, 1e-9) * bins)
        hist[min(k, bins - 1)] += 1
    for i, h in enumerate(hist):
        bar = "#" * (h * 40 // max(hist) if max(hist) else 1)
        print("    z %+.4f ~ %+.4f : %5d  %s"
              % (zmin + (zmax - zmin) * i / bins,
                 zmin + (zmax - zmin) * (i + 1) / bins, h, bar))

    # 前 8 个样例
    print("  样例:")
    for cen, d, el, a0, a1 in revs[:8]:
        print("    at (%+.4f, %+.4f, %+.4f)  dot=%+.4f  边长=%.2fmm  "
              "面面积 %.6f/%.6f m²"
              % (cen.x, cen.y, cen.z, d, el * 1000, a0, a1))
    bm.free()

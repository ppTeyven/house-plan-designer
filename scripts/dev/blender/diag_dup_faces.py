"""诊断"法线反向硬棱"的真实成因 —— 重复面 vs 绕序矛盾。

【为什么要区分】
修法完全不同：
  A. 【绕序矛盾】两个面共享边、法线反向 → 翻转其中一个即可修复
  B. 【重复面】同一个位置生成了两片法线相反的面（几何重合）
     → 翻转无用（翻转后还是两片重合），必须【删除重复面】
     或修正生成逻辑（不能生成两次）

判断方法：
  · 找一对 dot < -0.985 的相邻面
  · 算它们的"几何相似度"：把面 A 的顶点按最近点映射到面 B，
    若两组顶点几乎一一重合 → 重复面
  · 另算它们各自的面积与中心距离

用法：blender --background --python diag_dup_faces.py -- <glb> [obj]
"""
import bpy
import sys
import os
import math
import bmesh
import mathutils

args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
GLB = args[0]
ONLY = args[1] if len(args) > 1 else None

bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
bpy.ops.import_scene.gltf(filepath=GLB)
bpy.context.view_layer.update()

print("=" * 100)
print("重复面 / 绕序矛盾 诊断")
print("=" * 100)

for o in sorted(bpy.context.scene.objects, key=lambda x: x.name):
    if o.type != 'MESH' or not o.data.polygons:
        continue
    if ONLY and o.name != ONLY:
        continue

    bm = bmesh.new()
    bm.from_mesh(o.data)
    bm.normal_update()

    conflicts = []
    for e in bm.edges:
        if len(e.link_faces) != 2:
            continue
        f0, f1 = e.link_faces
        if f0.normal.dot(f1.normal) < -0.985:
            conflicts.append((f0, f1, e))

    if not conflicts:
        bm.free()
        continue

    # ---- 分类：重复面 vs 绕序矛盾 ----
    dup = 0
    twist = 0
    samples = []
    for f0, f1, e in conflicts[:40]:
        c0 = f0.calc_center_median()
        c1 = f1.calc_center_median()
        # 顶点距离：若两面的顶点集几乎重合 → 重复面
        dmin = []
        for v in f0.verts:
            dmin.append(min((v.co - w.co).length for w in f1.verts))
        avg_vd = sum(dmin) / max(len(dmin), 1)
        # 面积比
        ar = f0.calc_area() / max(f1.calc_area(), 1e-12)
        is_dup = avg_vd < 1e-5
        if is_dup:
            dup += 1
        else:
            twist += 1
        if len(samples) < 5:
            samples.append((avg_vd, ar, (c1 - c0).length,
                            f0.calc_area() * 1e6, f1.calc_area() * 1e6,
                            len(f0.verts), len(f1.verts)))

    print()
    print("### %-24s 冲突边 %4d  抽样40: 重复面 %2d / 绕序矛盾 %2d"
          % (o.name, len(conflicts), dup, twist))
    for avg_vd, ar, cd, a0, a1, n0, n1 in samples:
        kind = "重复面" if avg_vd < 1e-5 else "绕序矛盾"
        print("   %-6s 顶点平均距 %8.4fmm  面积比 %5.3f  中心距 %7.2fmm  "
              "面积 %8.1f/%8.1fmm²  顶点数 %d/%d"
              % (kind, avg_vd * 1000, ar, cd * 1000, a0, a1, n0, n1))
    bm.free()

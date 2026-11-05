"""硬棱成因精确诊断 —— 查明 180° 二面角到底是"折痕"还是"法线错误"。

【关键区分】
二面角 = 180° 有两种完全不同的成因：
  (a) 真实折痕：两个面确实背对（几何上有一道棱）
      → 例：top_clamp 把圆肩压平，压平区与未压平区交界处形成折角
  (b) 法线异常：某个面的绕序反了（normal 朝内）
      → 几何是平滑的，但法线翻转 → 渲染出现黑斑/硬边

两种的修法完全不同：(a) 要改建模参数或加过渡环，
                  (b) 要改 from_pydata 的面绕序。
不区分就乱改 = 白改。

【诊断输出】
对每条 >150° 的边，打印：
  · 两个面的法线向量
  · 两个面的面积
  · 是否退化（面积≈0）
  · 有符号体积（法线朝向是否一致）

用法：blender --background --python hard_edge_diag.py -- <glb> [obj_name]
"""
import bpy
import sys
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
print("硬棱成因诊断")
print("=" * 100)

for o in sorted(bpy.context.scene.objects, key=lambda x: x.name):
    if o.type != 'MESH' or not o.data.polygons:
        continue
    if ONLY and o.name != ONLY:
        continue

    bm = bmesh.new()
    bm.from_mesh(o.data)
    bm.normal_update()

    # ---- 全局法线一致性：有符号体积（散度定理）----
    vol = 0.0
    for f in bm.faces:
        vs = f.verts
        for i in range(len(vs)):
            a = vs[i].co
            b = vs[(i + 1) % len(vs)].co
            vol += a.x * (b.y * a.z - a.y * b.z) - a.y * (b.x * a.z - a.x * b.z) \
                + a.z * (b.x * a.y - a.x * b.y)
    vol /= 6.0

    hard = []
    degen = 0
    for f in bm.faces:
        if f.calc_area() < 1e-10:
            degen += 1
    for e in bm.edges:
        if len(e.link_faces) != 2:
            continue
        f0, f1 = e.link_faces
        deg = math.degrees(f0.normal.angle(f1.normal, 0.0))
        if deg > 150.0:
            hard.append((deg, e, f0, f1))

    if not hard:
        bm.free()
        continue

    print()
    print("### %s   有符号体积 %.1f cm³  退化面 %d" % (o.name, vol * 1e6, degen))
    hard.sort(key=lambda t: -t[0])
    for deg, e, f0, f1 in hard[:6]:
        mid = (e.verts[0].co + e.verts[1].co) * 0.5
        w = o.matrix_world @ mid
        print("  二面角 %6.1f°  at (%.3f, %.3f, %.3f)" % (deg, w.x, w.y, w.z))
        for tag, f in (("f0", f0), ("f1", f1)):
            n = f.normal
            c = f.calc_center_median()
            wc = o.matrix_world @ c
            print("     %s normal=(%6.3f,%6.3f,%6.3f) area=%9.2fmm2 center=(%.3f,%.3f,%.3f)"
                  % (tag, n.x, n.y, n.z, f.calc_area() * 1e6, wc.x, wc.y, wc.z))
        dot = f0.normal.dot(f1.normal)
        print("     dot=%.4f  (=-1 means fully reversed)  edge_len=%.1fmm"
              % (dot, e.calc_length() * 1000))
    bm.free()

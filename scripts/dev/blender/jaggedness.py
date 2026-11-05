"""锯齿/棱角检测 —— 定量分辨"几何不够圆滑"与"渲染采样不足"。

【为什么需要】
用户反馈："沙发上边边角角的地方纹理不够圆滑，有很强的锯齿感"。

这句话有两种完全不同的根因，必须分开：
  A. 【几何问题】模型本身的棱是硬的、网格分辨率不足、细分不够
     → 建模要改（加细分、平滑着色、提高 res_u/res_v）
  B. 【渲染问题】几何其实够圆滑，但渲染采样数低 / 视口用低精度预览
     → 渲染设置要改（taa_render_samples、视口采样）

肉眼分不清，因为渲染图里两者都表现为"边缘毛糙"。
→ 这里用【测量法】把两者分开。

【检测方法】
1. 几何棱角检测：
   对每个网格的相邻面，计算二面角（dihedral angle）。
   直角/锐角面 → 二面角接近 180°（平）或明显 < 180°（折痕）。
   统计"硬边"比例：二面角 < 150° 的边占比。
   → 硬边占比高 = 几何问题（真实的棱/折角）

2. 网格分辨率检测：
   对每个网格，估算三角形平均边长（米）。
   → 边长大 = 三角形过大 = 曲面会呈折线 = 几何分辨率不足

3. 曲线平滑度检测：
   沿网格边采样法线变化率（相邻面法线夹角），
   找出"法线跳变 > 30°"的位置 = 视觉上的棱。

用法：
  blender --background --python jaggedness.py -- <glb>
"""
import bpy
import sys
import os
import math
import bmesh
import mathutils

args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
GLB = args[0] if args else None
if not GLB:
    raise SystemExit("need a glb path")

bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
bpy.ops.import_scene.gltf(filepath=GLB)
bpy.context.view_layer.update()

# 排除装饰细件（滚边/针脚）—— 它们本来就该有细密几何
SKIP = ("pipe", "stitch", "tuft", "leg_cup", "alu_leg")

print("=" * 88)
print("锯齿/棱角 定量检测")
print("=" * 88)

rows = []
for o in bpy.context.scene.objects:
    if o.type != 'MESH' or not o.data.polygons:
        continue
    if any(k in o.name for k in SKIP):
        continue

    me = o.data
    bm = bmesh.new()
    bm.from_mesh(me)
    bm.normal_update()

    # ---- 1. 硬边统计（二面角）----
    hard = 0
    total_edges = 0
    worst_ang = 180.0
    for e in bm.edges:
        if len(e.link_faces) != 2:
            continue
        total_edges += 1
        a = e.link_faces[0].normal.angle(e.link_faces[1].normal, 0.0)
        deg = math.degrees(a)
        # 平的相邻面 → 夹角 0°；折角 → 夹角大
        if deg > 30.0:
            hard += 1
            worst_ang = max(worst_ang, deg)

    # ---- 2. 三角形边长统计 ----
    tri_edges = []
    for f in bm.faces:
        vs = f.verts
        for i in range(len(vs)):
            a = vs[i].co
            b = vs[(i + 1) % len(vs)].co
            tri_edges.append((a - b).length)
    avg_edge = sum(tri_edges) / max(len(tri_edges), 1)
    max_edge = max(tri_edges) if tri_edges else 0.0

    # ---- 3. 是否全部平滑着色 ----
    smooth_faces = sum(1 for p in me.polygons if p.use_smooth)
    smooth_pct = smooth_faces / max(len(me.polygons), 1) * 100

    # ---- 4. 细分修改器 ----
    mods = [m.type for m in o.modifiers]

    rows.append({
        'name': o.name,
        'faces': len(me.polygons),
        'hard_pct': hard / max(total_edges, 1) * 100,
        'worst_deg': worst_ang,
        'avg_edge_mm': avg_edge * 1000,
        'max_edge_mm': max_edge * 1000,
        'smooth_pct': smooth_pct,
        'mods': ','.join(mods) if mods else '-',
    })
    bm.free()

rows.sort(key=lambda r: -r['hard_pct'])

print()
print("%-16s %7s %8s %8s %10s %10s %7s %s"
      % ("对象", "面数", "硬边%", "最大折角°", "均边长mm", "最长边mm", "平滑%", "修改器"))
print("-" * 104)
for r in rows:
    print("%-16s %7d %8.1f %8.1f %10.2f %10.2f %7.0f %s"
          % (r['name'], r['faces'], r['hard_pct'], r['worst_deg'],
             r['avg_edge_mm'], r['max_edge_mm'], r['smooth_pct'], r['mods']))

# ---- 总结 ----
print()
print("=" * 88)
tot_faces = sum(r['faces'] for r in rows)
big = [r for r in rows if r['avg_edge_mm'] > 18.0]
not_smooth = [r for r in rows if r['smooth_pct'] < 99.0]
hardest = [r for r in rows if r['hard_pct'] > 3.0]

print("总面数: %d   对象数: %d" % (tot_faces, len(rows)))
print()
print("[A] 平均边长 > 18mm 的对象（曲面会呈折线 → 几何分辨率不足）:")
if big:
    for r in sorted(big, key=lambda x: -x['avg_edge_mm']):
        print("    %-16s 均边长 %.1fmm  最长 %.1fmm" % (r['name'], r['avg_edge_mm'], r['max_edge_mm']))
else:
    print("    无 —— 几何分辨率足够")

print()
print("[B] 硬边占比 > 3% 的对象（真实存在的棱/折角）:")
if hardest:
    for r in sorted(hardest, key=lambda x: -x['hard_pct']):
        print("    %-16s 硬边 %.1f%%  最大折角 %.1f°" % (r['name'], r['hard_pct'], r['worst_deg']))
else:
    print("    无 —— 没有明显的硬棱")

print()
print("[C] 非全平滑着色的对象:")
if not_smooth:
    for r in not_smooth:
        print("    %-16s 平滑面 %.0f%%" % (r['name'], r['smooth_pct']))
else:
    print("    无 —— 全部使用平滑着色")

print()
print("[结论]")
if big:
    print("  → 存在【几何分辨率不足】的对象：加大 res_u/res_v 或加细分细分")
else:
    print("  → 几何分辨率足够，锯齿【不是几何问题】")
if not_smooth:
    print("  → 存在未平滑着色的对象：会导致硬边视觉")
print("  → 若几何无问题，锯齿来自渲染采样（taa_render_samples 偏低）")

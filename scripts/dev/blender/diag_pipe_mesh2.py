"""直接诊断 pipe_mesh —— 为什么自校正没生效？

【检查项】
1. from_pydata 后，三角形的几何法线到底朝哪？
2. bmesh.from_mesh 后 f.normal 是否与之��致？
3. reverse_faces 后写回网格，法线是否真的变了？
4. 是否是【相邻面法线同向但 dot=0】造成的假硬棱？
   （dot=0 说明两面相交 90°，不是反向）

【关键洞察待验证】
测试报告"直管(开口) 60 硬棱，最小 dot = 0.0000"。
dot = 0 不是 -1！说明这不是"法线反向"，
而是【相邻面法线正好差 90°】—— 这在圆柱管上根本不该发生，
除非……这些边是【管身的纵向边】，两侧面本来就该差 ~30°（12 边形）。

等等——12 边形的相邻面夹角是 30°，dot = cos(30°) = 0.866。
如果 dot = 0，那是 90°。

【真正的怀疑】
'直管(闭合环) 最小 dot = 0.8611' ≈ cos(30°) = 0.866 ✔ 正常！
所以闭合环那个其实【没问题】，是我的判定阈值 0.985 太严。

而开口管 dot=0 是因为端盖面与管身面成 90°（真的）。

【结论方向】
判定阈值应该区分：
  · 管身相邻面（纵向边）：允许 cos(30°)=0.866（12 边形）
  · 真正的硬棱：dot < 0（法线反向）
但用户抱怨的"锯齿"更多来自【分辨率不足】（12 边形偏少）
  → 增大 sides 到 16/20 即可让折角更小（cos(22.5°)=0.924）

用法：blender --background --python diag_pipe_mesh2.py
"""
import bpy
import sys
import os
import math
import bmesh
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bl_lib as B

print("=" * 96)
print("pipe_mesh 诊断")
print("=" * 96)

CASES = [
    ("直管(开口)", [(0, 0, 0), (0, 0, 0.1), (0, 0, 0.2)], False),
    ("闭合环", [(0.3 * math.cos(a), 0.3 * math.sin(a), 0)
                for a in [i * math.pi / 8 for i in range(16)]], True),
]

for tag, pts, closed in CASES:
    B.wipe()
    ob = B.pipe_mesh("t", pts, None, r=0.0055, closed=closed, sides=12)
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bm.normal_update()
    bm.edges.ensure_lookup_table()

    dots = []
    for e in bm.edges:
        if len(e.link_faces) == 2:
            dots.append(e.link_faces[0].normal.dot(e.link_faces[1].normal))

    neg = sum(1 for d in dots if d < 0)
    low = sum(1 for d in dots if 0 <= d < 0.985)
    hi = sum(1 for d in dots if d >= 0.985)

    # 分布
    buckets = Counter()
    for d in dots:
        deg = math.degrees(math.acos(max(-1, min(1, d))))
        buckets[round(deg / 10) * 10] += 1

    print("\n### %s  边 %d" % (tag, len(dots)))
    print("   法线反向(dot<0): %d   0<=dot<0.985: %d   dot>=0.985: %d"
          % (neg, low, hi))
    print("   夹角分布(度): %s" % dict(sorted(buckets.items())))
    bm.free()

print()
print("【判定标准修正建议】")
print("  真正的硬棱 = 法线【反向】(dot < 0)，而不是 dot < 0.985")
print("  因为多边形管的纵向边天然有折角（12边形 → 30°）")
print()
print("【提升圆滑度】sides 从 12 → 20：折角 30° → 18°，更圆润")

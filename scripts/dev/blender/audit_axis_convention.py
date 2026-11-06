"""核对：验收站 251 个 GLB 的【轴向约定】是否一致。

【为什么必须查】
  验收站模型有两个来源：
    · 几何生成（geo_models）—— Mesh 坐标 (x=宽, y=高, z=深)，to_gltf 直写 POSITION
    · Polyhaven 现成资源 —— 原生 Z-up（z=高），fit_item 做缩放时
      用了 scale_matrix_xyz(s[0], s[2], s[1])，说明它【没有做轴旋转】
  如果两者轴向不一致（一个 y=高、一个 z=高），
  主程序按 (w,h,d) 读尺寸时，一半家具会【躺倒】——
  这正是"家具的正确方向搞清楚"要解决的事。

  判定方法：家具的高度轴通常明显区别于另外两轴
  （例如落地灯 400×400×1650、床 1800×2100×1050）。
  对每一件算「哪一轴是最大值」，再按来源分组统计。

用法：python audit_axis_convention.py
"""
import json
import os
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
MODELS = os.path.join(ROOT, "assets", "furnlib")
sys.path.insert(0, HERE)

import normalize_glb as NG

REPORT = os.path.join(ROOT, "assets", "_asset_cache", "build_report.json")


def main():
    rep = json.load(open(REPORT, encoding="utf-8"))
    route = {r["key"]: r.get("route") for r in rep["results"]}

    stats = {"geo": Counter(), "ph": Counter()}
    rows = []
    for fn in sorted(os.listdir(MODELS)):
        if not fn.endswith(".glb"):
            continue
        key = fn[:-4]
        js, _b = NG.read_glb(os.path.join(MODELS, fn))
        mn, mx = NG.world_bbox(js)
        dims = (mx[0] - mn[0], mx[1] - mn[1], mx[2] - mn[2])
        # 最大轴：0=x 1=y 2=z
        maxi = dims.index(max(dims))
        r = route.get(key, "?")
        stats.setdefault(r, Counter())[maxi] += 1
        rows.append((key, r, [round(d * 1000, 1) for d in dims], maxi))

    print("=== 每种来源的「最大轴」分布 ===")
    print("  0=x(宽)  1=y(高)  2=z(深)")
    for r, c in stats.items():
        tot = sum(c.values())
        print("  %-4s 总 %3d  →  x:%3d  y:%3d  z:%3d"
              % (r, tot, c.get(0, 0), c.get(1, 0), c.get(2, 0)))

    geo_y = stats.get("geo", Counter()).get(1, 0)
    geo_tot = sum(stats.get("geo", Counter()).values())
    ph_y = stats.get("ph", Counter()).get(1, 0)
    ph_tot = sum(stats.get("ph", Counter()).values())
    print()
    print("几何生成: 最大轴 = y 的占 %d/%d" % (geo_y, geo_tot))
    print("Polyhaven: 最大轴 = y 的占 %d/%d" % (ph_y, ph_tot))

    # 列出 Polyhaven 里最大轴不是 y 的（这些会躺倒）
    bad = [r for r in rows if r[1] == "ph" and r[3] != 1]
    if bad:
        print()
        print("=== Polyhaven 里最大轴 ≠ y 的（可能躺倒，需逐件核）===")
        for key, r, dims, maxi in bad:
            print("  %-18s dims=%-28s 最大轴=%s" % (key, dims, "xyz"[maxi]))
    return 0


if __name__ == "__main__":
    sys.exit(main())

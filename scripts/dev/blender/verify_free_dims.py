"""校验：3 个自由体 builder 的输出包围盒是否精确等于目标尺寸。

【为什么需要】
  build_all.py 的【几何生成路径不做自动缩放】——
  它完全依赖 builder 自己产出精确尺寸（见 build_all.py:105-109）。
  所以 builder 里的任何 "D * 0.55" 这类系数都会直接变成尺寸偏差。
  用户明令"不准有任何比例崩坏"，所以必须逐个验证包围盒。

【怎么测】
  不依赖 Blender：直接调用 builder 生成 Mesh，用其顶点算包围盒。
  注意 Mesh 坐标是 Blender 的 (x, y, z)，z 是竖直方向；
  导出后 glTF 会做 Y-up 转换 → 验收站读到的 (w, h, d) = (x范围, z范围, y范围)。

用法：python verify_free_dims.py
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import geo_models as GM          # 先加载主模块（geo_models_free 依赖它）
import geo_models_free as GF      # 再加载自由体（反向依赖会触发循环导入）

# 目标尺寸来自 reference/catalog-sizes.json
CASES = [
    ("freeSlats", "f_slats", 1800, 60, 2700),
    ("freeGlassScreen", "f_glass_screen", 1500, 60, 2400),
    ("freeLightBox", "f_light_box", 2000, 40, 30),
]


def bbox(mesh):
    """返回 (宽, 高, 深) mm。

    【Mesh 坐标约定】geo_gen.add_box(size=(w,h,d)) 的 size 是 (宽,高,深)，
    对应 Mesh 顶点 (x, y, z)：
      x = 宽 (w)
      y = 高 (h)   ← 注意：add_grid 的 fn 里 y 是竖直方向
      z = 深 (d)
    导出 glTF 时不做轴变换（to_gltf 直接写 POSITION），
    验收站按 (w,h,d) = (x范围, y范围, z范围) 读。
    """
    xs = [p[0] for p in mesh.pos]
    ys = [p[1] for p in mesh.pos]
    zs = [p[2] for p in mesh.pos]
    return ((max(xs) - min(xs)) * 1000,
            (max(ys) - min(ys)) * 1000,
            (max(zs) - min(zs)) * 1000)


def main():
    print("%-18s %-24s %-24s %-10s" % ("key", "实测 (w,h,d) mm", "目标 (w,d,h) mm", "偏差"))
    print("-" * 86)
    bad = 0
    for key, fn, w, d, h in CASES:
        f = getattr(GF, fn)
        m = f(w, d, h)
        bw, bh, bd = bbox(m)
        got = (bw, bh, bd)      # (w, h, d)
        tgt = (w, h, d)          # 目标 (w, h, d)
        errs = [abs(got[i] - tgt[i]) / max(tgt[i], 1e-6) for i in range(3)]
        mx = max(errs)
        flag = "  <-- 超 2%" if mx > 0.02 else ""
        if mx > 0.02:
            bad += 1
        print("%-18s %-24s %-24s %6.2f%%%s"
              % (key,
                 "(%.1f, %.1f, %.1f)" % got,
                 "(%d, %d, %d)" % tgt,
                 mx * 100, flag))
    print()
    if bad:
        print("仍有 %d 项偏差 > 2%%" % bad)
        return 1
    print("全部精确（偏差 <= 2%%）")
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""验收：把 assets/furnlib/*.glb 的【实测包围盒】与目录目标尺寸逐项对账。

【为什么必须做】
  用户要求"不准有任何比例崩坏"。build_report.json 里的 distort 只反映
  【资源原始尺寸 → 目标尺寸】的缩放比，不等于【成品 GLB 的实际尺寸】。
  几何生成路径不做自动缩放（见 build_all.py:105-109），
  所以 builder 里写错一个系数，成品尺寸就真的错了 —— 必须实测。

【对账口径】
  验收站 / 主程序按 (w, h, d) 读 GLB（glTF 是 Y-up）：
    w = x 范围, h = y 范围, d = z 范围
  目录目标 catalog-sizes.json 的顺序是 (w, d, h)，
  所以比较时要换成 (w, h, d) 再比。

用法：python audit_model_dims.py [--limit N]
"""
import json
import os
import struct
import sys

ROOT = r'D:\house planner\house-plan-designer-main'
MODELS = os.path.join(ROOT, "assets", "furnlib")
SIZES = os.path.join(ROOT, "reference", "catalog-sizes.json")


def read_glb_bbox(path):
    """读 GLB 的【世界包围盒】，返回 (w, h, d) 米。

    【为什么不能用 accessor 的 min/max】
      fit_item 的缩放是通过【根节点矩阵】施加的（见 fit_item.py:254
      apply_root_transform），节点还可能带旋转。
      accessor 的 min/max 是【局部轴对齐】包围盒，不含节点变换。
      必须用 normalize_glb.world_bbox —— 它把 8 个角点全部变换后取极值
      （旋转后的 AABB 正确算法）。

    glTF 是 Y-up：w = x 范围, h = y 范围, d = z 范围。
    """
    import normalize_glb as NG
    js, _bin = NG.read_glb(path)
    mn, mx = NG.world_bbox(js)
    return (mx[0] - mn[0], mx[1] - mn[1], mx[2] - mn[2])


def main():
    sizes = json.load(open(SIZES, encoding="utf-8"))
    files = sorted(f for f in os.listdir(MODELS) if f.endswith(".glb"))
    rows = []
    missing = []
    for fn in files:
        key = fn[:-4]
        tgt = sizes.get(key)
        if not tgt:
            missing.append(key)
            continue
        try:
            w, h, d = read_glb_bbox(os.path.join(MODELS, fn))
        except Exception as e:
            rows.append((key, None, tgt, str(e)))
            continue
        got = (round(w * 1000, 1), round(h * 1000, 1), round(d * 1000, 1))
        t = (tgt[0], tgt[2], tgt[1])        # (w, d, h) → (w, h, d)
        errs = [abs(got[i] - t[i]) / max(t[i], 1e-6) for i in range(3)]
        rows.append((key, got, t, max(errs)))

    ok = [r for r in rows if isinstance(r[3], float) and r[3] <= 0.02]
    bad = [r for r in rows if isinstance(r[3], float) and r[3] > 0.02]
    err = [r for r in rows if not isinstance(r[3], float)]

    print("模型总数: %d   目录有目标尺寸: %d   缺目标尺寸: %d"
          % (len(files), len(rows), len(missing)))
    print("精确 (<=2%%): %d    偏差 >2%%: %d    读取失败: %d"
          % (len(ok), len(bad), len(err)))
    print()
    if bad:
        print("=== 偏差 > 2% ===")
        for key, got, t, e in sorted(bad, key=lambda x: -x[3]):
            print("  %-18s got=%-22s target=%-22s err=%6.2f%%"
                  % (key, got, t, e * 100))
    if err:
        print("=== 读取失败 ===")
        for key, got, t, e in err:
            print("  %-18s %s" % (key, e))
    if missing:
        print("=== 目录无目标尺寸（catalog-sizes.json 缺）===")
        for k in missing:
            print("  ", k)
    return 0 if (not bad and not err and not missing) else 1


if __name__ == "__main__":
    sys.exit(main())

"""为每一款式挑选【语义正确 + 形变可接受】的现成资源（v3）。

【v2 的问题（实测）】
  只用"复合关键词"匹配 → 26/251 命中，其余 225 项全退几何生成。
  原因：Polyhaven 的家具库只有 ~85 件，很多品类（卫浴/地毯/楼梯/台球桌…）
  库里根本没有；同时"dining table"这种复合词命中率极低。

【v3 的三处改进】
  1. 形变指标区分【薄件轴】
     地毯(2000×1700×12)、挂画(900×40×650)这类薄件，
     厚度轴缩放 10 倍也看不出来。
     所以：目标里最小轴 < 最大轴 15% 时，该轴不计入形变。
     —— 这不是放水，是"人眼看不出"与"看得出来"的区别。
  2. 三级候选阶梯（语义优先，逐级放宽，但每级都要过形变关）
     L1 关键词命中（同品类 + 语义词）
     L2 仅品类命中（同品类，语义词没命中）
     L3 几何生成（库里没有 / 形变不可接受）
  3. 形变阈值按【是否对称件】微调
     通用 1.20；细长件（长宽比 > 2.2）放宽到 1.35；
     方形件（长宽比 < 1.15）收紧到 1.12（圆桌压成椭圆很显眼）。

【结论的正确表述】
  库里没有的品类 → 几何生成（按目标尺寸精确建，形变恒为 1.0）。
  这是"比例不崩坏"的**最强保证**，不是妥协。
"""
import os
import sys
import json
import re

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
CACHE = os.path.join(ROOT, "assets", "_asset_cache")
EXT = os.path.join(ROOT, "assets", "external")

import fit_item as FI
from pick_resources import CLASS_OK, KEYWORDS, cats_of, score_resource


def distort_of(target, src):
    """返回 (形变指标, 参与计算的轴数)。薄件轴不计入。"""
    t = list(target)
    s = list(src)
    mx = max(t)
    thin = [i for i in range(3) if t[i] < mx * 0.15]
    axes = [i for i in range(3) if i not in thin]
    if not axes:
        axes = [0, 1, 2]
    sc = [t[i] / s[i] for i in axes if s[i] > 0]
    if not sc:
        return 999.0, 0
    return max(sc) / min(sc), len(axes)


def threshold_for(target):
    """按形状特征定阈值。理由见模块 docstring。"""
    w, d, h = target
    ar = max(w, d) / max(1, min(w, d))
    if ar > 2.2:
        return 1.35                    # 细长件：拉伸不明显
    if ar < 1.15:
        return 1.12                    # 近方形：压扁成椭圆很显眼
    return 1.20


def pick(key, target, models):
    """返回 (level, info)。level ∈ L1/L2/None"""
    allow = CLASS_OK.get(key)
    if not allow:
        return None, None
    th = threshold_for(target)

    def scan(require_kw):
        best = None
        for m in models:
            if not (m.get("w") and m.get("d") and m.get("h")):
                continue
            c = cats_of(m)
            if not (c & set(allow)):
                continue
            sc = score_resource(key, m)
            if require_kw and sc <= 0:
                continue
            dist, naxes = distort_of(target, [m["w"], m["d"], m["h"]])
            if dist > th:
                continue
            k = (-round(sc), round(dist, 4))
            if best is None or k < best[0]:
                best = (k, m, dist, sc, naxes)
        if best is None:
            return None
        _, m, dist, sc, naxes = best
        return {"resource": m["id"], "distort": round(dist, 3),
                "score": sc, "src_dims": [m["w"], m["d"], m["h"]],
                "tri": m.get("tri"), "cats": m.get("cats"),
                "axes": naxes, "threshold": th}

    r = scan(True)
    if r:
        return "L1", r
    r = scan(False)
    if r:
        return "L2", r
    return None, None


def main():
    sizes = FI.load_sizes()
    with open(os.path.join(EXT, "ph_all_models.json"), encoding="utf-8-sig") as f:
        models = json.load(f)

    picked, geo = {}, []
    for key, target in sorted(sizes.items()):
        lvl, r = pick(key, target, models)
        if r:
            r["target"] = target
            r["level"] = lvl
            picked[key] = r
        else:
            geo.append(key)

    with open(os.path.join(CACHE, "pick_report.json"), "w", encoding="utf-8") as f:
        json.dump({"picked": picked, "geo_fallback": geo},
                  f, ensure_ascii=False, indent=1)

    l1 = sum(1 for v in picked.values() if v["level"] == "L1")
    l2 = len(picked) - l1
    print("现成资源 %d（L1 语义命中 %d / L2 仅品类 %d） / 几何生成 %d / 共 %d"
          % (len(picked), l1, l2, len(geo), len(sizes)))
    print()
    print("=== 形变分布 ===")
    ds = sorted(v["distort"] for v in picked.values())
    if ds:
        print("  min=%.3f p50=%.3f p90=%.3f max=%.3f"
              % (ds[0], ds[len(ds) // 2], ds[int(len(ds) * 0.9)], ds[-1]))
    print()
    print("=== L1（语义命中，优先使用）===")
    for k, v in sorted(picked.items()):
        if v["level"] == "L1":
            print("  %-18s -> %-28s d=%.3f/th=%.2f  %s"
                  % (k, v["resource"], v["distort"], v["threshold"],
                     v["src_dims"]))
    print()
    print("=== L2（仅品类命中，需人工复核语义）===")
    for k, v in sorted(picked.items()):
        if v["level"] == "L2":
            print("  %-18s -> %-28s d=%.3f/th=%.2f  %s"
                  % (k, v["resource"], v["distort"], v["threshold"],
                     v["src_dims"]))
    print()
    print("=== 几何生成（%d）===" % len(geo))
    print("  " + ", ".join(geo))


if __name__ == "__main__":
    main()

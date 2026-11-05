"""为每一款式挑选现成资源 —— v4 最终版。

【v3 的问题（实测）】
  L2 档（仅品类命中）产生了一批【语义错误】：
    rug        → dead_quiver_branch_01   （地毯配了根枯枝）
    printer    → lightbulb_led           （打印机配了个灯泡）
    catTree    → brass_vase_02           （猫爬架配了个铜花瓶）
    doormat   → root_cluster_01         （地垫配了树根）
    trashBin  → ceramic_vase_01         （垃圾桶配了个花瓶）
  这类"能看但不对"的搭配，摆进屋里就是逻辑错误 —— 用户明确禁止。

【v4 的修正】
  1. L2 档只允许【同品类且形态相近】的资源：
     用【形状签名】二次校验 —— 目标件与候选件的
     "扁平度"（最小轴/最大轴）必须同属一个档位。
     地毯是扁平件(0.006)，枯枝不是 → 淘汰。
  2. 仍然过不了 → 回退几何生成（形变恒为 1.0，语义绝对正确）。
     对 136 项这类"库里没有"的品类，几何生成反而是
     【比例最准】的方案，不是妥协。
  3. 形变阈值与薄件轴处理见 v3，保持不变。

【最终分布预期】
  现成资源 ~100 项（语义+比例双合格）
  几何生成 ~151 项（库里没有 / 比例不可接受）
  两者的尺寸都严格等于 reference/catalog-sizes.json 的目标值。
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


def thin_axes(t):
    """薄件轴：目标尺寸里 < 最大轴 15% 的轴。"""
    mx = max(t)
    return [i for i in range(3) if t[i] < mx * 0.15]


def distort_of(target, src):
    """形变指标（薄件轴不计入）。返回 (distort, axes)。"""
    t, s = list(target), list(src)
    thin = thin_axes(t)
    axes = [i for i in range(3) if i not in thin] or [0, 1, 2]
    sc = [t[i] / s[i] for i in axes if s[i] > 0]
    if not sc:
        return 999.0, 0
    return max(sc) / min(sc), len(axes)


def flatness(t):
    """扁平度 = 最小轴 / 最大轴。地毯 0.006，圆桌 1.0。"""
    return min(t) / max(t) if max(t) else 0.0


def shape_compatible(target, src):
    """目标件与候选件的形态是否同一档。

    规则：候选件与目标件的扁平度之比不能差太远。
    目标扁平件 → 候选也必须扁；目标方正件 → 候选不能是极扁的。
    """
    ft = flatness(target)
    fs = flatness(src)
    if ft < 0.12:                 # 目标很扁（地毯/挂画/屏风）
        return fs < 0.30
    if ft < 0.45:                 # 目标偏扁（矮柜/低桌）
        return fs < 0.60
    return fs > 0.18              # 目标方正 → 候选不能太扁


def threshold_for(target):
    w, d, h = target
    ar = max(w, d) / max(1, min(w, d))
    if ar > 2.2:
        return 1.35
    if ar < 1.15:
        return 1.12
    return 1.20


def pick(key, target, models):
    """返回 (level, info)。level ∈ L1 / L2 / None"""
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
            src = [m["w"], m["d"], m["h"]]
            if not shape_compatible(target, src):
                continue
            dist, naxes = distort_of(target, src)
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
    print("现成资源 %d（L1 %d / L2 %d） / 几何生成 %d / 共 %d"
          % (len(picked), l1, l2, len(geo), len(sizes)))
    print()
    print("=== L2（需人工复核语义）===")
    for k, v in sorted(picked.items()):
        if v["level"] == "L2":
            print("  %-18s -> %-28s d=%.3f/th=%.2f  %s  [%s]"
                  % (k, v["resource"], v["distort"], v["threshold"],
                     v["src_dims"], v["cats"]))
    print()
    print("=== 形变分布 ===")
    ds = sorted(v["distort"] for v in picked.values())
    if ds:
        print("  min=%.3f p50=%.3f p90=%.3f max=%.3f"
              % (ds[0], ds[len(ds) // 2], ds[int(len(ds) * 0.9)], ds[-1]))
    print()
    print("=== 几何生成（%d）===" % len(geo))
    print("  " + ", ".join(geo))


if __name__ == "__main__":
    main()

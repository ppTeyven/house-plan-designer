"""分析：251 个款式里，最多有多少能用【真实 PolyHaven 带贴图资源】替换掉几何白模。

【为什么需要】
  用户原话："别建模了，你去找现成的家具模型资源吧"，
  问卷选了 only_polyhaven —— 即目标是【全部换成现成资源】。
  但 PolyHaven 的家具类只有 ~85 个模型，而目录有 251 个款式，
  其中马桶/浴缸/钢琴/台球桌/楼梯/升降晾衣架… 库里根本没有。

  所以必须先用【数据】回答两个问题，而不是拍脑袋：
    Q1: 现有 517 个缓存资源，最多能覆盖多少款式？（放宽形变阈值后）
    Q2: 剩下的款式，是否真的库里没有？（还是关键词/品类门控太严）

【输出】
  - 可替换款式清单（资源 id + 形变）
  - 库中确实没有的款式清单（这些只能几何生成 + 真实扫描贴图）

用法：python analyze_ph_coverage.py [--max-distort 1.45]
"""
import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
CACHE = os.path.join(ROOT, "assets", "_asset_cache")
ACC = os.path.join(ROOT, "assets", "furnlib")

import fit_item as FI
import pick_resources_v5 as P5
from pick_resources import CLASS_OK, cats_of


def load_pool():
    """资源池：ph_dims.json（实测尺寸 + 品类）。"""
    with open(os.path.join(CACHE, "ph_dims.json"), encoding="utf-8") as f:
        dims = json.load(f)
    models = []
    for rid, d in dims.items():
        if not (d.get("w") and d.get("d") and d.get("h")):
            continue
        models.append({
            "id": rid,
            "cats": d.get("cats", ""),
            "w": d["w"], "d": d["d"], "h": d["h"],
            "tri": d.get("tri"),
        })
    return models


def best_candidates(key, target, models, max_distort):
    """不设品类门控，只按语义关键词找形变最小的候选。

    【为什么要绕开 CLASS_OK】
      CLASS_OK 是"品类大类"白名单（如 desk → table/office），
      它挡住了很多本来语义正确的资源（如 bookshelf → shelves）。
      这里用 REQUIRE 的关键词做语义判定 + 全库搜形变最小者，
      语义靠关键词、比例靠实测，两者独立评估。
    """
    reqs = P5.REQUIRE.get(key)
    if not reqs:
        return []
    exclude = P5.EXCLUDE.get(key) or ()
    out = []
    for m in models:
        kw, kw_w, kw_lvl = P5.keyword_hit(key, m)
        if not kw:
            continue
        # 排除词：资源 id 里的修饰词会改变语义
        id_toks = P5.toks_split(m["id"])
        if any(b in id_toks for b in exclude):
            continue
        src = P5.POSE_DIMS.get(m["id"]) or [m["w"], m["d"], m["h"]]
        dist, _naxes = P5.distort_of(target, src)
        if dist > max_distort:
            continue
        out.append((dist, kw_lvl, kw_w, kw, m["id"], src))
    out.sort(key=lambda r: (-r[1], -r[2], r[0]))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-distort", type=float, default=1.45)
    args = ap.parse_args()

    sizes = FI.load_sizes()
    models = load_pool()
    man = json.load(open(os.path.join(ACC, "manifest.json"), encoding="utf-8"))
    brep = {r["key"]: r for r in
            json.load(open(os.path.join(CACHE, "build_report.json"),
                           encoding="utf-8"))["results"]}

    replaceable = []
    no_asset = []
    already_ph = []
    for it in man["items"]:
        key = it["key"]
        if key not in sizes:
            no_asset.append((key, "no_target_size"))
            continue
        route = (brep.get(key) or {}).get("route", "?")
        if route == "ph":
            already_ph.append(key)
            continue
        target = list(sizes[key])
        cands = best_candidates(key, target, models, args.max_distort)
        if cands:
            replaceable.append((key, target, cands))
        else:
            no_asset.append((key, "no_semantic_match"))

    print("资源池: %d 个（ph_dims.json 实测）  max_distort=%.2f"
          % (len(models), args.max_distort))
    print("已是 ph 路线（不动）: %d" % len(already_ph))
    print("可用现成资源替换: %d" % len(replaceable))
    print("确实无可用现成资源: %d" % len(no_asset))
    print()

    print("=== 可替换（首选候选）===")
    for key, target, cands in replaceable:
        d, lvl, kw_w, kw, rid, src = cands[0]
        alt = ("  |备选 %s d=%.2f" % (cands[1][4], cands[1][0])) if len(cands) > 1 else ""
        print("  %-18s -> %-28s d=%.3f lvl=%d kw=%-14s target=%s src=%s%s"
              % (key, rid, d, lvl, kw, target, src, alt))

    print()
    print("=== 无可用现成资源（需几何生成 + 真实扫描贴图）===")
    groups = {}
    for key, why in no_asset:
        groups.setdefault(why, []).append(key)
    for why, keys in groups.items():
        print("  [%s] %d: %s" % (why, len(keys), ", ".join(sorted(keys))))

    # 输出给后续流水线用
    out = {
        "replaceable": {k: {"resource": c[0][4], "distort": c[0][0],
                            "keyword": c[0][3], "target": t,
                            "alts": [x[4] for x in c[1:4]]}
                        for k, t, c in replaceable},
        "no_asset": [k for k, _ in no_asset],
    }
    path = os.path.join(CACHE, "ph_coverage.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print("\n写入", path)


if __name__ == "__main__":
    main()

"""可行性分析：251 个款式里，有多少能从 518 个缓存资源里找到
【语义正确 + 形变可接受】的现成资源。

【为什么需要这个分析】
用户反馈"验收不合格，几乎所有的物件都是乱码"。实测交叉统计：

    route  source      贴图   数量
    geo    -           FLAT     131   ← 几何白模
    geo    polyhaven   FLAT      69   ← 有资源却走了 geo 路线
    ph     polyhaven   TEXTURED  38   ← 正常
    geo    polyhaven   TEXTURED   7   ← 之前已重建
    ph     -           TEXTURED   6   ← 正常

即 200/251 没有内嵌贴图 → 渲染成纯色白模 → 用户看到的"乱码"。

【本脚本只做分析，不写盘】
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
CACHE = os.path.join(ROOT, "assets", "_asset_cache")
RAW = os.path.join(CACHE, "raw")
ACC = os.path.join(ROOT, "assets", "furnlib")

import fit_item as FI
import pick_resources_v5 as P5
from pick_resources import CLASS_OK, cats_of


def toks(text):
    return set(re.split(r"[^a-z0-9]+", str(text).lower())) - {""}


def load_pool():
    """资源池：518 个 raw 资源 + 它们的实测尺寸 + 品类。"""
    dims = json.load(open(os.path.join(CACHE, "raw_dims.json"), encoding="utf-8"))
    ph = json.load(open(os.path.join(CACHE, "ph_dims.json"), encoding="utf-8"))
    pool = []
    for rid, d in dims.items():
        if not d:
            continue
        meta = ph.get(rid, {})
        pool.append({
            "id": rid,
            "w": d[0], "d": d[1], "h": d[2],
            "cats": meta.get("cats", ""),
            "tri": meta.get("tri"),
            "has_tex": os.path.exists(os.path.join(RAW, rid + ".glb")),
        })
    return pool


def best_for(key, target, pool):
    """按 v5 的两阶段语义门控 + 形变，返回最优资源或 None。

    直接委托给 pick_resources_v5.pick()，保证与正式构建管线
    【同一套选择逻辑】（否则两边的判定会漂移）。
    """
    return P5.pick(key, list(target), pool)


def main():
    sizes = FI.load_sizes()
    pool = load_pool()
    man = json.load(open(os.path.join(ACC, "manifest.json"), encoding="utf-8"))
    brep = {r["key"]: r for r in
            json.load(open(os.path.join(CACHE, "build_report.json"),
                           encoding="utf-8"))["results"]}
    amap = json.load(open(os.path.join(CACHE, "asset_map.json"), encoding="utf-8"))

    upgrades, keep_geo, already = [], [], []
    for it in man["items"]:
        key = it["key"]
        if key not in sizes:
            continue
        target = list(sizes[key])
        route = (brep.get(key) or {}).get("route", "?")
        cur_res = (amap.get(key) or {}).get("resource")
        if route == "ph":
            already.append((key, cur_res))
            continue
        r = best_for(key, target, pool)
        if r:
            upgrades.append((key, cur_res, r, route))
        else:
            keep_geo.append((key, cur_res, route))

    print("资源池 %d 个" % len(pool))
    print("已是 ph 路线（不动）: %d" % len(already))
    print("可升级为带贴图现成资源: %d" % len(upgrades))
    print("确实库里没有，只能几何生成: %d" % len(keep_geo))
    print()
    print("=== 可升级（前 90）===")
    for key, cur, r, route in upgrades[:90]:
        mark = "同" if cur == r["resource"] else "换"
        print("  %-18s %s %-28s d=%.3f/th=%.2f kw=%-16s src=%s"
              % (key, mark, r["resource"], r["distort"], r["threshold"],
                 r["keyword"], r["src_dims"]))
    print()
    print("=== 保持几何生成（%d）===" % len(keep_geo))
    print("  " + ", ".join(k for k, _, _ in keep_geo))


if __name__ == "__main__":
    main()

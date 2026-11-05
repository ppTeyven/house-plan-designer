"""诊断：现成资源的实测尺寸 vs ph_all_models.json 的记录值。

【为什么要查】
  挑选器用 ph_all_models.json 的 w/d/h 算形变，
  构建时 fit_item 从 GLB 重新量世界包围盒。
  两者的轴序/基准若不一致 → 挑选时合格、构建时被拒。
  这类"数据源不一致"必须查证，不能猜。
"""
import os
import sys
import json

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
CACHE = os.path.join(ROOT, "assets", "_asset_cache")
EXT = os.path.join(ROOT, "assets", "external")

import normalize_glb as NG


def main():
    with open(os.path.join(CACHE, "pick_report.json"), encoding="utf-8") as f:
        rep = json.load(f)
    picked = rep.get("picked", {})

    with open(os.path.join(EXT, "ph_all_models.json"), encoding="utf-8-sig") as f:
        allm = {m["id"]: m for m in json.load(f)}

    print("%-22s %-26s %-26s %s" % ("款式", "json 记录 (w,d,h)", "GLB 实测 (w,d,h)", "一致?"))
    print("-" * 92)
    bad = 0
    for key, v in sorted(picked.items()):
        rid = v["resource"]
        raw = os.path.join(CACHE, "raw", rid + ".glb")
        if not os.path.exists(raw):
            print("%-22s %-26s %s" % (key, v["src_dims"], "缺 raw GLB"))
            continue
        js, _ = NG.read_glb(raw)
        mn, mx = NG.world_bbox(js)
        meas = [round((mx[0] - mn[0]) * 1000), round((mx[2] - mn[2]) * 1000),
                round((mx[1] - mn[1]) * 1000)]
        rec = allm.get(rid, {})
        recs = [rec.get("w"), rec.get("d"), rec.get("h")]
        same = all(abs(a - b) <= max(8, a * 0.03)
                   for a, b in zip(meas, recs) if a and b)
        if not same:
            bad += 1
            print("%-22s %-26s %-26s %s"
                  % (key, recs, meas, "否 <<<"))
    print()
    print("不一致 %d / %d" % (bad, len(picked)))


if __name__ == "__main__":
    main()

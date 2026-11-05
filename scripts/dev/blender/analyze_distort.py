"""分析语义候选的形变分布 —— 为阈值找数据依据（不拍脑袋）。"""
import os
import sys
import json
import statistics

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))

import pick_resources as PR
import fit_item as FI

EXT = os.path.join(ROOT, "assets", "external")


def main():
    sizes = FI.load_sizes()
    with open(os.path.join(EXT, "ph_all_models.json"), encoding="utf-8-sig") as f:
        models = json.load(f)

    usable = [m for m in models
              if m.get("w") and m.get("d") and m.get("h")
              and min(m["w"], m["d"], m["h"]) > 0]

    rows, nosemi = [], []
    for key, target in sorted(sizes.items()):
        cands = [m for m in usable if PR.matches_semantic(key, m)]
        if not cands:
            nosemi.append(key)
            continue
        best = None
        for m in cands:
            s = [target[0] / m["w"], target[1] / m["d"], target[2] / m["h"]]
            d = max(s) / min(s)
            if best is None or d < best[0]:
                best = (d, m["id"])
        rows.append((best[0], key, best[1], len(cands)))

    rows.sort()
    vals = [r[0] for r in rows]
    print("有语义候选 %d / 无候选 %d（共 %d 款式）"
          % (len(rows), len(nosemi), len(sizes)))
    if len(vals) >= 4:
        q = statistics.quantiles(vals, n=4)
        q10 = statistics.quantiles(vals, n=10)
        print("形变分布 min=%.3f p25=%.3f p50=%.3f p75=%.3f p90=%.3f max=%.3f"
              % (vals[0], q[0], statistics.median(vals), q[2], q10[8], vals[-1]))
    print()
    for th in (1.10, 1.15, 1.20, 1.25, 1.30, 1.40, 1.60, 2.00):
        print("  阈值 %.2f -> 通过 %d 项" % (th, sum(1 for v in vals if v <= th)))

    print()
    print("=== 形变最小 40 项 ===")
    for d, key, rid, nc in rows[:40]:
        print("  %-18s %.3f  <- %-26s (候选 %d)" % (key, d, rid, nc))

    print()
    print("=== 无语义候选（%d）===" % len(nosemi))
    print("  " + ", ".join(nosemi))


if __name__ == "__main__":
    main()

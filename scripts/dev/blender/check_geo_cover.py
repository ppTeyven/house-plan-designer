"""检查：几何生成回退的每一款，是否都有对应的生成器。

【为什么必须查】
  pick_resources_v3 有 136 项要回退到几何生成。
  如果其中某项没有生成器 → 构建时会失败（no_builder）。
  提前查出来才能补齐。

用法：python check_geo_cover.py
"""
import os
import sys
import json

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
CACHE = os.path.join(ROOT, "assets", "_asset_cache")

import geo_models as GM
from asset_map import load_catalog, all_keys


def main():
    cat = load_catalog()
    keys = all_keys(cat)
    with open(os.path.join(CACHE, "pick_report.json"), encoding="utf-8") as f:
        rep = json.load(f)
    geo = rep.get("geo_fallback", [])

    print("几何生成回退 %d 项" % len(geo))
    missing = [k for k in geo if k not in GM.BUILDERS]
    print("有生成器: %d / 缺生成器: %d" % (len(geo) - len(missing), len(missing)))
    if missing:
        print()
        print("=== 缺生成器（必须补）===")
        for k in missing:
            t = dict((a, b) for a, b, c, d in keys).get(k, "?")
            print("  %-20s type=%s" % (k, t))
    return missing


if __name__ == "__main__":
    m = main()
    sys.exit(1 if m else 0)

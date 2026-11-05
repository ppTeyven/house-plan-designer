"""核对：每个款式是否有可用的参数化建模器（key 或 type 命中 BUILDERS）。

【为什么需要】
  修语义错配的策略是：语义不对的现成资源 → 改用【精确尺寸的参数化几何】。
  但只有存在 builder 的款式才能走这条路。
  这里一次性算出"哪些款式缺 builder"，避免改完发现无路可走。
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))

import geo_models as GM
from asset_map import load_catalog, all_keys
import fit_item as FI

cat = load_catalog()
keys = all_keys(cat)
SIZES = FI.load_sizes()

report = json.load(open(os.path.join(ROOT, "assets", "_asset_cache",
                                    "build_report.json"), encoding="utf-8"))
bykey = {r["key"]: r for r in report["results"]}

miss = []
ph_no_builder = []
for key, typ, name, group in keys:
    has_key = key in GM.BUILDERS
    has_typ = typ in GM.BUILDERS
    r = bykey.get(key, {})
    route = r.get("route")
    if route == "geo":
        if not (has_key or has_typ):
            miss.append((key, typ, name, group))
    else:
        if not (has_key or has_typ):
            ph_no_builder.append((key, typ, name, group, r.get("resource")))

print("总款式:", len(keys))
print("builder 覆盖:", sum(1 for k, t, n, g in keys
                          if k in GM.BUILDERS or t in GM.BUILDERS), "/", len(keys))
print()
print("=== 现走【几何】但【没有 builder】的款式（必须补）===")
for m in miss:
    print("   %-18s type=%-14s %-10s %s" % m)
print("   合计:", len(miss))
print()
print("=== 现走【现成资源】但【没有 builder】（改语义后可能需要）===")
for m in ph_no_builder:
    print("   %-18s type=%-14s %-10s %-22s %s" % m)
print("   合计:", len(ph_no_builder))

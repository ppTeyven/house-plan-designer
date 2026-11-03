"""校验 roadmap.json 与 catalog.json 的覆盖完整性。

【为什么需要】
roadmap.json 用【目录 key】标注 251 款分批。如果手工维护，
很容易漏款或写错 key（实测踩坑：P0 写了模型名 "bed"，
但目录里床的 key 是 "bed18"，导致进度显示 7/8 而不是 8/8）。

本脚本：
  1. 检查 roadmap 覆盖了 catalog 的全部款式（无遗漏）
  2. 检查没有重复分配（同一款不能出现在两个批次）
  3. 检查每个 key 都真实存在于 catalog（没有臆造）
  4. 打印每批进度

用法：python scripts/dev/blender/check_roadmap.py
"""
import json
import os
import sys
from collections import Counter

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
CAT = os.path.join(ROOT, "验收", "models", "catalog.json")
RM = os.path.join(ROOT, "验收", "models", "roadmap.json")

cat = json.load(open(CAT, encoding="utf-8"))
rm = json.load(open(RM, encoding="utf-8"))

cat_keys = [i["key"] for g in cat["groups"] for i in g["items"]]
built = {i["key"]: i["status"] for g in cat["groups"] for i in g["items"]}

assigned = []
errs = []

for b in rm["batches"]:
    assigned += b["items"]

# 1. 重复分配
dup = [k for k, c in Counter(assigned).items() if c > 1]
if dup:
    errs.append("重复分配到多个批次: %s" % dup)

# 2. 臆造的 key（roadmap 里有但目录没有）
unknown = [k for k in assigned if k not in cat_keys]
if unknown:
    errs.append("roadmap 里不存在的目录 key: %s" % unknown)

# 3. 漏掉的款式
missing = [k for k in cat_keys if k not in assigned]
if missing:
    errs.append("未分配批次的款式 %d 款: %s" % (len(missing), missing[:20]))

print("=== 批次覆盖 ===")
for b in rm["batches"]:
    keys = b["items"]
    ok = sum(1 for k in keys if built.get(k) == "ok")
    print("  %-3s %-34s %2d/%2d  %s" %
          (b["id"], b["name"], ok, len(keys), b["status"]))
print("  合计 %d 款 / 目录 %d 款" % (len(assigned), len(cat_keys)))

if errs:
    print("\n=== 错误 ===")
    for e in errs:
        print("  ✗", e)
    sys.exit(1)
print("\n✓ roadmap 与 catalog 完全对齐")

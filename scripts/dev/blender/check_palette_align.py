"""对比主程序 palette(hu) 与验收站 catalog 的 251 款式。

【为什么需要】
  主程序 assets/template.html 的 __FURN 是【按 type 取模型】：
      const __m = __FURN.get(n.type);
      __g.scale.set(i/__m.w, o/__m.h, s/__m.d);
  而 251 个款式里有很多【同 type 不同尺寸】的（例如 bed18/bed15/bed12
  都是 type:"bed"，但 1.8m / 1.5m / 1.2m）。
  按 type 取 = 一类共用一个模型 → 非均匀缩放到各自尺寸 → 比例崩坏。
  正确做法是【按款式 key 取】。

  本脚本核对：
    1. 两边的款式 key 集合是否一致（251 项全对齐）
    2. 同 type 的款式尺寸差异有多大（量化"按 type 取"的风险）
"""
import json
import os
import re

ROOT = r'D:\house planner\house-plan-designer-main'
TP = os.path.join(ROOT, "assets", "template.html")
CAT = os.path.join(ROOT, "验收", "models", "catalog.json")

s = open(TP, encoding="utf-8").read()
i = s.find("hu=[")
seg = s[i:]
end = seg.find("];")
seg = seg[:end] if end > 0 else seg[:60000]

# 主程序 palette: {key:"bed18",type:"bed",name:"...",w:1800,d:2100,h:1050,...}
pat = re.compile(
    r'\{key:"([^"]+)",type:"([^"]+)",name:"[^"]*",'
    r'w:([0-9.e]+),d:([0-9.e]+),h:([0-9.e]+)')
palette = {}
for m in pat.finditer(seg):
    k, t = m.group(1), m.group(2)
    try:
        w, d, h = float(m.group(3)), float(m.group(4)), float(m.group(5))
    except ValueError:
        continue
    palette[k] = (t, w, d, h)

cat = json.load(open(CAT, encoding="utf-8"))
catalog = {}
for g in cat["groups"]:
    for it in g["items"]:
        catalog[it["key"]] = it

print("主程序 palette 条目: %d" % len(palette))
print("验收站 catalog 条目: %d" % len(catalog))
print()

mk, ck = set(palette), set(catalog)
only_cat = sorted(ck - mk)
only_main = sorted(mk - ck)
print("catalog 有、主程序没有: %d  %s" % (len(only_cat), only_cat[:12]))
print("主程序有、catalog 没有: %d  %s" % (len(only_main), only_main[:12]))
print()

# type 不一致
mism = []
for k, it in catalog.items():
    if k in palette and palette[k][0] != it["type"]:
        mism.append((k, it["type"], palette[k][0]))
print("type 不一致: %d  %s" % (len(mism), mism[:10]))
print()

# 量化"按 type 取模型"的风险：同 type 的款式，尺寸差异
from collections import defaultdict
by_type = defaultdict(list)
for k, (t, w, d, h) in palette.items():
    by_type[t].append((k, w, d, h))

print("=== 同 type 多款式（按 type 取模型会导致共用/缩放失真）===")
risky = 0
for t, lst in sorted(by_type.items()):
    if len(lst) < 2:
        continue
    ws = [x[1] for x in lst]
    ds = [x[2] for x in lst]
    hs = [x[3] for x in lst]
    # 同一 type 内，三轴尺寸比的最大/最小
    ratios = []
    for arr in (ws, ds, hs):
        if min(arr) > 0:
            ratios.append(max(arr) / min(arr))
    r = max(ratios)
    mark = ""
    if r > 1.3:
        mark = "  <-- 高风险(共用会失真)"
        risky += 1
    print("  %-16s %d 项  尺寸比 max/min=%.2f%s" % (t, len(lst), r, mark))
print()
print("高风险 type 数: %d" % risky)

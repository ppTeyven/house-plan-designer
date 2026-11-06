"""对比 HEAD 基线与当前 template.html 的 check.mjs 报告，证明没有回归。

【为什么要对比，而不是只看当前版本】
  「改了没坏」只能靠同一套测试跑两遍、逐字段比对来证明。
  只看新版本通过，无法排除「本来就通过的项被我改坏了但没被发现」。

用法：python scripts/dev/compare_reports.py <基线report.json> <当前report.json>
"""
import json
import pathlib
import sys

a = json.load(open(sys.argv[1], encoding="utf-8"))
b = json.load(open(sys.argv[2], encoding="utf-8"))

ok = True


def cmp(name, key=None, deep=False):
    global ok
    key = key or name
    va, vb = a.get(key), b.get(key)
    if deep:
        same = json.dumps(va, ensure_ascii=False, sort_keys=True) == json.dumps(vb, ensure_ascii=False, sort_keys=True)
    else:
        same = va == vb
    mark = "OK  " if same else "DIFF"
    if not same:
        ok = False
    print("[%s] %-22s" % (mark, name))
    if not same:
        print("       基线: %s" % json.dumps(va, ensure_ascii=False)[:300])
        print("       现在: %s" % json.dumps(vb, ensure_ascii=False)[:300])


print("=== 结构 / 几何一致性（改动不应影响这些）===")
for k in ["name", "height", "walls", "openings", "openingsDropped",
          "wallsSkewed", "wallsDropped", "bounds_mm", "totalArea_m2",
          "labelsOutsideRooms", "freeWallEnds"]:
    cmp(k)

cmp("rooms", deep=True)
cmp("exteriorDims", deep=True)

print()
print("=== 问题清单 ===")
ia, ib = a.get("issues", []), b.get("issues", [])
print("  基线 %d 条，当前 %d 条" % (len(ia), len(ib)))
if ia == ib:
    print("[OK  ] issues 完全一致")
else:
    ok = False
    only_a = [x for x in ia if x not in ib]
    only_b = [x for x in ib if x not in ia]
    for x in only_a[:10]:
        print("  仅基线有: %s" % x[:160])
    for x in only_b[:10]:
        print("  仅当前有: %s" % x[:160])

print()
print("=== 运行时错误 ===")
ea, eb = a.get("errors", []), b.get("errors", [])
# 去掉 noise：同一错误文本出现多次只算一次
na = sorted(set(str(x) for x in ea))
nb = sorted(set(str(x) for x in eb))
print("  基线 %d 条(去重)，当前 %d 条(去重)" % (len(na), len(nb)))
print()
print("  【基线有、现在没了】")
for x in na:
    if x not in nb:
        print("    - %s" % x[:180])
print("  【现在新增的】")
for x in nb:
    if x not in na:
        print("    + %s" % x[:180])

print()
print("=== 截图 ===")
for k in ["screenshots"]:
    cmp(k, deep=True)

print()
print("=== 结论: %s ===" % ("无回归" if ok else "存在差异（见上）"))
sys.exit(0 if ok else 1)

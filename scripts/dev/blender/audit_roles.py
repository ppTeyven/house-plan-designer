"""对比【geo 模型当前材质角色】 vs 【builder 源码里写的材质】 —— 找出真正的错配。

【为什么要这个】
embed_pbr.py 的类型级兜底把混合材质模型改坏了（bed 床架→布、piano 琴键→木）。
正确做法是【以 builder 源码为真源】：
  · geo 模型：builder 已经给每个部件指定了正确材质 → 当前角色应当与 builder 一致
  · ph  模型：角色是 normalize_glb.guess_role() 从资源名猜的 → 猜错才是真 bug

输出：每个模型 builder 期望材质 vs 实际材质，标出 MISMATCH。
"""
import collections
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
ACC = os.path.join(ROOT, "assets", "furnlib")
CACHE = os.path.join(ROOT, "assets", "_asset_cache")

import normalize_glb as NG

# ---------------------------------------------------------------------
# 解析 builder 源码：builder 名 → 它用到的材质集合
# ---------------------------------------------------------------------
DEF_RE = re.compile(r"^def\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(", re.M)
MAT_RE = re.compile(r'mat\s*=\s*["\']([A-Za-z_]+)["\']')

FILES = ("geo_models.py", "geo_models_extra.py", "geo_models_extra2.py",
         "geo_models_extra3.py", "geo_models_extra4.py", "geo_models_free.py")

builder_mats = {}
for fn in FILES:
    p = os.path.join(HERE, fn)
    if not os.path.exists(p):
        continue
    s = open(p, encoding="utf-8").read()
    defs = list(DEF_RE.finditer(s))
    for i, m in enumerate(defs):
        name = m.group(1)
        end = defs[i + 1].start() if i + 1 < len(defs) else len(s)
        body = s[m.start():end]
        mats = set(MAT_RE.findall(body))
        if mats:
            builder_mats[name] = mats

# ---------------------------------------------------------------------
# BUILDERS 表：款式 key → 实际调用的 builder 函数
# ---------------------------------------------------------------------
BUILDERS_SRC = os.path.join(HERE, "geo_models.py")
src = open(BUILDERS_SRC, encoding="utf-8").read()
bstart = src.find("BUILDERS = {")
bblock = src[bstart:src.find("\n}", bstart)]
# lambda p: build_xxx(...)  → key → build_xxx
key2builder = {}
for m in re.finditer(r'"([A-Za-z_0-9]+)"\s*:\s*lambda\s+p\s*:\s*([A-Za-z_0-9]+)\(', bblock):
    key2builder[m.group(1)] = m.group(2)


def main():
    man = json.load(open(os.path.join(ACC, "manifest.json"), encoding="utf-8"))
    brep = {r["key"]: r for r in
            json.load(open(os.path.join(CACHE, "build_report.json"),
                           encoding="utf-8"))["results"]}
    amap = json.load(open(os.path.join(CACHE, "asset_map.json"), encoding="utf-8"))

    geo_ok = geo_bad = ph = 0
    bad_rows = []
    for it in man["items"]:
        key = it["key"]
        route = (brep.get(key) or {}).get("route", "?")
        js, _ = NG.read_glb(os.path.join(ACC, it["file"]))
        cur = [m.get("name", "") for m in js.get("materials", [])]
        if route == "geo":
            builder = (brep.get(key) or {}).get("builder") or key2builder.get(key)
            exp = builder_mats.get(builder)
            if exp is None:
                geo_ok += 1
                continue
            if set(cur) == exp:
                geo_ok += 1
            else:
                geo_bad += 1
                bad_rows.append((key, builder, sorted(exp), sorted(cur)))
        else:
            ph += 1

    print("geo 角色与 builder 一致: %d，不一致: %d；ph 模型: %d"
          % (geo_ok, geo_bad, ph))
    print()
    print("=== geo 角色不一致明细 ===")
    for key, builder, exp, cur in bad_rows:
        print("  %-18s builder=%-24s" % (key, builder))
        print("      期望: %s" % ",".join(exp))
        print("      实际: %s" % ",".join(cur))


if __name__ == "__main__":
    main()

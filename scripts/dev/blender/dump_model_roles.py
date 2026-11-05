"""导出：每个模型的 类别 / 语义类型 / 当前材质角色 / 是否有内嵌贴图。

用于制定"语义 → 材质角色"的修正表。
用法：python dump_model_roles.py > roles_dump.txt
"""
import json
import os
import struct
from collections import defaultdict

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
ACC = os.path.join(ROOT, "验收", "models")


def load_glb(path):
    blob = open(path, "rb").read()
    total = struct.unpack("<I", blob[8:12])[0]
    off = 12
    js = None
    while off + 8 <= min(total, len(blob)):
        clen, ctype = struct.unpack("<II", blob[off:off + 8])
        if ctype == 0x4E4F534A:
            js = json.loads(blob[off + 8:off + 8 + clen].decode("utf-8"))
            break
        off += 8 + clen
    return js


man = json.load(open(os.path.join(ACC, "manifest.json"), encoding="utf-8"))
items = man["items"]

by_cat = defaultdict(list)
for it in items:
    f = it.get("file")
    if not f:
        continue
    p = os.path.join(ACC, f)
    if not os.path.exists(p):
        continue
    js = load_glb(p)
    mats = [m.get("name", "") for m in js.get("materials", [])]
    roles = sorted(set(m[2:] if m.startswith("U_") else m for m in mats))
    nimg = len(js.get("images", []))
    by_cat[(it.get("cat"), it.get("type"))].append(
        (it["key"], it["name"], roles, nimg))

for (cat, typ), lst in sorted(by_cat.items(), key=lambda x: (str(x[0][0]), str(x[0][1]))):
    allroles = sorted(set(r for _, _, rs, _ in lst for r in rs))
    ntex = sum(1 for _, _, _, n in lst if n)
    print("cat=%-18s type=%-14s 件数=%-3d 有贴图=%-3d 角色集合=%s"
          % (cat, typ, len(lst), ntex, ",".join(allroles)))
    for key, name, roles, nimg in lst:
        print("      %-18s %-24s tex=%-2d %s"
              % (key, name, nimg, ",".join(roles)))

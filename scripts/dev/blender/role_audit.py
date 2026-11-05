"""统计 251 个 GLB 的材质角色分布，并对照 catalog 语义找出【角色错配】。

【为什么查】用户在验收站看到"几乎所有的物件都是乱码"。
实测发现：验收站 app.js 没有 U_* 角色 → 扫描贴图的映射，
207/251 个模型在 GLB 里也没内嵌贴图 → 在验收站里就是一团纯色白模，
认不出是什么家具。另外还要查角色本身是否错配
（比如 diningTable 的材质是 U_fabric_oat = 布的，桌子却是布料）。

用法：python role_audit.py
"""
import json
import os
import struct
from collections import Counter, defaultdict

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
ACC = os.path.join(ROOT, "验收", "models")
CT_JSON = 0x4E4F534A


def load_glb(path):
    blob = open(path, "rb").read()
    total = struct.unpack("<I", blob[8:12])[0]
    off = 12
    js = None
    while off + 8 <= min(total, len(blob)):
        clen, ctype = struct.unpack("<II", blob[off:off + 8])
        if ctype == CT_JSON:
            js = json.loads(blob[off + 8:off + 8 + clen].decode("utf-8"))
            break
        off += 8 + clen
    return js


man = json.load(open(os.path.join(ACC, "manifest.json"), encoding="utf-8"))
items = man["items"]

role_count = Counter()
models_with_tex = 0
models_no_tex = 0
by_key = {}

# 语义预期：哪些家具应该以什么材质为主
EXPECT = {
    "table": "wood", "desk": "wood", "counter": "wood", "cabinet": "wood",
    "wardrobe": "wood", "shelf": "wood", "bed": "wood", "chair": "wood",
    "stool": "wood", "bench": "wood", "dresser": "wood", "tvCabinet": "wood",
    "nightstand": "wood", "coffeeTable": "wood", "sideTable": "wood",
    "consoleTable": "wood", "diningTable": "wood", "conferenceTable": "wood",
    "sofa": "fabric", "armchair": "fabric", "chaise": "fabric", "beanbag": "fabric",
    "bedBench": "fabric", "bayCushion": "fabric", "mattress": "fabric",
}

for it in items:
    key = it["key"]
    f = it.get("file")
    if not f:
        continue
    p = os.path.join(ACC, f)
    if not os.path.exists(p):
        continue
    js = load_glb(p)
    mats = [m.get("name", "") for m in js.get("materials", [])]
    nimg = len(js.get("images", []))
    roles = []
    for m in mats:
        role = m[2:] if m.startswith("U_") else m
        roles.append(role)
        role_count[role] += 1
    has_tex = nimg > 0
    if has_tex:
        models_with_tex += 1
    else:
        models_no_tex += 1
    by_key[key] = {"roles": roles, "tex": has_tex, "imgs": nimg,
                   "name": it.get("name", "")}

print("=" * 72)
print("贴图情况：%d 个模型内嵌了扫描贴图，%d 个没有（验收站渲染成纯色白模）"
      % (models_with_tex, models_no_tex))
print("=" * 72)
print("\n材质角色分布：")
for r, c in role_count.most_common():
    print("   %-22s %4d" % (r, c))

print("\n" + "=" * 72)
print("角色错配（家具类型期望木质/布质，但材质全反）：")
print("=" * 72)
mismatch = []
for key, info in by_key.items():
    roles = set(info["roles"])
    if not roles:
        continue
    exp = None
    for k, v in EXPECT.items():
        if k.lower() in key.lower():
            exp = v
            break
    if not exp:
        continue
    fab = {r for r in roles if "fabric" in r or "uphol" in r}
    wd = {r for r in roles if "wood" in r}
    if exp == "wood" and fab and not wd:
        mismatch.append((key, info["name"], sorted(roles), "期望木质却是布料"))
    elif exp == "fabric" and wd and not fab:
        mismatch.append((key, info["name"], sorted(roles), "期望布料却是木质"))

for k, n, r, why in mismatch:
    print("   %-18s %-18s %-34s %s" % (k, n, ",".join(r), why))
print("\n共 %d 个角色错配" % len(mismatch))

print("\n" + "=" * 72)
print("完全没有贴图且角色单一的模型（验收站里=纯色方块，最像'乱码'）：")
print("=" * 72)
flat = [(k, i) for k, i in by_key.items() if not i["tex"] and len(set(i["roles"])) <= 1]
for k, i in sorted(flat)[:40]:
    print("   %-20s %-20s %s" % (k, i["name"], ",".join(i["roles"])))
print("共 %d 个" % len(flat))

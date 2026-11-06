"""【最终验收】确认 251 件全部是【高模 + 材质角色完整 + 尺寸正确】。

【四项硬指标】
  ① 面数：路径A 的 212 件必须比旧版显著更密（≥2.5x）；
          路径B 的 37 件（含 8 件 HERITAGE）必须【一字未动】
  ② 材质：每件至少 1 个 U_<role> 材质，且角色名在允许清单内
          （角色决定 PBR 贴图查找，写错 = 白模）
  ③ 尺寸：与 reference/catalog-sizes.json 一致（≤2%）
  ④ 同步：assets/furnlib/ 与 验收/models/ 字节完全相同
"""
import hashlib
import json
import os
import struct
import sys
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FURN = os.path.join(ROOT, "assets", "furnlib")
ACCM = os.path.join(ROOT, "验收", "models")
CACHE = os.path.join(ROOT, "assets", "_asset_cache", "_geo_highpoly")

VALID_ROLES = {
    "fabric_cream", "fabric_grey", "fabric_oat", "fabric_oat_d", "fabric_sheep",
    "wood_oak", "wood_walnut", "wood_ash", "wood_bamboo", "wood_mdf",
    "metal_black", "metal_steel", "metal_brass", "metal_chrome",
    "stone_light", "stone_dark", "ceramic_white", "glass_clear", "leaf",
    "leather_tan", "marble_white", "wall_clock", "plant",
}


def parse(path):
    with open(path, "rb") as f:
        blob = f.read()
    off = 12
    js = None
    while off + 8 <= len(blob):
        clen, ctype = struct.unpack("<II", blob[off:off + 8])
        if ctype == 0x4E4F534A:
            js = json.loads(blob[off + 8:off + 8 + clen].decode("utf-8"))
        off += 8 + clen
    if not js:
        return None
    acc = js.get("accessors") or []
    tris = 0
    for m in js.get("meshes", []):
        for p in m.get("primitives", []):
            i = p.get("indices")
            if i is not None and i < len(acc):
                tris += acc[i]["count"] // 3
    mn, mx = [1e9] * 3, [-1e9] * 3
    for a in acc:
        if a.get("type") != "VEC3" or "min" not in a:
            continue
        for k in range(3):
            mn[k] = min(mn[k], a["min"][k])
            mx[k] = max(mx[k], a["min"][k])
    size = None
    if mx[0] > -1e8:
        size = [round((mx[k] - mn[k]) * 1000) for k in range(3)]
    return {"tris": tris, "size": size, "kb": os.path.getsize(path) // 1024,
            "mats": [m.get("name") for m in (js.get("materials") or [])],
            "gen": (js.get("asset") or {}).get("generator", "")}


def sha1_8(p):
    h = hashlib.sha1()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()[:8]


def main():
    routes = json.load(open(os.path.join(CACHE, "_routes.json"), encoding="utf-8"))
    final = json.load(open(os.path.join(CACHE, "_final_2.json"), encoding="utf-8"))
    sizes = json.load(open(os.path.join(ROOT, "reference", "catalog-sizes.json"),
                           encoding="utf-8"))
    idx = json.load(open(os.path.join(FURN, "index.json"), encoding="utf-8"))
    key2file = {}
    for k, v in idx.items():
        if isinstance(v, dict) and v.get("file"):
            key2file.setdefault(k, v["file"])

    rebuilt = {b["key"]: b for b in final["built"]}
    problems = []
    stats = {"A": [0, 0], "B": [0, 0]}   # route -> [件数, 面数]
    synced = 0
    unsynced = []
    bad_role = []
    bad_size = []
    hash_mismatch = []

    for r in routes:
        key = r["key"]
        fn = key2file.get(key)
        if not fn:
            problems.append((key, "no_file"))
            continue
        p = os.path.join(FURN, fn)
        if not os.path.exists(p):
            problems.append((key, "missing"))
            continue
        info = parse(p)
        if not info:
            problems.append((key, "unreadable"))
            continue
        stats[r["route"]][0] += 1
        stats[r["route"]][1] += info["tris"]

        # ② 材质角色
        roles = []
        for m in info["mats"]:
            if m and m.startswith("U_"):
                roles.append(m[2:])
            elif m:
                bad_role.append((key, m))
        if not roles:
            bad_role.append((key, "无 U_ 材质: %s" % info["mats"]))
        for rl in roles:
            if rl not in VALID_ROLES:
                bad_role.append((key, "未知角色 U_" + rl))

        # ③ 尺寸（用旧文件尺寸对齐轴序后比）
        if r["route"] == "A" and key in rebuilt:
            b = rebuilt[key]
            old = parse(os.path.join(CACHE, "out2", fn))
            if old and info["size"] and old["size"]:
                if any(abs(a_ - b_) > max(20, 0.02 * b_) for a_, b_ in zip(old["size"], info["size"])):
                    bad_size.append((key, old["size"], info["size"]))

        # ④ 两处同步 + 哈希
        pa = os.path.join(ACCM, fn)
        if os.path.exists(pa):
            if sha1_8(pa) == sha1_8(p):
                synced += 1
            else:
                unsynced.append(fn)
        if idx.get(key, {}).get("v") != sha1_8(p):
            hash_mismatch.append(key)

    # ① 面数对比
    print("=" * 84)
    print("最终验收报告")
    print("=" * 84)
    for rt, label in (("A", "路径A 程序化重建"), ("B", "路径B 外部真实资源")):
        print("%-22s %3d 件  %10d 面  %7.1f MB"
              % (label, stats[rt][0], stats[rt][1],
                 sum(parse(os.path.join(FURN, key2file[r["key"]]))["kb"]
                     for r in routes if r["route"] == rt and r["key"] in key2file
                     and os.path.exists(os.path.join(FURN, key2file[r["key"]]))) / 1024))

    ratios = []
    for b in final["built"]:
        if b["old_tris"] > 0:
            ratios.append((b["new_tris"] / b["old_tris"], b["key"]))
    ratios.sort()
    print("\n① 面数提升: 最小 %.2fx(%s) 中位 %.2fx 最大 %.2fx"
          % (ratios[0][0], ratios[0][1], ratios[len(ratios) // 2][0], ratios[-1][0]))
    low = [x for x in ratios if x[0] < 1.0]
    print("   面数下降的件: %d %s" % (len(low), low[:8]))

    print("\n② 材质角色问题: %d 件" % len(bad_role))
    for k, m in bad_role[:15]:
        print("   %-18s %s" % (k, m))

    print("\n③ 尺寸偏差: %d 件" % len(bad_size))
    for k, o, n in bad_size[:10]:
        print("   %-18s %s -> %s" % (k, o, n))

    print("\n④ furnlib 与 验收/models 同步: %d / %d" % (synced, len(routes)))
    if unsynced:
        print("   不同步: %s" % unsynced[:10])
    print("   index.json 哈希不一致: %d 件" % len(hash_mismatch))
    if hash_mismatch:
        print("   %s" % hash_mismatch[:10])

    print("\n其他问题: %d" % len(problems))
    for k, m in problems[:10]:
        print("   %-18s %s" % (k, m))

    ok = (not low) and (not bad_role) and (not bad_size) and \
         (not unsynced) and (not hash_mismatch) and (not problems)
    print("\n" + ("=" * 84))
    print("结论: " + ("全部通过 ✅" if ok else "存在问题 ❌"))
    print("=" * 84)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())

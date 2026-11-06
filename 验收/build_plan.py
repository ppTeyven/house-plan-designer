"""【重建参数对齐】为 214 件路径A 模型确定【精确重建参数】。

【两个要验证的前提】
  ① 旧文件的实际尺寸 == catalog-sizes 的 (w,d,h)？
     —— 只有相等，才能"照原样重建"（外形不变，只加密细分）
  ② 重建后材质角色如何保持不变？
     —— geo_gen 的默认材质可能与旧版不同（例：freeBox 旧 U_wood_oak / 新 U_wood_walnut）
     —— 材质角色决定 PBR 贴图查找，变了就换色 = 视觉回退
     —— 方案：按材质槽序号把新名映射回旧名（槽数相同即可）

输出 _buildplan.json: 每件的 {w,d,h} + mat_remap
"""
import json
import os
import struct

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FURN = os.path.join(ROOT, "assets", "furnlib")
CACHE = os.path.join(ROOT, "assets", "_asset_cache", "_geo_highpoly")


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
            mx[k] = max(mx[k], a["max"][k])
    size = [round((mx[k] - mn[k]) * 1000) for k in range(3)] if mx[0] > -1e8 else None
    mats = [m.get("name") for m in (js.get("materials") or [])]
    return {"tris": tris, "size": size, "mats": mats}


def main():
    routes = json.load(open(os.path.join(CACHE, "_routes.json"), encoding="utf-8"))
    sizes = json.load(open(os.path.join(ROOT, "reference", "catalog-sizes.json"),
                           encoding="utf-8"))
    idx = json.load(open(os.path.join(FURN, "index.json"), encoding="utf-8"))
    key2file = {}
    for k, v in idx.items():
        if isinstance(v, dict) and v.get("file"):
            key2file.setdefault(k, v["file"])

    a = [r for r in routes if r["route"] == "A"]
    print("路径A %d 件" % len(a))

    # ---- 前提①：旧尺寸 vs catalog-sizes ----
    dim_ok = dim_bad = nofile = 0
    bad = []
    for r in a:
        fn = key2file.get(r["key"])
        if not fn:
            nofile += 1
            continue
        p = os.path.join(FURN, fn)
        if not os.path.exists(p):
            nofile += 1
            continue
        info = parse(p)
        tgt = sizes.get(r["key"])
        if not tgt or not info["size"]:
            bad.append((r["key"], "no_size"))
            dim_bad += 1
            continue
        # catalog-sizes 顺序是 (w,d,h)？ 用旧文件的三个值做集合比较，找出对应关系
        s = info["size"]
        tgt_sorted = sorted(tgt)
        s_sorted = sorted(s)
        if all(abs(a_ - b_) <= max(30, 0.03 * b_) for a_, b_ in zip(s_sorted, tgt_sorted)):
            dim_ok += 1
        else:
            dim_bad += 1
            bad.append((r["key"], "old=%s tgt=%s" % (s, tgt)))

    print("尺寸可对齐: %d / 尺寸不符: %d / 缺文件: %d" % (dim_ok, dim_bad, nofile))
    for k, why in bad[:15]:
        print("   %-18s %s" % (k, why))

    # ---- 前提②：轴序判定 (w,d,h) vs (w,h,d) ----
    print("\n=== 轴序判定（统计旧文件三轴与 catalog-sizes 三轴的对应命中）===")
    for perm, label in [((0, 1, 2), "w,d,h"), ((0, 2, 1), "w,h,d")]:
        hits = 0
        tot = 0
        for r in a:
            fn = key2file.get(r["key"])
            if not fn:
                continue
            p = os.path.join(FURN, fn)
            if not os.path.exists(p):
                continue
            info = parse(p)
            tgt = sizes.get(r["key"])
            if not tgt or not info["size"]:
                continue
            tot += 1
            if all(abs(info["size"][perm[i]] - tgt[i]) <= max(30, 0.03 * tgt[i])
                   for i in range(3)):
                hits += 1
        print("   %s : %d / %d  (%.0f%%)" % (label, hits, tot, 100.0 * hits / max(tot, 1)))

    # ---- 前提③：材质槽序能否一一映射 ----
    print("\n=== 材质角色核对（旧 vs geo_gen 默认）===")
    same = diff = 0
    diffs = []
    for r in a:
        old = r["mats"]
        fn = key2file.get(r["key"])
        if not fn:
            continue
        p = os.path.join(FURN, fn)
        if not os.path.exists(p):
            continue
        info = parse(p)
        if info["mats"] == old:
            same += 1
        else:
            diff += 1
            diffs.append((r["key"], old, info["mats"]))
    print("   一致 %d / 不同 %d" % (same, diff))
    for k, o, n in diffs[:20]:
        print("   %-18s 旧 %s -> 现 %s" % (k, o, n))


if __name__ == "__main__":
    main()

"""【高模重建 · 最终执行】路径A 的 214 件程序化模型 → GEO_DETAIL 倍率重建。

【已验证的前提】（见 验收/fidelity_check.py 的实测结果）
  用 GEO_DETAIL=1 重建，与旧文件逐图元比对：
    · 191/214 完全一致（材质名、部件数、三角面数、包围盒全同）
      → 证明 builder 未变，DETAIL 调大只会加密细分、不改外形
    · 22 件仅材质角色名不同（U_wood_oak -> U_wood_walnut 之类）
      → 材质名决定 PBR 贴图查找，换名 = 换色 = 视觉回退
      → 修法：重建后按【材质槽序号】把名字写回旧名（槽数一致即可）
    · 2 件 builder 缺失（longTable / diningTable4）→ 跳过，不动

【为什么只重建路径A】
  路由审计（验收/route_audit.py）实测：
    路径A 程序化生成  214 件  均  5,083 面  ← 真正的低模，是回退感的来源
    路径B 外部真实资源  37 件  均 41,023 面  ← 已是真资产，程序化覆盖必回退
  8 件 HERITAGE 手工高模（sofa 398k 面等）在路径B 内，本就完好。

【用法】
  python rebuild_final.py --apply
  GEO_DETAIL=3 python rebuild_final.py --apply   # 更激进
"""
import argparse
import json
import os
import shutil
import struct
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "scripts", "dev", "blender"))

FURN = os.path.join(ROOT, "assets", "furnlib")
ACCM = os.path.join(ROOT, "验收", "models")
CACHE = os.path.join(ROOT, "assets", "_asset_cache", "_geo_highpoly")
CT_JSON = 0x4E4F534A
CT_BIN = 0x004E4942


def read_glb(path):
    with open(path, "rb") as f:
        blob = f.read()
    off = 12
    js = None
    bin_ = b""
    chunks = []
    while off + 8 <= len(blob):
        clen, ctype = struct.unpack("<II", blob[off:off + 8])
        chunks.append((ctype, blob[off + 8:off + 8 + clen]))
        if ctype == CT_JSON:
            js = json.loads(chunks[-1][1].decode("utf-8"))
        elif ctype == CT_BIN:
            bin_ = chunks[-1][1]
        off += 8 + clen
    return js, bin_, chunks


def write_glb(path, js, bin_, chunks):
    jsb = json.dumps(js, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    jsb += b" " * ((4 - len(jsb) % 4) % 4)
    out = b"glTF" + struct.pack("<II", 2, 12 + 8 + len(jsb) + (8 + len(bin_) if bin_ else 0))
    out += struct.pack("<II", len(jsb), CT_JSON) + jsb
    if bin_:
        bb = bin_ + b"\x00" * ((4 - len(bin_) % 4) % 4)
        out += struct.pack("<II", len(bb), CT_BIN) + bb
    with open(path, "wb") as f:
        f.write(out)


def audit(path):
    js, _, _ = read_glb(path)
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
            mx[k] = max(mx[k], a["max"][k])
    size = [round((mx[k] - mn[k]) * 1000) for k in range(3)] if mx[0] > -1e8 else None
    return {"tris": tris, "size": size, "kb": os.path.getsize(path) // 1024,
            "mats": [m.get("name") for m in (js.get("materials") or [])]}


def remap_materials(path, old_names):
    """按槽位把材质名写回旧名。槽数不同则放弃（返回 False）。"""
    js, bin_, chunks = read_glb(path)
    mats = js.get("materials") or []
    if len(mats) != len(old_names):
        return False
    changed = 0
    for m, n in zip(mats, old_names):
        if m.get("name") != n:
            m["name"] = n
            changed += 1
    if changed:
        write_glb(path, js, bin_, chunks)
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    import geo_models as GM
    import geo_gen as GG
    print("GEO_DETAIL = %d" % GG.GEO_DETAIL)

    routes = json.load(open(os.path.join(CACHE, "_routes.json"), encoding="utf-8"))
    fid = json.load(open(os.path.join(CACHE, "_fidelity.json"), encoding="utf-8"))
    sizes = json.load(open(os.path.join(ROOT, "reference", "catalog-sizes.json"),
                           encoding="utf-8"))
    idx = json.load(open(os.path.join(FURN, "index.json"), encoding="utf-8"))
    key2file = {}
    for k, v in idx.items():
        if isinstance(v, dict) and v.get("file"):
            key2file.setdefault(k, v["file"])

    out = os.path.join(CACHE, "out%d" % GG.GEO_DETAIL)
    os.makedirs(out, exist_ok=True)

    a = [r for r in routes if r["route"] == "A"]
    # 跳过 builder 缺失的
    skip = [r for r in a if "no builder" in fid.get(r["key"], "")]
    todo = [r for r in a if "no builder" not in fid.get(r["key"], "")]
    print("路径A %d 件：重建 %d，跳过(builder缺失) %d"
          % (len(a), len(todo), len(skip)))
    for r in skip:
        print("   跳过 %-18s %s" % (r["key"], fid[r["key"]]))

    built, failed = [], []
    old_tris = new_tris = old_kb = new_kb = 0
    t0 = time.time()
    for i, r in enumerate(todo):
        key = r["key"]
        fn = key2file.get(key)
        if not fn:
            failed.append((key, "no_file"))
            continue
        oldp = os.path.join(FURN, fn)
        o = audit(oldp)
        tgt = sizes.get(key)
        params = {"w": tgt[0], "d": tgt[1], "h": tgt[2]} if tgt else {}
        dest = os.path.join(out, key + ".glb")
        try:
            GM.export(key, dest, params)
        except Exception as e:
            failed.append((key, "export: %s" % str(e)[:90]))
            continue
        n = audit(dest)
        if n is None:
            failed.append((key, "unreadable"))
            continue
        # 材质回映射
        if o and o["mats"] != n["mats"]:
            if not remap_materials(dest, o["mats"]):
                failed.append((key, "mat_slot_mismatch %d vs %d"
                               % (len(o["mats"]), len(n["mats"]))))
                continue
            n = audit(dest)
        # 尺寸校验（重建后必须与旧文件一致）
        if o and o["size"] and n["size"]:
            if any(abs(a_ - b_) > max(20, 0.02 * b_) for a_, b_ in zip(o["size"], n["size"])):
                failed.append((key, "size %s -> %s" % (o["size"], n["size"])))
                continue
        if o:
            old_tris += o["tris"]
            old_kb += o["kb"]
        new_tris += n["tris"]
        new_kb += n["kb"]
        built.append({"key": key, "file": fn, "new": dest,
                      "old_tris": o["tris"] if o else 0, "new_tris": n["tris"],
                      "old_kb": o["kb"] if o else 0, "new_kb": n["kb"],
                      "mats": n["mats"]})
        if (i + 1) % 50 == 0:
            print("   ...%d/%d (%.0fs)" % (i + 1, len(todo), time.time() - t0))

    print("\n生成 %d / 失败 %d  (%.1fs)" % (len(built), len(failed), time.time() - t0))
    for k, e in failed:
        print("   %-18s %s" % (k, e))
    print("\n面数: %d -> %d  (%.2fx)" % (old_tris, new_tris, new_tris / max(old_tris, 1)))
    print("体积: %.1f MB -> %.1f MB" % (old_kb / 1024, new_kb / 1024))
    tris = sorted(b["new_tris"] for b in built)
    if tris:
        print("新面数: 最小 %d / 中位 %d / 最大 %d"
              % (tris[0], tris[len(tris) // 2], tris[-1]))

    json.dump({"built": built, "failed": failed, "detail": GG.GEO_DETAIL},
              open(os.path.join(CACHE, "_final_%d.json" % GG.GEO_DETAIL), "w",
                   encoding="utf-8"), ensure_ascii=False, indent=1)

    if not args.apply:
        print("\n【预览】加 --apply 替换")
        return

    stamp = time.strftime("%Y%m%d_%H%M%S")
    bdir = os.path.join(ROOT, "assets", "_asset_cache",
                        "glb_backup_detail%d_%s" % (GG.GEO_DETAIL, stamp))
    os.makedirs(bdir, exist_ok=True)
    n = 0
    for b in built:
        fn = b["file"]
        for base in (FURN, ACCM):
            dst = os.path.join(base, fn)
            if not os.path.exists(dst):
                continue
            shutil.copy2(dst, os.path.join(bdir, fn + "." +
                         ("furn" if base == FURN else "acc")))
            shutil.copy2(b["new"], dst)
            n += 1
    print("\n备份 -> %s" % bdir)
    print("替换 %d 个文件（furnlib + 验收/models）" % n)


if __name__ == "__main__":
    main()

"""【保真校验】用 GEO_DETAIL=1 重建路径A 模型，逐图元比对旧文件。

【为什么必须先做这一步】
  直接用 DETAIL=2 重建会引入两类风险：
    ① 材质角色改名（freeBox: U_wood_oak -> U_wood_walnut）= 换贴图 = 视觉回退
    ② 材质槽与部件的对应关系错位（counter 的石材/木件对调）= 结构错乱
  只有先证明"DETAIL=1 重建 == 旧文件"（同 builder、同部件、同材质绑定），
  才能放心把 DETAIL 调到 2 —— 那时唯一的变化就是细分密度。

【比对内容】
  每个 primitive: (材质名, 三角面数, 顶点包围盒)
  旧文件 vs DETAIL=1 重建 → 必须逐项一致

【输出】
  _fidelity.json: {key: {ok:bool, reason:str}}
"""
import json
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
BL = os.path.join(ROOT, "scripts", "dev", "blender")
sys.path.insert(0, BL)

FURN = os.path.join(ROOT, "assets", "furnlib")
CACHE = os.path.join(ROOT, "assets", "_asset_cache", "_geo_highpoly")
OUT = os.path.join(CACHE, "_fid1")


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
    mats = [m.get("name") for m in (js.get("materials") or [])]
    acc = js.get("accessors") or []
    prims = []
    for m in js.get("meshes", []):
        for p in m.get("primitives", []):
            mi = p.get("material")
            name = mats[mi] if mi is not None and mi < len(mats) else None
            i = p.get("indices")
            tris = (acc[i]["count"] // 3) if i is not None and i < len(acc) else 0
            pa = p.get("attributes", {}).get("POSITION")
            bb = None
            if pa is not None and pa < len(acc):
                a = acc[pa]
                if "min" in a:
                    bb = [round(x, 4) for x in a["min"]] + [round(x, 4) for x in a["max"]]
            prims.append({"mat": name, "tris": tris, "bb": bb})
    return {"prims": prims}


def main():
    os.environ["GEO_DETAIL"] = "1"
    import geo_models as GM
    import geo_gen as GG
    import fit_item as FI

    print("GEO_DETAIL =", GG.GEO_DETAIL)
    routes = json.load(open(os.path.join(CACHE, "_routes.json"), encoding="utf-8"))
    sizes = json.load(open(os.path.join(ROOT, "reference", "catalog-sizes.json"),
                           encoding="utf-8"))
    idx = json.load(open(os.path.join(FURN, "index.json"), encoding="utf-8"))
    key2file = {}
    for k, v in idx.items():
        if isinstance(v, dict) and v.get("file"):
            key2file.setdefault(k, v["file"])

    a = [r for r in routes if r["route"] == "A"]
    os.makedirs(OUT, exist_ok=True)

    ok = bad = 0
    reasons = {}
    for i, r in enumerate(a):
        key = r["key"]
        fn = key2file.get(key)
        if not fn:
            continue
        oldp = os.path.join(FURN, fn)
        if not os.path.exists(oldp):
            continue
        tgt = sizes.get(key)
        params = {}
        if tgt:
            params = {"w": tgt[0], "d": tgt[1], "h": tgt[2]}
        dest = os.path.join(OUT, key + ".glb")
        try:
            GM.export(key, dest, params)
        except Exception as e:
            bad += 1
            reasons[key] = "export_fail: %s" % str(e)[:80]
            continue
        old = parse(oldp)
        new = parse(dest)
        if not old or not new:
            bad += 1
            reasons[key] = "unreadable"
            continue
        if len(old["prims"]) != len(new["prims"]):
            bad += 1
            reasons[key] = "prim_count %d vs %d" % (len(old["prims"]), len(new["prims"]))
            continue
        diffs = []
        for k2, (po, pn) in enumerate(zip(old["prims"], new["prims"])):
            if po["mat"] != pn["mat"]:
                diffs.append("p%d mat %s->%s" % (k2, po["mat"], pn["mat"]))
            elif po["tris"] != pn["tris"]:
                diffs.append("p%d tris %d->%d" % (k2, po["tris"], pn["tris"]))
            elif po["bb"] and pn["bb"] and any(
                    abs(a_ - b_) > 0.0015 for a_, b_ in zip(po["bb"], pn["bb"])):
                diffs.append("p%d bb" % k2)
        if diffs:
            bad += 1
            reasons[key] = "; ".join(diffs[:3])
        else:
            ok += 1
        if (i + 1) % 50 == 0:
            print("   ...%d/%d ok=%d bad=%d" % (i + 1, len(a), ok, bad))

    print("\n保真: 一致 %d / 不一致 %d  (共 %d)" % (ok, bad, len(a)))
    for k, v in list(reasons.items())[:30]:
        print("   %-20s %s" % (k, v))
    json.dump(reasons, open(os.path.join(CACHE, "_fidelity.json"), "w",
                            encoding="utf-8"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()

"""【来源判定】251 件家具里，哪些是 geo_gen 程序化生成、哪些是外部真实资源？

【为什么必须先分清】
  之前打算"全部用 GEO_DETAIL 重新生成"，但校验暴露：
    · plant 176,226 面 -> 13,616 面（回退！它来自真实资源库）
    · lawn  101,621 面 -> 3,072 面（回退！）
    · tree   82,074 面 -> 14,000 面（回退！）
  这些是【真实下载/导入的高质量资源】，被程序化模型覆盖就是真回退。

【判定方法】
  ① geo_gen 生成的 GLB，其 asset.generator == "geo_gen.py"（特征指纹）
  ② 其余都是外部资源
  另外用"节点命名"交叉验证：geo_gen 产出只有 1 个 mesh 名为 "geo"。

输出：每件的 route(A=程序化 / B=外部资源) + 三角面数，供高模重建精确筛选。
"""
import json
import os
import struct
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FURN = os.path.join(ROOT, "assets", "furnlib")


def parse(path):
    with open(path, "rb") as f:
        blob = f.read()
    off = 12
    js = None
    while off + 8 <= len(blob):
        clen, ctype = struct.unpack("<II", blob[off:off + 8])
        if ctype == 0x4E4F534A:
            try:
                js = json.loads(blob[off + 8:off + 8 + clen].decode("utf-8"))
            except Exception:
                return None
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
    gen = (js.get("asset") or {}).get("generator", "")
    mesh_names = [m.get("name") for m in (js.get("meshes") or [])]
    return {"tris": tris, "gen": gen, "meshes": mesh_names,
            "mats": sorted(set(m.get("name") for m in (js.get("materials") or []))),
            "kb": os.path.getsize(path) // 1024}


def main():
    idx = json.load(open(os.path.join(FURN, "index.json"), encoding="utf-8"))
    rows = []
    seen = set()
    for k, v in idx.items():
        if not isinstance(v, dict) or not v.get("file"):
            continue
        fn = v["file"]
        if fn in seen:
            continue
        seen.add(fn)
        p = os.path.join(FURN, fn)
        if not os.path.exists(p):
            continue
        r = parse(p)
        if not r:
            continue
        geo_gen = ("geo_gen" in (r["gen"] or "")) or \
                  (len(r["meshes"]) == 1 and r["meshes"][0] == "geo")
        rows.append({"key": k, "file": fn, "route": "A" if geo_gen else "B",
                     "tris": r["tris"], "kb": r["kb"], "gen": r["gen"],
                     "meshes": r["meshes"][:3], "mats": r["mats"]})

    a = [r for r in rows if r["route"] == "A"]
    b = [r for r in rows if r["route"] == "B"]
    print("=" * 88)
    print("251 件的构建来源判定")
    print("=" * 88)
    print("路径A 几何生成(geo_gen): %3d 件  %8d 面  %7.1f MB  均 %6d 面"
          % (len(a), sum(r["tris"] for r in a), sum(r["kb"] for r in a) / 1024,
             sum(r["tris"] for r in a) // max(len(a), 1)))
    print("路径B 外部真实资源:      %3d 件  %8d 面  %7.1f MB  均 %6d 面"
          % (len(b), sum(r["tris"] for r in b), sum(r["kb"] for r in b) / 1024,
             sum(r["tris"] for r in b) // max(len(b), 1)))
    print()
    print("--- 路径B（外部资源，不能被程序化覆盖）---")
    for r in sorted(b, key=lambda x: -x["tris"])[:40]:
        print("   %-20s %8d 面  %6d KB  mats=%s"
              % (r["key"], r["tris"], r["kb"], r["mats"][:3]))
    print()
    print("--- 路径A 中面数最高的 15 件（这些是真正的低模）---")
    for r in sorted(a, key=lambda x: -x["tris"])[:15]:
        print("   %-20s %8d 面  %6d KB" % (r["key"], r["tris"], r["kb"]))

    json.dump(rows, open(os.path.join(ROOT, "assets", "_asset_cache",
                                     "_geo_highpoly", "_routes.json"),
                         "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("\n明细已写 _geo_highpoly/_routes.json")


if __name__ == "__main__":
    main()

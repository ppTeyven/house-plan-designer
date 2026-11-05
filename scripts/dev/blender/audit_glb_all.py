"""GLB 结构探针：检查 extensionsRequired / accessor / 实际包围盒（修正版）。

"乱码"根因候选：
  (a) KHR_draco_mesh_compression —— 验收站没挂 Draco 解码器 => 顶点数据全是垃圾
  (b) accessor bufferView 偏移/步长算错 => 顶点乱飞
  (c) 材质角色错配
"""
import json
import os
import struct
import sys
import math
from collections import Counter

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
GLB_DIR = os.path.join(ROOT, "assets", "furnlib")

COMP = {5120: ("b", 1), 5121: ("B", 1), 5122: ("h", 2), 5123: ("H", 2),
        5125: ("I", 4), 5126: ("f", 4)}
NCOMP = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4, "MAT4": 16}


def read_glb(path):
    with open(path, "rb") as f:
        data = f.read()
    ver, total = struct.unpack("<II", data[4:12])
    off, js, bin_ = 12, None, b""
    while off + 8 <= len(data):
        clen, ctype = struct.unpack("<II", data[off:off + 8])
        chunk = data[off + 8:off + 8 + clen]
        if ctype == 0x4E4F534A:
            js = json.loads(chunk.decode("utf-8"))
        elif ctype == 0x004E4942:
            bin_ = chunk
        off += 8 + clen
    return js, bin_, total, len(data)


def bounds_of(js, bin_, idx, limit=200000):
    acc = js["accessors"][idx]
    bv = acc.get("bufferView")
    if bv is None:
        return None
    bview = js["bufferViews"][bv]
    fmt, sz = COMP[acc["componentType"]]
    ncomp = NCOMP[acc["type"]]
    count = acc["count"]
    stride = bview.get("byteStride") or (sz * ncomp)
    base = bview.get("byteOffset", 0) + acc.get("byteOffset", 0)
    gmin = [float("inf")] * 3
    gmax = [float("-inf")] * 3
    n = min(count, limit)
    for i in range(n):
        o = base + i * stride
        if o + sz * ncomp > len(bin_):
            return ("OVERRUN", count)
        vals = struct.unpack_from("<%d%s" % (ncomp, fmt), bin_, o)
        for k in range(min(3, ncomp)):
            v = vals[k]
            if math.isnan(v) or math.isinf(v):
                return ("NAN", count)
            if v < gmin[k]:
                gmin[k] = v
            if v > gmax[k]:
                gmax[k] = v
    return ([round(gmax[i] - gmin[i], 4) for i in range(3)],
            [round(gmin[i], 4) for i in range(3)], count)


def probe(path):
    js, bin_, total, filelen = read_glb(path)
    ext_req = js.get("extensionsRequired", [])
    ext_use = js.get("extensionsUsed", [])
    info = {
        "key": os.path.splitext(os.path.basename(path))[0],
        "gen": js.get("asset", {}).get("generator", "?"),
        "extReq": ext_req, "extUse": ext_use,
        "meshes": len(js.get("meshes", [])), "mats": len(js.get("materials", [])),
        "tex": len(js.get("textures", [])),
        "accessors": len(js.get("accessors", [])),
        "bv": len(js.get("bufferViews", [])),
        "prims": 0, "dracoPrim": 0, "tris": 0,
        "bbox": None, "minY": None, "err": None,
        "matNames": [m.get("name", "") for m in js.get("materials", [])],
    }
    gmin = [float("inf")] * 3
    gmax = [float("-inf")] * 3
    for mesh in js.get("meshes", []):
        for prim in mesh.get("primitives", []):
            info["prims"] += 1
            if "KHR_draco_mesh_compression" in prim.get("extensions", {}):
                info["dracoPrim"] += 1
                continue
            ai = prim.get("indices")
            if ai is not None:
                info["tris"] += js["accessors"][ai]["count"] // 3
            pi = prim.get("attributes", {}).get("POSITION")
            if pi is None:
                continue
            r = bounds_of(js, bin_, pi)
            if r is None:
                continue
            if not isinstance(r[0], list):
                info["err"] = "%s (%s)" % (r[0], r[1])
                continue
            bb, mn, _ = r
            for k in range(3):
                gmin[k] = min(gmin[k], mn[k])
                gmax[k] = max(gmax[k], bb[k])
    if gmin[0] != float("inf"):
        info["bbox"] = [round(gmax[i] - gmin[i], 4) for i in range(3)]
        info["minY"] = round(gmin[1], 4)
    return info


def main():
    files = sorted(f for f in os.listdir(GLB_DIR) if f.endswith(".glb"))
    only = set(sys.argv[1:])
    extreq = Counter()
    gens = Counter()
    draco = 0
    errs = []
    baddim = []
    ungrounded = []
    nomat = []
    for f in files:
        i = probe(os.path.join(GLB_DIR, f))
        if only and i["key"] not in only:
            continue
        extreq[tuple(i["extReq"])] += 1
        gens[i["gen"]] += 1
        if i["dracoPrim"]:
            draco += 1
        if i["err"]:
            errs.append((i["key"], i["err"]))
        if i["bbox"]:
            if max(i["bbox"]) > 100 or min(i["bbox"]) < 0.005:
                baddim.append((i["key"], i["bbox"], i["minY"]))
            if i["minY"] is not None and abs(i["minY"]) > 0.03:
                ungrounded.append((i["key"], i["minY"]))
        if not i["matNames"]:
            nomat.append(i["key"])
    print("total:", len(files))
    print("\n-- extensionsRequired histogram --")
    for k, v in extreq.most_common():
        print("  %-50s %d" % (",".join(k) or "(none)", v))
    print("\n-- generator histogram --")
    for k, v in gens.most_common():
        print("  %-50s %d" % (k, v))
    print("\n-- models WITH draco prims:", draco)
    print("\n-- ERRORS (%d) --" % len(errs))
    for k, e in errs[:40]:
        print("  %-18s %s" % (k, e))
    print("\n-- BAD DIMENSIONS (%d) --" % len(baddim))
    for k, b, y in baddim[:40]:
        print("  %-18s bbox=%s minY=%s" % (k, b, y))
    print("\n-- UNGROUNDED (%d) --" % len(ungrounded))
    for k, y in ungrounded[:40]:
        print("  %-18s minY=%s" % (k, y))
    print("\n-- NO MATERIAL (%d) --" % len(nomat))
    print("  " + ", ".join(nomat[:40]))


if __name__ == "__main__":
    main()

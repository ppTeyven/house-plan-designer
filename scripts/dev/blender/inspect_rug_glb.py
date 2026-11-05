"""检查地毯 GLB 的网格密度，判断能否用位移贴图做自然褶皱。"""
import os
import sys
import json
import struct

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
GLB_DIR = os.path.join(ROOT, "assets", "furnlib")


def read_glb(path):
    with open(path, "rb") as f:
        data = f.read()
    magic, ver, total = struct.unpack("<III", data[:12])
    off = 12
    chunks = {}
    while off < total:
        clen, ctype = struct.unpack("<II", data[off:off + 8])
        chunks[ctype] = data[off + 8:off + 8 + clen]
        off += 8 + clen + ((4 - clen % 4) % 4 if clen % 4 else 0)
    j = json.loads(chunks[0x4E4F534A].decode("utf-8"))
    return j


for name in ["rug", "roundRug", "doormat", "playMat"]:
    p = os.path.join(GLB_DIR, name + ".glb")
    if not os.path.exists(p):
        print(name, "MISSING")
        continue
    j = read_glb(p)
    prims = []
    for m in j.get("meshes", []):
        for pr in m.get("primitives", []):
            attrs = pr.get("attributes", {})
            count = j["accessors"][attrs["POSITION"]]["count"] if "POSITION" in attrs else 0
            idx = pr.get("indices")
            tri = j["accessors"][idx]["count"] // 3 if idx is not None else count // 3
            mat = pr.get("material")
            mname = ""
            if mat is not None:
                mname = j["materials"][mat].get("name", "")
            prims.append((count, tri, mname, sorted(attrs.keys())))
    print("%-10s meshes=%d prims=%s" % (name, len(j.get("meshes", [])), prims))
    # bbox
    for acc in j.get("accessors", []):
        if acc.get("type") == "VEC3" and acc.get("componentType") == 5126:
            mn = acc.get("min")
            mx = acc.get("max")
            if mn and mx and (mx[1] - mn[1]) > 1e-6 and (mx[1] - mn[1]) < 0.05:
                print("           flat-ish acc bbox:", [round(v, 4) for v in mn], [round(v, 4) for v in mx])
            break

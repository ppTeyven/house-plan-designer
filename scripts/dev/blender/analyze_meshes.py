"""统计 furnlib 里每个 GLB 的 mesh 数 / 材质数 / 按材质分组后的 mesh 数。
用于评估「按材质合并子网格」能把 draw call 降多少。
"""
import io
import json
import os
import struct
import sys
from collections import Counter, defaultdict

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "assets", "furnlib")


def read_glb(path):
    with open(path, "rb") as f:
        data = f.read()
    magic, version, length = struct.unpack("<III", data[:12])
    assert magic == 0x46546C67, "not a glb: %s" % path
    off = 12
    js = None
    while off < length:
        clen, ctype = struct.unpack("<II", data[off:off + 8])
        chunk = data[off + 8:off + 8 + clen]
        if ctype == 0x4E4F534A:
            js = json.loads(chunk.decode("utf-8"))
        off += 8 + clen + ((4 - (clen % 4)) % 4 if clen % 4 else 0)
    return js


def analyse(path):
    js = read_glb(path)
    meshes = js.get("meshes") or []
    mats = js.get("materials") or []
    prim_per_mesh = []
    mat_names = []
    for m in meshes:
        prims = m.get("primitives") or []
        prim_per_mesh.append(len(prims))
        for p in prims:
            mi = p.get("material")
            nm = mats[mi].get("name", "") if mi is not None and mi < len(mats) else ""
            mat_names.append(nm)
    # 合并后：同一材质名的 mesh 可以合成 1 个 draw call
    by_mat = Counter(mat_names)
    return {
        "meshes": len(meshes),
        "prims": sum(prim_per_mesh),
        "materials": len(mats),
        "mat_groups": len(by_mat),
        "mat_names": by_mat,
    }


def main():
    lib = os.path.normpath(ROOT)
    files = sorted(f for f in os.listdir(lib) if f.endswith(".glb"))
    total_meshes = total_groups = 0
    rows = []
    for f in files:
        try:
            a = analyse(os.path.join(lib, f))
        except Exception as e:
            print("ERR %s: %s" % (f, e))
            continue
        total_meshes += a["meshes"]
        total_groups += a["mat_groups"]
        rows.append((f, a))
    print("models: %d" % len(rows))
    print("total mesh objects: %d" % total_meshes)
    print("total after merge-by-material: %d" % total_groups)
    print("reduction: %.1f%%" % (100.0 * (1 - total_groups / float(total_meshes))))
    print()
    print("--- top 20 by mesh count ---")
    rows.sort(key=lambda r: -r[1]["meshes"])
    for f, a in rows[:20]:
        print("  %-24s meshes=%-4d groups=%-4d  %s" % (
            f, a["meshes"], a["mat_groups"],
            ",".join("%s x%d" % (k or "-", v) for k, v in a["mat_names"].most_common(6))))
    print()
    # 属性集合是否一致（合并前提）
    print("--- attribute consistency check (top 12) ---")
    for f, a in rows[:12]:
        js = read_glb(os.path.join(lib, f))
        sets = set()
        for m in js.get("meshes") or []:
            for p in m.get("primitives") or []:
                sets.add(tuple(sorted(p.get("attributes", {}).keys())))
        print("  %-24s attrsets=%d %s" % (f, len(sets), [list(x) for x in sets]))


if __name__ == "__main__":
    main()

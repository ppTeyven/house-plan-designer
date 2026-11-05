"""检查单个 GLB 的三角面 / 顶点 / 材质 分布，找出「大文件」到底贵在哪。"""
import io
import json
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import normalize_glb as NG  # noqa: E402

COMP = {5120: 1, 5121: 1, 5122: 2, 5123: 2, 5125: 4, 5126: 4}
TYPE_N = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4, "MAT4": 16}


def main():
    path = sys.argv[1]
    js, bin_data = NG.read_glb(path)
    mats = js.get("materials") or []
    print("file: %s  (%.2f MB)" % (os.path.basename(path),
                                  os.path.getsize(path) / 1048576.0))
    print("meshes=%d materials=%d accessors=%d bufferViews=%d" % (
        len(js.get("meshes") or []), len(mats),
        len(js.get("accessors") or []), len(js.get("bufferViews") or [])))
    total_tris = 0
    for mi, mesh in enumerate(js.get("meshes") or []):
        for pi, prim in enumerate(mesh.get("primitives") or []):
            attrs = prim.get("attributes", {})
            acc = js["accessors"][attrs["POSITION"]]
            n = acc["count"]
            if prim.get("indices") is not None:
                ic = js["accessors"][prim["indices"]]["count"]
                tris = ic // 3
            else:
                tris = n // 3
            total_tris += tris
            mi_ = prim.get("material")
            mname = mats[mi_].get("name", "?") if mi_ is not None else "?"
            bvs = set()
            for a in attrs.values():
                bv = js["accessors"][a].get("bufferView")
                if bv is not None:
                    bvs.add(bv)
            bbytes = sum(js["bufferViews"][b].get("byteLength", 0) for b in bvs)
            print("  mesh%-2d prim%-2d verts=%-7d tris=%-7d mat=%-18s bytes=%-9d attrs=%s" % (
                mi, pi, n, tris, mname, bbytes, ",".join(sorted(attrs.keys()))))
    print("TOTAL tris: %s" % f"{total_tris:,}")


if __name__ == "__main__":
    main()

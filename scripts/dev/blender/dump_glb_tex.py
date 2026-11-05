"""导出 GLB 内嵌贴图为 PNG，肉眼判断是否"乱码"（噪点/色块/错图）。"""
import os
import struct
import sys
import io
import json
import math

from PIL import Image

ROOT = os.path.abspath(os.join(os.path.dirname(__file__), "..", "..", ".."))
GLB_DIR = os.path.join(ROOT, "assets", "furnlib")
OUT = os.path.join(ROOT, "_texdump")


def read_glb(path):
    with open(path, "rb") as f:
        data = f.read()
    off, js, bin_ = 12, None, b""
    while off + 8 <= len(data):
        clen, ctype = struct.unpack("<II", data[off:off + 8])
        chunk = data[off + 8:off + 8 + clen]
        if ctype == 0x4E4F534A:
            js = json.loads(chunk.decode("utf-8"))
        elif ctype == 0x004E4942:
            bin_ = chunk
        off += 8 + clen
    return js, bin_


COMP = {5120: ("b", 1), 5121: ("B", 1), 5122: ("h", 2), 5123: ("H", 2),
        5125: ("I", 4), 5126: ("f", 4)}


def uv_range(js, bin_):
    """返回所有 primitive 的 TEXCOORD_0 包围盒。"""
    gmin = [float("inf")] * 2
    gmax = [float("-inf")] * 2
    for mesh in js.get("meshes", []):
        for prim in mesh.get("primitives", []):
            ti = prim.get("attributes", {}).get("TEXCOORD_0")
            if ti is None:
                continue
            acc = js["accessors"][ti]
            bv = js["bufferViews"][acc["bufferView"]]
            fmt, sz = COMP[acc["componentType"]]
            stride = bv.get("byteStride") or sz * 2
            base = bv.get("byteOffset", 0) + acc.get("byteOffset", 0)
            for i in range(min(acc["count"], 50000)):
                o = base + i * stride
                u, v = struct.unpack_from("<2%s" % fmt, bin_, o)
                gmin[0] = min(gmin[0], u); gmax[0] = max(gmax[0], u)
                gmin[1] = min(gmin[1], v); gmax[1] = max(gmax[1], v)
    if gmin[0] == float("inf"):
        return None
    return ([round(gmin[0], 3), round(gmin[1], 3)], [round(gmax[0], 3), round(gmax[1], 3)])


def dump(key):
    p = os.path.join(GLB_DIR, key + ".glb")
    if not os.path.exists(p):
        print(key, "MISSING")
        return
    js, bin_ = read_glb(p)
    bvs = js.get("bufferViews", [])
    os.makedirs(OUT, exist_ok=True)
    print("=" * 74)
    print("%s   uv=%s" % (key, uv_range(js, bin_)))
    texmap = {}
    for mi, m in enumerate(js.get("materials", [])):
        pbr = m.get("pbrMetallicRoughness", {})
        roles = []
        if pbr.get("baseColorTexture"):
            roles.append(("col", pbr["baseColorTexture"]["index"]))
        if pbr.get("metallicRoughnessTexture"):
            roles.append(("mr", pbr["metallicRoughnessTexture"]["index"]))
        if m.get("normalTexture"):
            roles.append(("nrm", m["normalTexture"]["index"]))
        if m.get("occlusionTexture"):
            roles.append(("ao", m["occlusionTexture"]["index"]))
        print("  mat[%d] %-20s roles=%s" % (mi, m.get("name", "?"), roles))
        for role, ti in roles:
            t = js["textures"][ti]
            si = t.get("source")
            if si is None:
                print("      %s -> texture has NO source" % role)
                continue
            texmap.setdefault(si, []).append((mi, role))
    for si, usage in sorted(texmap.items()):
        im = js["images"][si]
        bv = im.get("bufferView")
        if bv is None:
            print("  img%d EXTERNAL uri=%s" % (si, im.get("uri", "")[:60]))
            continue
        b = bvs[bv]
        blob = bin_[b.get("byteOffset", 0):b.get("byteOffset", 0) + b.get("byteLength", 0)]
        try:
            img = Image.open(io.BytesIO(blob)).convert("RGB")
            fn = os.path.join(OUT, "%s_img%d.png" % (key, si))
            img.save(fn)
            g = img.convert("L").histogram()
            mean = sum(i * c for i, c in enumerate(g)) / float(sum(g) or 1)
            std = (sum(((i - mean) ** 2) * c for i, c in enumerate(g)) / float(sum(g) or 1)) ** 0.5
            print("  img%d -> %s  roles=%s  mean=%.1f std=%.1f size=%s"
                  % (si, os.path.basename(fn), [u[1] for u in usage], mean, std, img.size))
        except Exception as e:
            print("  img%d DECODE FAIL %s" % (si, e))


if __name__ == "__main__":
    for k in (sys.argv[1:] or ["sofa", "armchair", "bed18", "diningTable", "wardrobe", "plant"]):
        dump(k)

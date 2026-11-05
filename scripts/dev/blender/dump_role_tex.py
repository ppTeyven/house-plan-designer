"""把 GLB 里内嵌的 baseColor 贴图导出成 png，肉眼判断角色对不对。

【为什么】role_audit 发现 diningTable / wardrobe / coffeeTable 这些
【应该是木头】的家具，材质角色却是 U_fabric_oat（布料）。
需要确认：GLB 内嵌的贴图是跟着角色走的（布），还是本来是木纹但角色被写错了？
角色写错 → 验收站和主程序都会把它当成布料渲染 → 餐桌变成布桌子。

用法：python dump_role_tex.py diningTable wardrobe coffeeTable nightstand
"""
import base64
import io
import json
import os
import struct
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
ACC = os.path.join(ROOT, "验收", "models")
OUT = os.path.join(ROOT, "assets", "_shots", "roletex")
os.makedirs(OUT, exist_ok=True)
CT_JSON = 0x4E4F534A
CT_BIN = 0x004E4942


def load_glb(path):
    blob = open(path, "rb").read()
    total = struct.unpack("<I", blob[8:12])[0]
    off = 12
    js = None
    binchunk = None
    while off + 8 <= min(total, len(blob)):
        clen, ctype = struct.unpack("<II", blob[off:off + 8])
        data = blob[off + 8:off + 8 + clen]
        if ctype == CT_JSON:
            js = json.loads(data.decode("utf-8"))
        elif ctype == CT_BIN:
            binchunk = data
        off += 8 + clen
    return js, binchunk, blob


def img_bytes(js, binchunk, blob, iidx):
    img = js["images"][iidx]
    if "bufferView" in img:
        bv = js["bufferViews"][img["bufferView"]]
        s = bv.get("byteOffset", 0)
        return binchunk[s:s + bv["byteLength"]]
    if "uri" in img:
        u = img["uri"]
        if u.startswith("data:"):
            return base64.b64decode(u.split(",", 1)[1])
        p = os.path.join(ACC, u)
        if os.path.exists(p):
            return open(p, "rb").read()
    return b""


targets = sys.argv[1:] or ["diningTable", "wardrobe", "coffeeTable", "nightstand",
                           "chair", "sofa"]
for t in targets:
    p = os.path.join(ACC, t + ".glb")
    if not os.path.exists(p):
        print("缺", t)
        continue
    js, binchunk, blob = load_glb(p)
    print("\n===== %s =====" % t)
    for mi, m in enumerate(js.get("materials", [])):
        pbr = m.get("pbrMetallicRoughness", {}) or {}
        bct = pbr.get("baseColorTexture")
        bc = pbr.get("baseColorFactor")
        print("  mat[%d] name=%-20s bcFactor=%s" % (mi, m.get("name"),
              [round(x, 3) for x in bc] if bc else None))
        if bct is not None:
            ti = bct["index"]
            src = js["textures"][ti].get("source")
            if src is None:
                print("        (no source)")
                continue
            data = img_bytes(js, binchunk, blob, src)
            if not data:
                print("        (no bytes)")
                continue
            out = os.path.join(OUT, "%s_mat%d.jpg" % (t, mi))
            with open(out, "wb") as f:
                f.write(data)
            try:
                from PIL import Image
                im = Image.open(io.BytesIO(data))
                im.load()
                small = im.convert("RGB").resize((24, 24))
                px = list(small.getdata())
                avg = [sum(c[i] for c in px) // len(px) for i in range(3)]
                print("        -> %s  %s  avgRGB=%s" % (os.path.basename(out), im.size, avg))
            except Exception as e:
                print("        -> saved %s (%s)" % (os.path.basename(out), e))

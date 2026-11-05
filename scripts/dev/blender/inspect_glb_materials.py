"""检查 GLB 内嵌材质定义：U_* 角色名 / 基色 / 是否带贴图引用 / 贴图 MIME。

乱码的可能来源：
  (a) 内嵌材质基色被写成乱码字符串
  (b) GLB 里带了贴图但验收站不解析（GLTFLoader 需要 GLB 内嵌 buffer 或外部 URI）
  (c) 材质名 U_* 没有被 app.js 映射，导致所有面用同一个默认材质
"""
import json
import os
import struct
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
GLB_DIR = os.path.join(ROOT, "assets", "furnlib")


def read_glb(path):
    with open(path, "rb") as f:
        data = f.read()
    total = struct.unpack("<III", data[:12])[2]
    off = 12
    js = None
    bin_ = b""
    while off + 8 <= min(total, len(data)):
        clen, ctype = struct.unpack("<II", data[off:off + 8])
        chunk = data[off + 8:off + 8 + clen]
        if ctype == 0x4E4F534A:
            js = json.loads(chunk.decode("utf-8"))
        elif ctype == 0x004E4942:
            bin_ = chunk
        off += 8 + clen
    return js, bin_


names = sys.argv[1:] or ["armchair", "sofa", "bed18", "diningTable", "wardrobe", "plant"]
for nm in names:
    p = os.path.join(GLB_DIR, nm + ".glb")
    if not os.path.exists(p):
        print("%-14s MISSING" % nm)
        continue
    js, bin_ = read_glb(p)
    mats = js.get("materials", [])
    print("=" * 70)
    print("%-14s materials=%d  images=%d  textures=%d  samplers=%d"
          % (nm, len(mats), len(js.get("images", [])), len(js.get("textures", [])),
             len(js.get("samplers", []))))
    for m in mats:
        pbr = m.get("pbrMetallicRoughness", {})
        bc = pbr.get("baseColorFactor")
        bcs = "[%.3f,%.3f,%.3f,%.3f]" % tuple(bc) if bc else "(default 1,1,1,1)"
        tex = pbr.get("baseColorTexture")
        mr = pbr.get("metallicRoughnessTexture")
        nm_ = pbr.get("normalTexture")
        ao = m.get("occlusionTexture")
        print("   name=%-18s base=%s  maps: col=%s rough=%s norm=%s ao=%s"
              % (m.get("name", "?"), bcs,
                 "Y" if tex else "-", "Y" if mr else "-", "Y" if nm_ else "-", "Y" if ao else "-"))
        print("        metallic=%s roughness=%s" % (pbr.get("metallicFactor"), pbr.get("roughnessFactor")))
    for im in js.get("images", [])[:4]:
        print("        image: uri=%s mime=%s bv=%s"
              % (im.get("uri", "")[:70], im.get("mimeType", ""), im.get("bufferView", "-")))



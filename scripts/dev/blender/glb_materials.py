"""检查 GLB 里的材质定义：有没有贴图、有没有 U_* 角色名、baseColor 是否异常。

用法：python glb_materials.py [glb名...]
"""
import json
import os
import struct
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
ACC = os.path.join(ROOT, "assets", "furnlib")


def load_glb(path):
    blob = open(path, "rb").read()
    total = struct.unpack("<I", blob[8:12])[0]
    off = 12
    js = None
    while off + 8 <= min(total, len(blob)):
        clen, ctype = struct.unpack("<II", blob[off:off + 8])
        if ctype == 0x4E4F534A:
            js = json.loads(blob[off + 8:off + 8 + clen].decode("utf-8"))
            break
        off += 8 + clen
    return js, blob


def summarize(js, blob):
    mats = js.get("materials", [])
    imgs = js.get("images", [])
    texs = js.get("textures", [])
    out = []
    for m in mats:
        pbr = m.get("pbrMetallicRoughness", {}) or {}
        bc = pbr.get("baseColorFactor")
        bct = pbr.get("baseColorTexture")
        met = pbr.get("metallicRoughnessTexture")
        nrm = m.get("normalTexture")
        occ = m.get("occlusionTexture")
        emi = m.get("emissiveFactor")
        out.append({
            "name": m.get("name", ""),
            "bc": [round(x, 3) for x in bc] if bc else None,
            "tex": [bool(bct), bool(met), bool(nrm), bool(occ)],
            "texIdx": (bct or {}).get("index"),
            "emi": emi,
            "alpha": m.get("alphaMode"),
        })
    return out, len(imgs), len(texs)


targets = sys.argv[1:] or ["mirror", "sofa", "bed12", "armchair", "bigPlant",
                           "barStool", "bedroomChair", "diningTable"]
for t in targets:
    p = os.path.join(ACC, t + ".glb")
    if not os.path.exists(p):
        print("缺 %s" % t)
        continue
    js, blob = load_glb(p)
    rows, nimg, ntex = summarize(js, blob)
    print("\n===== %s.glb  %.2f MB  images=%d textures=%d mats=%d ====="
          % (t, len(blob) / 1048576.0, nimg, ntex, len(rows)))
    for r in rows[:8]:
        print("   name=%-24s bc=%-22s tex(col/rough/nor/ao)=%s imgIdx=%s alpha=%s"
              % (r["name"][:24], r["bc"], r["tex"], r["texIdx"], r["alpha"]))
    if len(rows) > 8:
        print("   ... 共 %d 个材质" % len(rows))

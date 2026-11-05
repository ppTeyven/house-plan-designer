"""诊断：ph_all_models.json 的 w/d/h 是【局部】还是【世界】测量？

【为什么要查】
  挑选器用 json 的尺寸算形变，构建时用 GLB 世界包围盒。
  两者不一致（13/40）→ 挑选通过、构建被拒。
  必须查明 JSON 数据的来源口径，才能统一。
"""
import os
import sys
import json
import struct
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
CACHE = os.path.join(ROOT, "assets", "_asset_cache")
EXT = os.path.join(ROOT, "assets", "external")

import normalize_glb as NG
from measure_glb import _read_gltf


def local_dims(gltf_path):
    """只取 accessor.min/max（网格局部坐标），不加节点变换。"""
    gltf, bufs = _read_gltf(gltf_path)
    accs = gltf.get("accessors", [])
    mn = [1e9] * 3
    mx = [-1e9] * 3
    for m in gltf.get("meshes", []):
        for p in m.get("primitives", []):
            if "POSITION" not in p.get("attributes", {}):
                continue
            a = accs[p["attributes"]["POSITION"]]
            if "min" not in a:
                continue
            for i in range(3):
                mn[i] = min(mn[i], a["min"][i])
                mx[i] = max(mx[i], a["max"][i])
    return [round((mx[i] - mn[i]) * 1000) for i in range(3)]


def world_dims(glb):
    js, _ = NG.read_glb(glb)
    mn, mx = NG.world_bbox(js)
    return [round((mx[0] - mn[0]) * 1000), round((mx[2] - mn[2]) * 1000),
            round((mx[1] - mn[1]) * 1000)]


def main():
    with open(os.path.join(EXT, "ph_all_models.json"), encoding="utf-8-sig") as f:
        allm = {m["id"]: m for m in json.load(f)}

    ids = ["modern_coffee_table_01", "chinese_cabinet", "vintage_cabinet_01",
           "Sofa_01", "metal_tool_chest", "brass_diya_lantern"]
    print("%-26s %-22s %-22s %-22s" % ("id", "json(w,d,h)", "局部", "世界"))
    print("-" * 100)
    for rid in ids:
        raw = os.path.join(CACHE, "raw", rid + ".glb")
        gd = os.path.join(CACHE, "polyhaven", rid)
        gltf = None
        if os.path.isdir(gd):
            for fn in os.listdir(gd):
                if fn.endswith(".gltf"):
                    gltf = os.path.join(gd, fn)
                    break
        rec = allm.get(rid, {})
        js = [rec.get("w"), rec.get("d"), rec.get("h")]
        loc = local_dims(gltf) if gltf else None
        wor = world_dims(raw) if os.path.exists(raw) else None
        print("%-26s %-22s %-22s %-22s" % (rid, js, loc, wor))


if __name__ == "__main__":
    main()

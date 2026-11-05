"""探测 GLB 里 TEXCOORD_0 的真实质量（UV 覆盖率 / 是否退化）。

【为什么需要】
  决定"能不能直接给几何生成的白模贴真实扫描图"：
  · UV 跨度接近 1.0 → 贴图铺满整个件，视觉正常
  · UV 跨度接近 0   → 所有三角形挤在贴图同一个像素里 → 看起来就是纯色/"乱码"
  · 没有 UV          → 根本没法贴图

用法：python probe_uv.py
"""
import array
import collections
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
ACC = os.path.join(ROOT, "验收", "models")

import normalize_glb as NG

COMP_SIZE = {5120: 1, 5121: 1, 5122: 2, 5123: 2, 5125: 4, 5126: 4}
COMP_FMT = {5120: "b", 5121: "B", 5122: "h", 5123: "H", 5125: "i", 5126: "f"}
TYPE_NCOMP = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4}


def read_accessor(js, bin_data, idx):
    """读取 accessor 的数值（只支持有 bufferView 的）。"""
    acc = js["accessors"][idx]
    bv_idx = acc.get("bufferView")
    if bv_idx is None:
        return None
    bv = js["bufferViews"][bv_idx]
    comp = acc["componentType"]
    ncomp = TYPE_NCOMP.get(acc["type"], 1)
    size = COMP_SIZE[comp]
    start = bv.get("byteOffset", 0) + acc.get("byteOffset", 0)
    count = acc["count"] * ncomp
    arr = array.array(COMP_FMT[comp])
    arr.frombytes(bin_data[start:start + count * size])
    return arr, ncomp


def probe(path):
    """返回该 GLB 的 UV 统计。"""
    js, bin_data = NG.read_glb(path)
    prims = 0
    no_uv = 0
    spans = []
    for mesh in js.get("meshes", []):
        for prim in mesh.get("primitives", []):
            prims += 1
            ti = prim.get("attributes", {}).get("TEXCOORD_0")
            if ti is None:
                no_uv += 1
                continue
            got = read_accessor(js, bin_data, ti)
            if got is None:
                no_uv += 1
                continue
            arr, ncomp = got
            if len(arr) < ncomp:
                no_uv += 1
                continue
            us = [arr[i * ncomp] for i in range(len(arr) // ncomp)]
            vs = [arr[i * ncomp + 1] for i in range(len(arr) // ncomp)]
            if not us:
                no_uv += 1
                continue
            spans.append(max(max(us) - min(us), max(vs) - min(vs)))
    return {
        "prims": prims,
        "no_uv": no_uv,
        "avg_span": (sum(spans) / len(spans)) if spans else 0.0,
        "min_span": min(spans) if spans else 0.0,
        "max_span": max(spans) if spans else 0.0,
    }


def main():
    man = json.load(open(os.path.join(ACC, "manifest.json"), encoding="utf-8"))
    hist = collections.defaultdict(list)
    no_uv_models = []
    degenerate = []
    for it in man["items"]:
        key = it["key"]
        st = probe(os.path.join(ACC, key + ".glb"))
        if st["prims"] == 0:
            continue
        if st["no_uv"] > 0:
            no_uv_models.append((key, st["no_uv"], st["prims"]))
        bucket = round(st["avg_span"], 2)
        hist[bucket].append(key)
        if st["avg_span"] < 0.05:
            degenerate.append((key, round(st["avg_span"], 4)))

    print("=== UV 跨度分布（1.0 = 贴图铺满整个件）===")
    for bucket in sorted(hist):
        print("  span~%-6.2f : %3d 个  %s"
              % (bucket, len(hist[bucket]), hist[bucket][:6]))
    print()
    print("缺 UV 的模型: %d" % len(no_uv_models))
    for row in no_uv_models[:20]:
        print("   ", row)
    print("UV 退化(span<0.05)的模型: %d" % len(degenerate))
    for row in degenerate[:30]:
        print("   ", row)


if __name__ == "__main__":
    main()

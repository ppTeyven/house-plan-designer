"""校验 GLB 内 metallicRoughnessTexture 的【通道语义】是否正确。

【glTF 2.0 规范（硬事实）】
  metallicRoughnessTexture:  G = roughness, B = metalness
  occlusionTexture:          R = AO
  baseColorTexture:          RGB = albedo(sRGB), A = alpha

【为什么必须查】
  如果把【单通道的 roughness 灰度图】直接挂到 metallicRoughnessTexture，
  three.js 会读 G 通道（灰度图 G=R=灰度值 → 粗糙度尚可）
  但读 B 通道当金属度 → 同一张灰度图的 B 也是灰度值
  → 粗糙度 0.3 的地方金属度也 0.3 → 【半金属的脏塑料感】
  → 画面看起来"脏、噪、不像材质"= 用户说的"乱码"。

  正确做法：把 AO(R) / roughness(G) / metalness(B) 打包成 ORM 三通道图。

用法：python verify_mr_channels.py
"""
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
ACC = os.path.join(ROOT, "assets", "furnlib")

import normalize_glb as NG

try:
    import numpy as np
    from PIL import Image
except ImportError:
    np = None
    Image = None


def texture_bytes(js, bin_data, tex_index):
    tex = js["textures"][tex_index]
    src = tex.get("source")
    im = js["images"][src]
    bv = js["bufferViews"][im["bufferView"]]
    off = bv.get("byteOffset", 0)
    return bin_data[off:off + bv.get("byteLength", 0)]


def analyse(path):
    """返回该模型所有材质的通道统计。"""
    js, bin_data = NG.read_glb(path)
    out = []
    for m in js.get("materials", []):
        pbr = m.get("pbrMetallicRoughness") or {}
        row = {"name": m.get("name", ""), "mrTex": None, "metalF": pbr.get("metallicFactor"),
               "roughF": pbr.get("roughnessFactor"), "norm": "normalTexture" in m,
               "occ": "occlusionTexture" in m}
        idx = pbr.get("metallicRoughnessTexture", {}).get("index")
        if idx is not None and idx < len(js.get("textures", [])):
            if Image is None or np is None:
                row["mrTex"] = "?"
                out.append(row)
                continue
            data = texture_bytes(js, bin_data, idx)
            try:
                with Image.open(io.BytesIO(data)) as im:
                    arr = np.asarray(im.convert("RGB"), dtype=np.float32) / 255.0
                r = arr[:, :, 0]
                g = arr[:, :, 1]
                b = arr[:, :, 2]
                # 若三通道几乎相同 → 这是一张灰度图被直接当 ORM 用
                same = float(np.abs(r - g).mean() + np.abs(g - b).mean()) / 2.0
                row["mrTex"] = {
                    "R": round(float(r.mean()), 3),
                    "G": round(float(g.mean()), 3),
                    "B": round(float(b.mean()), 3),
                    "rg_diff": round(float(np.abs(r - g).mean()), 4),
                    "gb_diff": round(float(np.abs(g - b).mean()), 4),
                    "is_grayscale": same < 0.02,
                    "metal_from_B": round(float(b.mean()), 3),
                    "rough_from_G": round(float(g.mean()), 3),
                }
            except Exception as exc:
                row["mrTex"] = "decode_fail:%s" % str(exc)[:40]
        out.append(row)
    return out


def main():
    man = json.load(open(os.path.join(ACC, "manifest.json"), encoding="utf-8"))
    grayscale = []
    ok = 0
    total = 0
    for it in man["items"]:
        key = it["key"]
        path = os.path.join(ACC, key + ".glb")
        if not os.path.exists(path):
            continue
        for row in analyse(path):
            if row["mrTex"] in (None, "?"):
                continue
            total += 1
            info = row["mrTex"]
            if isinstance(info, dict):
                if info.get("is_grayscale"):
                    grayscale.append((key, row["name"], info))
                else:
                    ok += 1
            else:
                grayscale.append((key, row["name"], info))

    print("带 metallicRoughnessTexture 的材质: %d 个" % total)
    print("  通道语义正确（R/G/B 三通道有差异）: %d" % ok)
    print("  疑似灰度图直挂（金属度/粗糙度串通道）: %d" % len(grayscale))
    for key, name, info in grayscale[:30]:
        if isinstance(info, dict):
            print("   %-18s %-20s R=%.3f G=%.3f B=%.3f  rough(G)=%.3f metal(B)=%.3f"
                  % (key, name, info["R"], info["G"], info["B"],
                     info["rough_from_G"], info["metal_from_B"]))
        else:
            print("   %-18s %-20s %s" % (key, name, info))


if __name__ == "__main__":
    main()

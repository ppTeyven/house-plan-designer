"""【对比审计】当前 GLB vs PolyHaven 原始资源 —— 检查原始扫描贴图是否被覆盖。

【为什么必须查】
  历史上有脚本用"通用角色注入"把 PH 原始扫描贴图冲掉，
  换成 ambientCG 通用贴图 —— 材质名对，但贴图不是这个模型自己的。
  这属于"拿贴图糊弄"，必须查证是否还在。

判定：
  · 原资源有 N 张图，当前 0 张   → 被冲掉了（严重）
  · 原资源有 N 张，当前 M 张    → 看纹理下标集合是否有交集
    有交集 → 原始贴图还在（好）
    无交集 → 被整体替换（严重）
"""
import json
import os
import struct
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
ACC = os.path.join(ROOT, "assets", "furnlib")
CACHE_RAW = os.path.join(ROOT, "assets", "_asset_cache", "raw")
AMAP = os.path.join(ROOT, "assets", "_asset_cache", "asset_map.json")

CT_JSON = 0x4E4F534A
CT_BIN = 0x004E4942


def load_glb(path):
    with open(path, "rb") as f:
        blob = f.read()
    off = 12
    js, bin_ = None, b""
    while off + 8 <= len(blob):
        clen, ctype = struct.unpack("<II", blob[off:off + 8])
        data = blob[off + 8:off + 8 + clen]
        if ctype == CT_JSON:
            js = json.loads(data.decode("utf-8"))
        elif ctype == CT_BIN:
            bin_ = data
        off += 8 + clen
    return js, bin_


def img_bytes(js, bin_):
    """返回 {image_index: (mime, bytes)}"""
    out = {}
    for i, im in enumerate(js.get("images") or []):
        bv = im.get("bufferView")
        mime = im.get("mimeType", "?")
        if bv is None:
            out[i] = (mime, b"")
            continue
        v = js["bufferViews"][bv]
        off = v.get("byteOffset", 0)
        out[i] = (mime, bin_[off:off + v["byteLength"]])
    return out


def tex_img_set(js):
    """材质用到的 image 索引集合"""
    used = set()
    for m in js.get("materials") or []:
        pbr = m.get("pbrMetallicRoughness") or {}
        for slot in (pbr.get("baseColorTexture"),
                     pbr.get("metallicRoughnessTexture"),
                     m.get("normalTexture"), m.get("occlusionTexture")):
            if slot:
                t = (js.get("textures") or [])[slot["index"]]
                if "source" in t:
                    used.add(t["source"])
    return used


def main():
    amap = json.load(open(AMAP, encoding="utf-8"))
    man = json.load(open(os.path.join(ACC, "manifest.json"), encoding="utf-8"))
    rows = []
    for it in man["items"]:
        key = it["key"]
        res = (amap.get(key) or {}).get("resource")
        if not res:
            continue
        rawp = os.path.join(CACHE_RAW, res + ".glb")
        curp = os.path.join(ACC, key + ".glb")
        if not (os.path.exists(rawp) and os.path.exists(curp)):
            continue
        try:
            rjs, rbin = load_glb(rawp)
            cjs, cbin = load_glb(curp)
        except Exception as e:
            rows.append((key, res, "ERR %s" % e))
            continue
        rimgs = img_bytes(rjs, rbin)
        cimgs = img_bytes(cjs, cbin)
        rused = tex_img_set(rjs)
        cused = tex_img_set(cjs)
        rhash = {i: hash(b) for i, (m, b) in rimgs.items()}
        chash = {i: hash(b) for i, (m, b) in cimgs.items()}
        rh = {rhash[i] for i in rused}
        ch = {chash[i] for i in cused}
        keep = len(rh & ch)
        lost = len(rh - ch)
        rows.append((key, res, "原始用图%d 当前用图%d 保留%d 丢失%d"
                     % (len(rused), len(cused), keep, lost)))

    print("=== PH 资源原始贴图保留情况 (%d 项) ===" % len(rows))
    lost_items = [r for r in rows if "丢失0" not in r[2] and "ERR" not in r[2]]
    print("  原始贴图完全丢失: %d" % len(lost_items))
    for k, res, s in rows:
        print("  %-20s %-34s %s" % (k, res[:34], s))


if __name__ == "__main__":
    main()

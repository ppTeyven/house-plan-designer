"""测量"摆位修正后"的资源尺寸 —— 供挑选器使用。

【为什么需要】
  measure_ph.py 测的是【原样】的资源包围盒。
  但有些资源的零件是侧躺/散落的（如 metal_trash_can 的盖子侧躺 75°），
  原样包围盒高 1185mm —— 摆正后只有 977mm。
  挑选器若用原样尺寸判定，会把"摆正后其实很合适"的好资源误杀
  （trashBin 就是这么被误杀的 → 最后只能退回几何生成）。

  所以这里额外测一份"摆正后"的尺寸，写进 ph_dims_posed.json，
  挑选器优先用这份。

用法：python measure_posed.py
"""
import os
import sys
import json

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
CACHE = os.path.join(ROOT, "assets", "_asset_cache")

import normalize_glb as NG
import fit_item as FI
from pose_fix import POSE_FIX

RAW = os.path.join(CACHE, "raw")
OUT = os.path.join(CACHE, "ph_dims_posed.json")


def main():
    dims = json.load(open(os.path.join(CACHE, "ph_dims.json"), encoding="utf-8"))
    out = {}
    for rid, pose in POSE_FIX.items():
        raw = os.path.join(RAW, rid + ".glb")
        if not os.path.exists(raw):
            print("跳过 %s —— raw 不存在" % rid)
            continue
        js, _ = NG.read_glb(raw)
        keep = set(pose["keep"]) if pose.get("keep") else None
        if keep:
            f = FI._filter_nodes(js, keep)
            if f:
                js = f
        if pose.get("transform"):
            js = FI._apply_node_transforms(js, pose["transform"])
        mn, mx = NG.world_bbox(js)
        out[rid] = {
            "w": round((mx[0] - mn[0]) * 1000),
            "d": round((mx[2] - mn[2]) * 1000),
            "h": round((mx[1] - mn[1]) * 1000),
        }
        old = dims.get(rid)
        print("%-24s 原样=%s → 摆正=%s" % (
            rid,
            [old["w"], old["d"], old["h"]] if old else "?",
            [out[rid]["w"], out[rid]["d"], out[rid]["h"]]))

    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print("\n写入", OUT, "（%d 项）" % len(out))


if __name__ == "__main__":
    main()

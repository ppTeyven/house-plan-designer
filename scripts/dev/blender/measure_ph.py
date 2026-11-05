"""测量 Polyhaven 资源的世界空间尺寸 —— 作为挑选器的唯一尺寸真源。

【为什么要重测，而不用 ph_all_models.json】
  实测发现那份 JSON 的轴序不一致：
    modern_coffee_table_01  json=[1202,600,390]  局部=[600,390,1202]  世界=[600,1202,390]
    chinese_cabinet         json=[1262,545,2872]  局部=[1262,3669,696] 世界=[1262,696,3669]
    Sofa_01                 json=[1571,658,797]   局部=[1571,797,658]  世界=[1571,658,797]
  —— 同一份文件里，有的按 Y-up 记录，有的按 Z-up 记录。
  用它算形变 → 13/40 的资源"挑选时合格、构建时被拒"。
  【世界空间包围盒】是唯一无歧义的口径：glTF 约定 Y=高。
  所以这里统一从 GLB 实测，结果与 fit_item 的判定完全对齐。

【输出】assets/_asset_cache/ph_dims.json
  { model_id: {"w":…, "d":…, "h":…, "tri":…} }   单位 mm
"""
import os
import sys
import json

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
CACHE = os.path.join(ROOT, "assets", "_asset_cache")
EXT = os.path.join(ROOT, "assets", "external")
PH_DIR = os.path.join(CACHE, "polyhaven")
RAW = os.path.join(CACHE, "raw")

import asset_fetch as AF
import normalize_glb as NG

OUT = os.path.join(CACHE, "ph_dims.json")


def ensure_raw(rid):
    """确保 raw/<id>.glb 存在，返回路径或 None。"""
    raw = os.path.join(RAW, rid + ".glb")
    if os.path.exists(raw):
        return raw
    src_dir = os.path.join(PH_DIR, rid)
    if not os.path.isdir(src_dir):
        return None
    gltf = None
    for fn in os.listdir(src_dir):
        if fn.endswith(".gltf"):
            gltf = os.path.join(src_dir, fn)
            break
    if not gltf:
        return None
    try:
        AF.gltf_to_glb(gltf, None, raw)
        return raw
    except Exception:
        return None


def main():
    with open(os.path.join(EXT, "ph_all_models.json"), encoding="utf-8-sig") as f:
        models = json.load(f)

    out = {}
    missing = []
    for i, m in enumerate(models):
        rid = m["id"]
        raw = ensure_raw(rid)
        if not raw:
            missing.append(rid)
            continue
        try:
            js, _ = NG.read_glb(raw)
            mn, mx = NG.world_bbox(js)
            out[rid] = {
                "w": round((mx[0] - mn[0]) * 1000),
                "d": round((mx[2] - mn[2]) * 1000),
                "h": round((mx[1] - mn[1]) * 1000),
                "tri": NG.count_tris(js),
                "cats": m.get("cats", ""),
            }
        except Exception as e:
            missing.append("%s(%s)" % (rid, str(e)[:40]))
        if (i + 1) % 50 == 0:
            print("  %d/%d" % (i + 1, len(models)))

    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print()
    print("测量成功 %d / 失败 %d" % (len(out), len(missing)))
    print("写入", OUT)
    if missing:
        print("失败:", missing[:10])

    # ---- 与旧 JSON 对账 ----
    old = {m["id"]: m for m in models}
    diff = 0
    for rid, v in out.items():
        o = old.get(rid)
        if not o:
            continue
        if [o.get("w"), o.get("d"), o.get("h")] != [v["w"], v["d"], v["h"]]:
            diff += 1
    print()
    print("与 ph_all_models.json 记录不一致: %d / %d（说明旧文件轴序混用）"
          % (diff, len(out)))


if __name__ == "__main__":
    main()

"""全量普查 Polyhaven 521 个模型的真实几何数据（面数/尺寸/材质）。

【为什么要全量普查】
  项目验收标准（make_manifest.py SPEC）要求：
    沙发 ≥60,000 三角面、床 ≥60,000、餐椅 ≥15,000 ...
  但 Polyhaven 的分辨率（1k/2k/4k）只影响【贴图】，几何是固定的。
  所以必须实测每个模型的面数，不能凭"下载量大"就以为面数高。

【产出】
  assets/_asset_cache/ph_survey.json
    { model_id: {tris, verts, dims_mm, mats, bytes, src} }
  供映射脚本挑选：只选面数达标的。

用法：python survey_polyhaven.py
"""
import os
import sys
import json
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
CACHE = os.path.join(ROOT, "assets", "_asset_cache")

import asset_fetch as AF

OUT = os.path.join(CACHE, "ph_survey.json")


def main():
    models = AF.ph_assets("models")
    print("Polyhaven 模型总数:", len(models))

    # 家具/室内相关关键词（用于标注用途）
    FURN = ("chair", "sofa", "table", "desk", "bed", "cabinet", "shelf",
            "stool", "bench", "lamp", "light", "rug", "curtain", "plant",
            "pot", "vase", "door", "window", "fence", "gate", "wall",
            "floor", "ceiling", "stairs", "stair", "picture", "frame",
            "clock", "toilet", "sink", "fridge", "oven", "stove", "washer",
            "microwave", "mirror", "towel", "heater", "vent", "sink")

    results = {}
    t0 = time.time()
    fails = []
    for i, mid in enumerate(sorted(models)):
        try:
            gltf_path, files = AF.ph_download_gltf(mid, resolution="1k")
            glb = os.path.join(CACHE, "survey", mid + ".glb")
            if not os.path.exists(glb):
                AF.gltf_to_glb(gltf_path, files, glb)
            sys.path.insert(0, HERE)
            from inspect_glb import stats
            st = stats(glb)
            results[mid] = {
                "tris": st["triangles"],
                "verts": st["vertices"],
                "dims_mm": [round(v * 1000) for v in st["dims"]],
                "mats": st["materials"],
                "bytes": os.path.getsize(glb),
                "is_furniture": any(k in mid.lower() for k in FURN),
            }
            os.remove(glb)
        except Exception as e:
            fails.append((mid, str(e)[:120]))
        if (i + 1) % 40 == 0:
            print("  %d/%d  (%.0fs)" % (i + 1, len(models), time.time() - t0))

    print()
    print("成功 %d / 失败 %d  (%.0fs)" % (len(results), len(fails), time.time() - t0))
    for mid, e in fails[:10]:
        print("   FAIL", mid, e)

    os.makedirs(CACHE, exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=1)
    print("写入", OUT)

    # ---- 家具类按面数排序 ----
    furn = {k: v for k, v in results.items() if v["is_furniture"]}
    print()
    print("=== 家具相关 %d 个，按面数降序 ===" % len(furn))
    for k, v in sorted(furn.items(), key=lambda x: -x[1]["tris"])[:60]:
        print("  %-38s tris=%-8s dims=%s mats=%d"
              % (k, format(v["tris"], ","), v["dims_mm"], len(v["mats"])))

    print()
    print("=== 面数分档 ===")
    bands = [(0, 5000), (5000, 15000), (15000, 60000), (60000, 10 ** 9)]
    for lo, hi in bands:
        n = sum(1 for v in results.values() if lo <= v["tris"] < hi)
        print("  %6d ~ %-10s : %d" % (lo, hi if hi < 10 ** 8 else "∞", n))


if __name__ == "__main__":
    main()

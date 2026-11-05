"""下载挑选器候选所需的 Polyhaven 资源（1k gltf）。

【为什么只下候选】
  全量 521 个资源全部下载体积很大；
  而挑选器只需要那些【通过类别+关键词门控】的候选。
  先按门控筛出候选，再只下载这部分 —— 省时省空间。

【幂等】
  已下载的目录会跳过；中断后可重跑续传。
"""
import os
import sys
import json
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
CACHE = os.path.join(ROOT, "assets", "_asset_cache")
EXT = os.path.join(ROOT, "assets", "external")

import asset_fetch as AF
from pick_resources import CLASS_OK
from pick_resources_v5 import keyword_hit


def main():
    with open(os.path.join(EXT, "ph_all_models.json"), encoding="utf-8-sig") as f:
        models = json.load(f)

    # ---- 筛出候选 ----
    cands = set()
    for m in models:
        for key, allow in CLASS_OK.items():
            if not allow:
                continue
            cats = set(c.strip() for c in str(m.get("cats", "")).split(",") if c.strip())
            if not (cats & set(allow)):
                continue
            kw, _ = keyword_hit(key, m)
            if kw:
                cands.add(m["id"])
                break

    print("门控候选 %d 个（总量 %d）" % (len(cands), len(models)))

    ok = fail = skip = 0
    t0 = time.time()
    for i, rid in enumerate(sorted(cands)):
        dest_dir = os.path.join(CACHE, "polyhaven", rid)
        has = os.path.isdir(dest_dir) and any(
            fn.endswith(".gltf") for fn in os.listdir(dest_dir))
        if has:
            skip += 1
            continue
        try:
            AF.ph_download_gltf(rid, resolution="1k")
            ok += 1
        except AF.FetchError as e:
            fail += 1
            print("  FAIL %-32s %s" % (rid, e.message[:60]))
        if (i + 1) % 25 == 0:
            print("  %d/%d  新装 %d / 已有 %d / 失败 %d  (%.0fs)"
                  % (i + 1, len(cands), ok, skip, fail, time.time() - t0))

    print()
    print("完成：新装 %d / 已存在 %d / 失败 %d  (%.0fs)"
          % (ok, skip, fail, time.time() - t0))


if __name__ == "__main__":
    main()

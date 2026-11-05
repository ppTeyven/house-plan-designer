"""校验 ambientCG assetId 是否真实存在 —— 不允许凭记忆断言资源存在。

【为什么必须校验】
  fetch_textures.py 里的 assetId 是我按 ambientCG 的命名规则推断的。
  手册第 3 条：禁止凭记忆断言事实。资源不存在 = 下载 404 = 静默失败。
  所以批量下载前，先逐个查 API 确认。

用法：python verify_texture_ids.py
"""
import os
import sys
import json
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import asset_fetch as AF
from fetch_textures import TEXTURE_SETS


def main():
    ok, bad = [], []
    for name, spec in TEXTURE_SETS.items():
        aid = spec["id"]
        try:
            info = AF.acg_detail(aid)
            maps = info.get("maps") or []
            dl = info.get("downloadFolders") or {}
            variants = []
            for cat in dl.values():
                for fmt in cat.get("downloadFiletypeCategories", {}).values():
                    for d in fmt.get("downloads", []):
                        variants.append(d.get("fileName"))
            has_2k_jpg = any(v and v.endswith("_2K-JPG.zip") for v in variants)
            print("  %-22s %-16s OK  maps=%-45s 2K-JPG=%s"
                  % (name, aid, ",".join(maps), has_2k_jpg))
            ok.append((name, aid, maps, has_2k_jpg))
        except AF.FetchError as e:
            print("  %-22s %-16s FAIL %s" % (name, aid, e.message[:70]))
            bad.append((name, aid, e.code))
        time.sleep(0.25)

    print()
    print("存在 %d / 不存在 %d" % (len(ok), len(bad)))
    if bad:
        print("=== 无效 ID（需替换）===")
        for n, a, c in bad:
            print("   %-22s %-16s %s" % (n, a, c))

    # 输出可用清单，供下游自动替换
    dest = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "_texture_valid.json")
    with open(dest, "w", encoding="utf-8") as f:
        json.dump({"ok": [o[1] for o in ok], "bad": [b[1] for b in bad]},
                  f, ensure_ascii=False, indent=1)
    print("写入", dest)


if __name__ == "__main__":
    main()

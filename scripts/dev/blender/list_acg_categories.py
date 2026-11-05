"""从 ambientCG 真实目录里挑选替换用的 assetId（不靠猜）。

【为什么】
  verify_texture_ids.py 查出 8 个 ID 不存在（我按命名规则推断的）。
  正确做法是查 ambientCG 的真实分类列表，从中选出对应用途的材质，
  而不是继续猜 ID。

【查询方式】
  api/v2/full_json?type=Material&category=<分类名>
  分类名从 API 返回的 displayCategory 字段聚合而来。

用法：python list_acg_categories.py [关键字]
"""
import os
import sys
import json
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import asset_fetch as AF


def categories():
    """聚合 ambientCG 全库的 displayCategory。"""
    cats = defaultdict(list)
    offset = 0
    limit = 100
    total = None
    while True:
        url = ("https://ambientcg.com/api/v2/full_json?type=Material"
               "&limit=%d&offset=%d" % (limit, offset))
        data = AF._http_json(url)
        assets = data.get("foundAssets", [])
        if not assets:
            break
        for a in assets:
            c = a.get("displayCategory") or "Uncategorized"
            cats[c].append((a["assetId"], a.get("downloadCount", 0),
                            ",".join(a.get("maps") or [])))
        offset += limit
        if total is None:
            total = data.get("numberOfResults", 0)
        if offset >= total:
            break
    return cats, total


def main():
    kw = sys.argv[1] if len(sys.argv) > 1 else None
    cats, total = categories()
    print("ambientCG Material 总数:", total)
    print("分类数:", len(cats))
    print()

    keys = sorted(cats, key=lambda c: -len(cats[c]))
    for c in keys:
        if kw and kw.lower() not in c.lower():
            continue
        ids = sorted(cats[c], key=lambda x: -x[1])
        print("== %s (%d) ==" % (c, len(cats[c])))
        for aid, dl, maps in ids[:14]:
            print("   %-16s dl=%-7s maps=%s" % (aid, dl, maps))
        print()

    # 存一份供挑选
    dest = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "_acg_categories.json")
    with open(dest, "w", encoding="utf-8") as f:
        json.dump({c: cats[c] for c in cats}, f, ensure_ascii=False, indent=1)
    print("写入", dest)


if __name__ == "__main__":
    main()

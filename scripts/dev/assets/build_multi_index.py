"""多源资源【全量索引】：把所有源里可下载的模型一次性抓下来存成本地索引。

【为什么重写】
旧版 build_gap_map.py 是"每个 type 打一次搜索 → 命中即用"，实测两个硬伤：
  ① 聚合 API 3d.shep.bot 在并发下持续 503（无重试时 ~1/4 请求直接失败）
  ② 一次查询只看前 25~30 条 → 大量 type 明明有货却搜不到
     （例：'rug' 只搜到 26 条，其中真正可用的 Area Rug 排在第 3 位就命中了，
       但 'round rug'、'wool rug' 等不同词会搜出完全不同的结果集，
       单次搜索 = 只能看到源里的一个切片）

【新做法】
  ① 用 ?providers=<逗号分隔> 定向检索，把结果混排问题彻底消除
     （实测 providers=grab3d 只返回 grab3d 的资产，排序稳定、可穷举）
  ② 【广撒网】：用一份覆盖全品类语义的检索词表 × 每个有 model 能力的源，
     把每个源能给出的模型全部拉下来，合并去重，存成本地索引
  ③ 之后所有匹配都在【本地索引】上做 —— 零网络请求、零 503、可反复调参

【输出】
  assets/external/multi_index.json
    [ {id, provider, nativeId, title, license, commercialUse, formats,
       polyCount, tags, categories, url, thumb} ]

用法：
  python build_multi_index.py                # 全量抓取
  python build_multi_index.py --providers kenney,grab3d
  python build_multi_index.py --skip-existing
"""
import argparse
import concurrent.futures as cf
import json
import os
import random
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
EXT = os.path.join(ROOT, "assets", "external")
INDEX = os.path.join(EXT, "multi_index.json")
UA = "HousePlannerAssetFetcher/1.0"
BASE = "https://3d.shep.bot/v1"

# --------------------------------------------------------------------
# HTTP（带指数退避，扛住 503）
# --------------------------------------------------------------------
_lock = threading.Lock()
_stats = {"req": 0, "err": 0, "hits": 0}


def _raw_get(url, timeout=60):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def get_json(url, timeout=60, retries=6):
    last = None
    for i in range(retries):
        try:
            out = _raw_get(url, timeout=timeout)
            with _lock:
                _stats["req"] += 1
            return out
        except urllib.error.HTTPError as e:
            last = e
            if e.code not in (429, 500, 502, 503, 504):
                break
        except Exception as e:
            last = e
        delay = min(20.0, 1.4 * (2 ** i)) + random.uniform(0, 1.2)
        time.sleep(delay)
    with _lock:
        _stats["err"] += 1
    raise last if last else RuntimeError("get failed: %s" % url)


# --------------------------------------------------------------------
# 检索词表：覆盖验收目录 158 个 type 的语义空间
# --------------------------------------------------------------------
TERMS = [
    # 家具主体
    "sofa", "loveseat", "sectional sofa", "armchair", "lounge chair",
    "accent chair", "chaise", "ottoman", "footstool", "stool", "bar stool",
    "bench", "dining chair", "office chair", "desk", "office desk",
    "conference table", "meeting table", "dining table", "coffee table",
    "side table", "console table", "nightstand", "bed", "bunk bed",
    "wardrobe", "closet", "cabinet", "sideboard", "bookshelf", "shelf",
    "chest of drawers", "dresser", "tv cabinet", "storage cabinet",
    "kitchen counter", "kitchen island", "kitchen cabinet", "sink",
    "bathroom sink", "washbasin", "toilet", "bathtub", "shower",
    "mirror", "lamp", "floor lamp", "table lamp", "chandelier", "pendant light",
    "wall lamp", "light fixture", "rug", "carpet", "curtain", "drape",
    "pillow", "cushion", "blanket", "vase", "plant", "potted plant",
    "painting", "picture frame", "wall art", "clock", "tv", "television",
    "refrigerator", "freezer", "dishwasher", "microwave", "oven", "stove",
    "range hood", "coffee machine", "espresso machine", "kettle", "toaster",
    "washing machine", "dryer", "air purifier", "vacuum cleaner", "fan",
    "radiator", "air conditioner", "water heater", "boiler", "fireplace",
    "projector", "speaker", "printer", "piano", "billiards table",
    "pool table", "treadmill", "exercise bike", "yoga mat", "aquarium",
    "fish tank", "sauna", "trash bin", "garbage can", "coat rack", "hat stand",
    "clothes rack", "laundry basket", "cat tree", "pet bed", "bird cage",
    "water dispenser", "water cooler", "fire extinguisher", "smoke detector",
    "whiteboard", "mirror cabinet", "towel rail", "towel rack", "soap dispenser",
    "bathroom vanity", "bidet", "urinal", "squat toilet", "shower curtain",
    "shower head", "faucet", "tap", "kitchen appliance", "blender",
    "router", "wifi access point", "ceiling speaker", "air vent", "vent grille",
    "smoke alarm", "fire alarm", "door", "door frame", "window", "stairs",
    "staircase", "railing", "balustrade", "elevator", "garage shelf",
    "workbench", "toolbox", "tool cabinet", "stage", "platform", "step",
    "fence", "gate", "carport", "garage", "pergola", "gazebo",
    "parasol", "garden umbrella", "sun lounger", "deck chair", "hammock",
    "swing", "bbq", "grill", "barbecue", "fire pit", "water feature",
    "fountain", "swimming pool", "pool", "lawn", "grass", "stepping stone",
    "tree", "shrub", "bush", "hedge", "outdoor furniture set", "patio set",
    "car", "suv", "vehicle", "bicycle", "bike", "truck", "van",
    "ev charger", "charging station", "floor lamp", "pendant",
    "display screen", "signage", "poster", "book", "books", "decor",
    "bedside table", "end table", "night stand", "trolley", "cart",
    "room divider", "folding screen", "partition", "pet", "toy",
    "bedside", "baby crib", "changing table", "high chair",
]


def search(q, providers=None, limit=100, kind="model"):
    params = {"q": q, "type": kind, "limit": str(limit), "free": "true"}
    if providers:
        params["providers"] = ",".join(providers)
    url = "%s/search?%s" % (BASE, urllib.parse.urlencode(params))
    try:
        r = get_json(url)
    except Exception:
        return []
    out = []
    for it in (r.get("results") or []):
        lic = it.get("license") or {}
        price = it.get("price") or {}
        if not it.get("downloadable"):
            continue
        if not price.get("free", False):
            continue
        if lic.get("commercialUse") is False:
            continue
        out.append({
            "id": it.get("id"),
            "provider": it.get("provider"),
            "nativeId": it.get("nativeId"),
            "title": it.get("title"),
            "license": lic.get("name"),
            "commercialUse": lic.get("commercialUse"),
            "attributionRequired": lic.get("attributionRequired"),
            "formats": it.get("formats") or [],
            "resolutions": it.get("resolutions") or [],
            "polyCount": it.get("polyCount"),
            "tags": it.get("tags") or [],
            "categories": it.get("categories") or [],
            "url": it.get("url"),
            "thumb": it.get("thumbnailUrl"),
            "desc": (it.get("description") or "")[:400],
            "matchedTerm": q,
        })
    return out


# --------------------------------------------------------------------
# 源分组
# --------------------------------------------------------------------
# 只用【有 model 能力】且【免费可下载】的源。
# kenney / grab3d / opengameart 的 access=scrape → 聚合层能拿到直链，优先。
SOURCE_GROUPS = [
    ("polyhaven", ["polyhaven"]),
    ("grab3d", ["grab3d"]),
    ("threedassets", ["threedassets"]),
    ("sharetextures", ["sharetextures"]),
    ("ambientcg", ["ambientcg"]),
    ("polyfork", ["polyfork"]),
    ("kenney", ["kenney"]),
    ("sketchfab", ["sketchfab"]),
    ("quaternius", ["quaternius"]),
    ("blenderkit", ["blenderkit"]),
    ("scenario", ["scenario"]),
    ("freestylized", ["freestylized"]),
    ("opengameart", ["opengameart"]),
    ("wikimediacommons", ["wikimediacommons"]),
    ("texturecan", ["texturecan"]),
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--providers", default="")
    ap.add_argument("--terms", default="")
    ap.add_argument("--limit", type=int, default=100)
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--out", default=INDEX)
    args = ap.parse_args()

    groups = SOURCE_GROUPS
    if args.providers:
        want = set(x.strip() for x in args.providers.split(",") if x.strip())
        groups = [(n, p) for n, p in SOURCE_GROUPS if n in want or set(p) & want]
    terms = [t.strip() for t in args.terms.split(",") if t.strip()] or TERMS

    print("源 %d 个，检索词 %d 个，总请求 %d"
          % (len(groups), len(terms), len(groups) * len(terms)))

    found = {}     # id → record
    done = [0]
    t0 = time.time()

    def job(gname, provs, term):
        res = search(term, providers=provs, limit=args.limit)
        with _lock:
            done[0] += 1
            n = len(res)
            print("[%4d/%4d] %-18s %-22s -> %d" %
                  (done[0], len(groups) * len(terms), gname, term[:22], n))
        return res

    tasks = [(g, p, t) for g, p in groups for t in terms]
    with cf.ThreadPoolExecutor(max_workers=args.workers) as ex:
        futs = [ex.submit(job, g, p, t) for g, p, t in tasks]
        for fu in cf.as_completed(futs):
            try:
                for r in fu.result():
                    if not r["id"]:
                        continue
                    if r["id"] not in found:
                        found[r["id"]] = r
                    else:
                        # 记录它被哪些词命中，方便回溯
                        prev = found[r["id"]]
                        mt = prev.setdefault("matchedTerms", [])
                        if prev.get("matchedTerm") and prev["matchedTerm"] not in mt:
                            mt.append(prev["matchedTerm"])
                        if r["matchedTerm"] not in mt:
                            mt.append(r["matchedTerm"])
            except Exception as e:
                print("  [task err]", e)

    out = list(found.values())
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)

    byprov = {}
    for r in out:
        byprov[r["provider"]] = byprov.get(r["provider"], 0) + 1
    print("\n耗时 %.0fs  请求 %d  失败 %d" %
          (time.time() - t0, _stats["req"], _stats["err"]))
    print("索引资产 %d 条" % len(out))
    for p, n in sorted(byprov.items(), key=lambda x: -x[1]):
        print("  %-20s %d" % (p, n))
    print("->", args.out)


if __name__ == "__main__":
    main()

"""在【本地多源索引】上做 type → 资产匹配，并输出可下载计划。

【为什么改成"先全量索引、再本地匹配"】
旧流程是"每个 type 现场搜一次"，问题：
  ① 聚合 API 高频 503（无重试时 ~1/4 请求失败）
  ② 一次搜索只看得到源里的一个切片 → 明明有货却说"找不到"
  ③ 调参（改关键词/改尺寸区间）就要重新联网，慢且不稳定
现在：一次联网抓全量索引 → 之后所有匹配都在本地跑，秒级迭代。

【匹配判据（按优先级）】
  ① 语义守卫   : must 命中其一 且 ban 全不命中（防"关键词命中≠语义正确"）
  ② 尺寸贴合   : 实测包围盒 vs 现实区间，按相对偏差打分（防比例崩坏）
  ③ 风格亲和   : 与全屋统一风格（modern/classic/industrial/outdoor）一致
  ④ 细节充足   : 面数在合理区间（< 500 的低模不接受，用户要 3A 水准）
  ⑤ 许可证     : 必须 free + 可商用 + 有可下载格式

【输出】
  assets/external/asset_plan.json
    { type: [ {id, provider, nativeId, title, license, score, why, dims_mm?} ] }

用法：
  python match_index.py
  python match_index.py --types sofa,bed --verbose
"""
import argparse
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, HERE)

from catalog_spec import SPEC, style_tags   # noqa: E402

EXT = os.path.join(ROOT, "assets", "external")
IDX = os.path.join(EXT, "multi_index.json")
PH = os.path.join(EXT, "ph_all_models.json")
OUT = os.path.join(EXT, "asset_plan.json")

# 源优先级：Poly Haven 质量最高且带权威尺寸；其余按"品类覆盖度"排序
PROVIDER_RANK = {
    "polyhaven": 0,
    "grab3d": 1,
    "threedassets": 2,
    "sharetextures": 3,
    "ambientcg": 4,
    "polyfork": 5,
    "kenney": 6,
    "sketchfab": 7,
    "quaternius": 8,
    "blenderkit": 9,
    "scenario": 10,
    "freestylized": 11,
    "opengameart": 12,
    "wikimediacommons": 13,
    "texturecan": 14,
}

OK_FORMATS = ("glb", "gltf", "blend", "fbx", "obj", "usd", "usdz")


def tokens(text):
    """把标题/标签切成小写词元集合（用于词边界匹配）"""
    return set(t for t in re.split(r"[^a-z0-9]+", (text or "").lower()) if t)


def phrase_hit(phrase, title, tags):
    """词组是否命中标题或标签。

    【为什么要拆词组逐词匹配，而不是直接 substring】
    直接 substring 会产生大量误命中：
      must=["curtain"] → "Curtain Straight 2m" ✔
                     → "medieval curtain" ✘（被 ban 拦）
      must=["vase"]    → "vase" ✔ / "Vases" ✔ / "Vase Stand" ✔
    拆词后要求【所有词都在标题词元里】，避免 "shower" 命中 "showroom"，
    也避免 "car" 命中 "cart"。
    """
    t = (title or "").lower()
    parts = [p for p in re.split(r"[^a-z0-9]+", phrase.lower()) if p]
    if not parts:
        return False
    tt = tokens(title)
    tg = tokens(" ".join(tags or []))
    # 全部词都在标题里 → 命中
    if all(p in tt for p in parts):
        return True
    # 部分词在标题、其余在标签里 → 也算命中（如 "Area Rug"：area 在标题、rug 在标签）
    combined = tt | tg
    return all(p in combined for p in parts)


def semantic_ok(rec, must, ban):
    title = rec.get("title") or ""
    tags = rec.get("tags") or []
    blob = (title + " " + " ".join(tags)).lower()
    for b in ban:
        # ban 也用词边界匹配，避免 "car" 命中 "cart"
        if b.lower() in blob:
            # 词边界判定
            if re.search(r"(?<![a-z0-9])" + re.escape(b.lower()) + r"(?![a-z0-9])", blob):
                return False
    if not must:
        return True
    for m in must:
        if phrase_hit(m, title, tags):
            return True
    return False


def size_score(dims, band):
    """尺寸贴合度：返回 (0~1 贴合分, 说明)

    dims  : [W, D, H] mm
    band  : (Wmin, Wmax, Dmin, Dmax, Hmin, Hmax)
    对每个轴：落在区间内 → 1.0；超出 → 按超出比例衰减。
    """
    if not dims or not band:
        return 0.5, "no_size"
    wmin, wmax, dmin, dmax, hmin, hmax = band
    bands = [(dims[0], wmin, wmax, "W"), (dims[1], dmin, dmax, "D"),
             (dims[2], hmin, hmax, "H")]
    total = 0.0
    notes = []
    for v, lo, hi, ax in bands:
        if v <= 0:
            total += 0.0
            notes.append("%s:?" % ax)
            continue
        if lo <= v <= hi:
            total += 1.0
            notes.append("%s:ok" % ax)
        else:
            if v < lo:
                pen = (lo - v) / max(lo, 1.0)
            else:
                pen = (v - hi) / max(hi, 1.0)
            total += max(0.0, 1.0 - pen * 2.2)
            notes.append("%s:%+.0f%%" % (ax, (v - (lo if v < lo else hi)) /
                                         max(lo if v < lo else hi, 1) * 100))
    return total / 3.0, ",".join(notes)


def score_rec(rec, spec, ph_dims):
    """给一条索引记录打分。返回 (score, why) 或 (None, "")。"""
    # ---- 硬性门槛 ----
    if not rec.get("downloadable", True):
        return None, ""
    fmts = [f.lower() for f in (rec.get("formats") or [])]
    if not any(f in OK_FORMATS for f in fmts):
        return None, ""
    pc = rec.get("polyCount")
    # 低模（< 80 面）一律不要 —— 用户要 3A 水准，不是玩具
    if pc is not None and pc < 80:
        return None, ""
    # 极高模（> 1.2M）也降权，浏览器扛不住
    if pc is not None and pc > 1200000:
        return None, ""

    # ---- 语义 ----
    if not semantic_ok(rec, spec.get("must") or [], spec.get("ban") or []):
        return None, ""

    why = []
    score = 40.0

    # ---- 尺寸 ----
    dims = ph_dims.get(rec.get("nativeId")) if rec.get("provider") == "polyhaven" else None
    if dims:
        s, note = size_score(dims, spec.get("size"))
        score += s * 45.0
        why.append("size=%.2f(%s)" % (s, note))
    else:
        score += 12.0
        why.append("size=n/a")

    # ---- 风格 ----
    pref = spec.get("style")
    tags = style_tags(rec.get("nativeId") or "") | style_tags(rec.get("title") or "")
    if pref:
        if pref in tags:
            score += 18.0
            why.append("style:%s" % pref)
        elif tags:
            score -= 22.0
            why.append("style:X(%s)" % ",".join(sorted(tags)))
        else:
            score += 6.0
            why.append("style:neutral")

    # ---- 细节充足度 ----
    if pc is None:
        score += 0.0
        why.append("tri:?")
    elif 400 <= pc <= 120000:
        score += 16.0
        why.append("tri:good")
    elif pc < 400:
        score += 4.0
        why.append("tri:low(%d)" % pc)
    else:
        score += 6.0
        why.append("tri:high(%d)" % pc)

    # ---- 源优先级 ----
    pr = PROVIDER_RANK.get(rec.get("provider"), 50)
    score += max(0.0, 12.0 - pr * 1.2)
    why.append("src:%s" % rec.get("provider"))

    # ---- 有权威尺寸元数据（Poly Haven）加分：下载后可直接校验比例 ----
    if dims:
        score += 8.0
        why.append("dims_meta")

    # ---- 许可证加分 ----
    lic = (rec.get("license") or "").lower()
    if "cc0" in lic:
        score += 6.0
    elif rec.get("attributionRequired"):
        score += 1.0

    return score, ",".join(why)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--index", default=IDX)
    ap.add_argument("--types", default="")
    ap.add_argument("--out", default=OUT)
    ap.add_argument("--top", type=int, default=6)
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()

    idx = []
    if os.path.exists(args.index):
        with open(args.index, encoding="utf-8") as f:
            idx = json.load(f)
    print("本地索引 %d 条" % len(idx))

    # Poly Haven 权威尺寸表
    ph_dims = {}
    if os.path.exists(PH):
        with open(PH, encoding="utf-8-sig") as f:
            for m in json.load(f):
                ph_dims[m["id"]] = [m["w"], m["d"], m["h"]]
    print("PolyHaven 尺寸元数据 %d 条" % len(ph_dims))

    cat_path = os.path.join(ROOT, "验收", "models", "catalog.json")
    with open(cat_path, encoding="utf-8") as f:
        cat = json.load(f)
    all_types = sorted({it["type"] for g in cat["groups"] for it in g["items"]})

    want = set(t.strip() for t in args.types.split(",") if t.strip())
    types = [t for t in all_types if not want or t in want]

    plan = {}
    covered, uncovered = [], []
    for t in types:
        spec = SPEC.get(t)
        if not spec:
            uncovered.append((t, "no_spec"))
            continue
        scored = []
        for rec in idx:
            sc, why = score_rec(rec, spec, ph_dims)
            if sc is None:
                continue
            scored.append((sc, rec, why))
        scored.sort(key=lambda x: -x[0])
        if not scored:
            uncovered.append((t, "no_candidate"))
            continue
        cands = []
        for sc, rec, why in scored[:args.top]:
            c = {
                "id": rec.get("id"),
                "provider": rec.get("provider"),
                "nativeId": rec.get("nativeId"),
                "title": rec.get("title"),
                "license": rec.get("license"),
                "commercialUse": rec.get("commercialUse"),
                "formats": rec.get("formats"),
                "polyCount": rec.get("polyCount"),
                "url": rec.get("url"),
                "thumb": rec.get("thumb"),
                "tags": rec.get("tags"),
                "matchedTerms": rec.get("matchedTerms") or ([rec["matchedTerm"]]
                                 if rec.get("matchedTerm") else []),
                "score": round(sc, 1),
                "why": why,
            }
            if rec.get("nativeId") in ph_dims:
                c["dims_mm"] = ph_dims[rec["nativeId"]]
            cands.append(c)
        plan[t] = {"candidates": cands, "size_mm": spec.get("size"),
                   "style": spec.get("style"), "tier": spec.get("tier")}
        covered.append((t, cands[0]["title"], cands[0]["score"], cands[0]["provider"]))

    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(plan, f, ensure_ascii=False, indent=1)

    print("\n=== 覆盖 %d / %d ===" % (len(covered), len(types)))
    for t, title, sc, prov in covered:
        mark = "*" if sc < 55 else " "
        print(" %s%-18s -> %-44s %5.1f %s" % (mark, t, (title or "")[:44], sc, prov))
    print("\n=== 未覆盖 %d ===" % len(uncovered))
    for t, why in uncovered:
        print("  %-18s %s" % (t, why))
    print("\n->", args.out)


if __name__ == "__main__":
    main()

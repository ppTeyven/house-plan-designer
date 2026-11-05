"""为验收目录的 158 个 type 生成【外部资源候选映射】。

【为什么要自动匹配】
验收目录有 158 种不同 type、251 个款式。手工逐条映射既慢又容易漏。
这里用【关键词规则 + 尺寸约束 + 风格约束】做自动匹配：
  1. 每个 type 声明一组【同义词/关键词】（匹配 Poly Haven 的 id）
  2. 声明【现实尺寸区间】（mm），候选模型必须落在区间内
  3. 声明【风格偏好】（modern / classic / industrial），
     用于排除风格冲突的候选
  4. 对每个 type 按"尺寸贴合度 + 风格贴合度 + 面数适中"打分排序

【输出】
  assets/external/catalog_map.json
    { type: { "candidates": [{slug, tri, dims_mm, score, why}], ... } }

【可解释性】
每个候选都带 score 与 why（为什么选它），便于人工复核，
而不是给一个不可追溯的黑盒结果。

用法：python build_catalog_map.py
"""
import json
import os
import re
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
UA = "HousePlannerAssetFetcher/1.0"


def api_models():
    req = urllib.request.Request(
        "https://api.polyhaven.com/assets?t=models",
        headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=120) as r:
        data = json.loads(r.read().decode("utf-8"))
    out = []
    for slug, meta in data.items():
        d = meta.get("dimensions") or [0, 0, 0]
        cats = [c for c in meta.get("categories", [])
                if not c.startswith("collection:")]
        out.append({
            "slug": slug,
            "categories": cats,
            "polycount": meta.get("polycount", 0),
            "dims_mm": [round(float(d[0])), round(float(d[1])), round(float(d[2]))],
        })
    return out


# =====================================================================
# type 规格表
#   kw   : 匹配 Poly Haven 模型 id 的关键词（任一命中）
#   size : 现实尺寸区间 mm [W, D, H]，None 表示不限
#   style: 风格偏好（加权），用于排除风格冲突
#   alt  : 备用关键词
# =====================================================================
SPEC = {
    # ---------------- 沙发组 ----------------
    "sofa":         dict(kw=["sofa"], size=[1800, 2600, 850, 1000], style="modern",
                         alt=["couch"]),
    "lSofa":        dict(kw=["sofa"], size=[2200, 3200, 800, 1000], style="modern"),
    "armchair":     dict(kw=["armchair", "arm_chair", "lounge_chair"], size=[700, 1100, 800, 1100], style="modern"),
    "lounge":       dict(kw=["lounge_chair", "armchair"], size=[700, 1100, 700, 1000], style="modern"),
    "chaise":       dict(kw=["chaise", "day_bed"], size=[1500, 2000, 650, 900], style="modern"),
    "ottoman":      dict(kw=["ottoman", "stool"], size=[400, 900, 350, 500], style="modern"),
    "stool":        dict(kw=["stool"], size=[300, 600, 400, 700], style="modern"),
    "barStool":     dict(kw=["bar_chair", "stool"], size=[350, 550, 650, 850], style="modern"),
    "rockingChair": dict(kw=["rocking"], size=[550, 900, 800, 1100], style="classic"),
    "officeChair":  dict(kw=["office_chair", "chair"], size=[550, 750, 900, 1300], style="modern"),
    "chair":        dict(kw=["chair"], size=[400, 560, 780, 1000], style="modern"),
    "entryBench":   dict(kw=["bench"], size=[800, 1200, 400, 500], style="modern"),
    "bedBench":     dict(kw=["bench"], size=[1000, 1600, 400, 500], style="modern"),

    # ---------------- 桌组 ----------------
    "coffeeTable":  dict(kw=["coffee_table"], size=[800, 1400, 330, 480], style="modern"),
    "roundTable":   dict(kw=["round_wooden_table", "coffee_table_round"], size=[800, 1600, 700, 780], style="modern"),
    "ovalTable":    dict(kw=["table"], size=[1200, 2000, 700, 780], style="modern"),
    "diningTable":  dict(kw=["dining_table", "wooden_table"], size=[1400, 2200, 700, 800], style="modern"),
    "sideTable":    dict(kw=["side_table", "small_wooden_table"], size=[350, 700, 450, 800], style="modern"),
    "consoleTable": dict(kw=["console"], size=[900, 1800, 700, 950], style="modern"),
    "desk":         dict(kw=["desk"], size=[1000, 1600, 700, 800], style="modern"),
    "lDesk":        dict(kw=["desk"], size=[1400, 2000, 700, 800], style="modern"),
    "trainingTable": dict(kw=["desk", "table"], size=[1400, 3000, 700, 780], style="modern"),
    "kitchenIsland": dict(kw=["counter", "cabinet", "table"], size=[1800, 3000, 850, 950], style="modern"),
    "barCounter":   dict(kw=["counter", "table"], size=[1200, 2400, 1000, 1150], style="modern"),

    # ---------------- 柜组 ----------------
    "wardrobe":     dict(kw=["cabinet", "wardrobe"], size=[1000, 2400, 1800, 2400], style="modern"),
    "nightstand":   dict(kw=["nightstand"], size=[380, 620, 450, 700], style="modern"),
    "tvCabinet":    dict(kw=["cabinet", "sideboard"], size=[1200, 2200, 350, 650], style="modern"),
    "sideboard":    dict(kw=["cabinet", "drawer"], size=[1200, 2200, 700, 1000], style="modern"),
    "chest":        dict(kw=["drawer", "commode", "chest"], size=[800, 1800, 700, 1300], style="modern"),
    "bookshelf":    dict(kw=["shelf", "bookshelf"], size=[700, 1600, 1500, 2200], style="modern"),
    "cabinet":      dict(kw=["cabinet", "shelves"], size=[600, 2000, 800, 2400], style="modern"),
    "shelfRack":    dict(kw=["shelf", "shelves", "rack"], size=[600, 1400, 1000, 2000], style="modern"),

    # ---------------- 床组 ----------------
    "bed":          dict(kw=["bed"], size=[1400, 2000, 900, 1400], style="modern"),
    "roundBed":     dict(kw=["bed"], size=[1400, 2000, 500, 900], style="modern"),
    "bunkBed":      dict(kw=["bed"], size=[900, 1200, 1500, 1900], style="modern"),
    "crib":         dict(kw=["bed", "crib"], size=[600, 900, 900, 1200], style="modern"),
    "tatami":       dict(kw=["table", "platform", "bed"], size=[1500, 2200, 300, 600], style="modern"),
    "bayCushion":   dict(kw=["cushion", "pillow"], size=[800, 1600, 100, 250], style="modern"),

    # ---------------- 卫浴 ----------------
    "counter":      dict(kw=["counter", "cabinet"], size=[600, 1800, 850, 950], style="modern"),
    "toilet":       dict(kw=["toilet", "urinal"], size=[350, 500, 700, 850], style="modern"),
    "vanity":       dict(kw=["cabinet", "counter", "sink"], size=[600, 1200, 800, 950], style="modern"),
    "pedestalSink": dict(kw=["sink", "basin"], size=[400, 700, 750, 950], style="modern"),
    "bathtub":      dict(kw=["bathtub", "tub"], size=[1400, 1800, 450, 650], style="modern"),
    "freeTub":      dict(kw=["tub", "bathtub"], size=[1400, 1800, 450, 650], style="modern"),
    "shower":       dict(kw=["shower"], size=[800, 1200, 1800, 2200], style="modern"),
    "towelWarmer":  dict(kw=["towel", "rack"], size=[400, 900, 800, 1400], style="modern"),
    "serviceSink":  dict(kw=["sink", "basin"], size=[500, 800, 500, 700], style="industrial"),

    # ---------------- 厨电 / 电器 ----------------
    "fridge":       dict(kw=["fridge", "refrigerator", "freezer", "cooler"], size=[600, 900, 1500, 2100], style="modern"),
    "freezer":      dict(kw=["freezer", "fridge"], size=[600, 900, 800, 1200], style="modern"),
    "dishwasher":   dict(kw=["dishwasher"], size=[450, 700, 800, 900], style="modern"),
    "tallOven":     dict(kw=["oven", "stove"], size=[550, 700, 1800, 2200], style="modern"),
    "hood":         dict(kw=["hood", "vent"], size=[500, 900, 500, 900], style="modern"),
    "microwave":    dict(kw=["microwave"], size=[450, 600, 300, 450], style="modern"),
    "washer":       dict(kw=["washer"], size=[550, 700, 800, 950], style="modern"),
    "dryer":        dict(kw=["dryer"], size=[550, 700, 800, 950], style="modern"),
    "waterHeater":  dict(kw=["kettle", "boiler", "heater"], size=[400, 600, 700, 1200], style="modern"),
    "coffeeMachine": dict(kw=["coffee", "kettle", "espresso"], size=[200, 500, 300, 500], style="modern"),
    "vacuum":       dict(kw=["vacuum", "cleaner"], size=[300, 500, 900, 1200], style="modern"),

    # ---------------- 灯具 ----------------
    "floorLamp":    dict(kw=["floor_lamp", "lamp"], size=[300, 700, 1400, 1900], style="modern"),
    "deskLamp":     dict(kw=["desk_lamp", "lamp"], size=[300, 600, 400, 900], style="modern"),
    "chandelier":   dict(kw=["chandelier", "hanging_lamp", "ceiling_lamp"], size=[600, 1400, 600, 1400], style="modern"),
    "lawnLamp":     dict(kw=["street_lamp", "lamp"], size=[300, 700, 2500, 4000], style="modern"),

    # ---------------- 电器 / 娱乐 ----------------
    "wallTV":       dict(kw=["television", "tv"], size=[800, 1600, 600, 1200], style="modern"),
    "speaker":      dict(kw=["speaker", "boombox"], size=[200, 500, 600, 1200], style="modern"),
    "fireplace":    dict(kw=["stove", "fireplace"], size=[800, 1500, 900, 1400], style="modern"),
    "piano":        dict(kw=["piano"], size=[1400, 1600, 1000, 1300], style="classic"),
    "billiards":    dict(kw=["pool_table", "billiard"], size=[1800, 2800, 750, 900], style="modern"),

    # ---------------- 软装 ----------------
    "rug":          dict(kw=["rug", "carpet"], size=[1600, 3000, 10, 30], style="modern"),
    "rugRound":     dict(kw=["rug", "carpet"], size=[1200, 2500, 10, 30], style="modern"),
    "curtain":      dict(kw=["curtain", "drape"], size=[1000, 3000, 1800, 2800], style="modern"),
    "plant":        dict(kw=["plant", "planter"], size=[300, 900, 500, 1600], style="modern"),
    "hangingPlant": dict(kw=["plant", "hanging"], size=[200, 700, 300, 900], style="modern"),
    "wallArt":      dict(kw=["picture_frame", "art"], size=[400, 1500, 400, 1200], style="modern"),
    "wallClock":    dict(kw=["wall_clock", "clock"], size=[200, 600, 200, 600], style="modern"),
    "floorVase":    dict(kw=["vase"], size=[200, 500, 400, 1000], style="modern"),
    "mirror":       dict(kw=["mirror"], size=[400, 900, 700, 1600], style="modern"),
    "wallPanel":    dict(kw=["wall", "panel", "screen"], size=[600, 2400, 1500, 2600], style="modern"),

    # ---------------- 庭院 ----------------
    "tree":         dict(kw=["tree"], size=[2000, 8000, 3000, 12000], style="modern"),
    "shrub":        dict(kw=["shrub", "bush"], size=[400, 2000, 300, 1200], style="modern"),
    "lawn":         dict(kw=["grass", "lawn", "ground"], size=[1000, 10000, 10, 60], style="modern"),
    "fence":        dict(kw=["fence"], size=[2000, 8000, 1000, 2500], style="modern"),
    "gate":         dict(kw=["gate"], size=[1500, 4000, 1500, 3000], style="modern"),
    "car":          dict(kw=["car"], size=[4000, 5000, 1400, 1700], style="modern"),
    "bicycle":      dict(kw=["bicycle", "bike"], size=[1600, 1900, 1000, 1200], style="modern"),

    # ---------------- 建筑 ----------------
    "stairRun":     dict(kw=["stair"], size=[900, 4000, 2500, 3500], style="modern"),
    "elevator":     dict(kw=["elevator"], size=[1000, 1500, 2200, 2600], style="modern"),
    "ceilingSpeaker": dict(kw=["speaker"], size=[150, 350, 50, 150], style="modern"),
    "airVent":      dict(kw=["vent", "air"], size=[200, 600, 200, 600], style="modern"),
    "wifiAP":       dict(kw=["router", "antenna"], size=[100, 400, 30, 200], style="modern"),
}


# =====================================================================
# 风格评分
# =====================================================================
STYLE_TAGS = {
    "modern": ["modern", "contemporary", "minimal", "scandinavian", "nordic",
               "industrial_pipe", "office", "school", "metal_office",
               "bar_chair", "side_table", "coffee_table_round", "round_wooden"],
    "classic": ["gothic", "victorian", "classic", "ornate", "antique",
                "barber", "chinese", "rocking", "vintage", "mantel",
                "grandfather", "medieval", "renaissance"],
    "industrial": ["industrial", "tool", "metal_tool", "worn", "rusty",
                   "ammo", "welding", "workshop", "warehouse"],
}


def style_tags(slug):
    s = slug.lower()
    tags = set()
    for t, kws in STYLE_TAGS.items():
        for k in kws:
            if k in s:
                tags.add(t)
    return tags


def kw_hit(kw, slug):
    """关键词命中判定 —— 必须按【词边界】匹配，不能用裸 substring。

    【v24 · 修复真 bug】
    早期用 `kw.lower() in slug`（裸子串）→ 大量误命中：
      · airVent  的 kw "air"  命中 bar_chAIR_round_01
      · car      的 kw "car"  命中 CoffeeCART_01
      · wallArt  的 kw "art"  命中 dARTboard
      · counter  的 kw "cabinet" 命中 …… 等
    → 映射表里塞进了明显不是该品类的模型（换气口→吧椅、汽车→咖啡车）。

    正解：把 slug 按 _ / 空格 / 数字拆成 token，要求：
      · 关键词整体等于某个 token（如 "coffee_table" → slug 含 token "coffee_table"）
      · 或关键词是某个 token 的【前缀且 token 长度 ≥ 关键词长度】的完整词
        （如 "armchair" 命中 "armchair"；"chair" 命中 "dining_chair"）
      · 但 "air" 不得命中 "chair"（前缀方向反了）
    规则：关键词必须是 token 的【起始前缀】，且 token 不得在关键词处截断成别的词。
    实现：token.split("_") 后取首词，要求 首词 == 关键词 或 首词.startswith(关键词)
         这样 "chair" 不会命中 token 首词 "bar"，"air" 不会命中 "armchair"
         （首词 "armchair".startswith("air") 为 False）。
    """
    toks = [t for t in re.split(r"[^a-z0-9]+", slug.lower()) if t]
    heads = set()
    for t in toks:
        heads.add(t)
        # 多词 slug 的首词也算独立 token
    # 关键词可能是多词（coffee_table），先试整体
    if kw.lower() in slug.lower():
        # 仍需确认不是更长单词里的小片段：检查 "kw" 前后是分隔符
        pat = r"(?<![a-z0-9])" + re.escape(kw.lower()) + r"(?![a-z0-9])"
        if re.search(pat, slug.lower()):
            return True
    # 单词前缀匹配：token 首词以关键词开头
    for t in toks:
        for piece in t.split("_"):
            if piece == kw.lower():
                return True
            if piece.startswith(kw.lower()) and len(piece) > len(kw.lower()):
                # 必须是完整词的前缀且后面不接字母（如 "chairs" 算，"airplane" 不算 "air"）
                if len(piece) == len(kw.lower()) + 1 and piece[-1] == "s":
                    return True
    return False


def score_candidate(type_spec, m):
    """给候选打分，返回 (score, why)。分数越高越合适。"""
    slug = m["slug"].lower()
    w = m["dims_mm"]
    why = []
    score = 0.0

    kws = list(type_spec.get("kw", [])) + list(type_spec.get("alt", []))
    hit = None
    for k in kws:
        if kw_hit(k, slug):
            hit = k
            break
    if hit is None:
        return -1, ""
    score += 50
    why.append("kw:%s" % hit)

    size = type_spec.get("size")
    if size:
        lo_w, hi_w, lo_h, hi_h = size
        dw = w[0]
        dh = w[2]
        if lo_w <= dw <= hi_w and lo_h <= dh <= hi_h:
            score += 30
            why.append("size:ok")
        else:
            def over(v, lo, hi):
                if v < lo:
                    return (lo - v) / max(lo, 1)
                if v > hi:
                    return (v - hi) / max(hi, 1)
                return 0.0
            pen = over(dw, lo_w, hi_w) + over(dh, lo_h, hi_h)
            score += max(0.0, 25 - pen * 60)
            why.append("size:off%.2f" % pen)

    pref = type_spec.get("style")
    tags = style_tags(m["slug"])
    if pref:
        if pref in tags:
            score += 20
            why.append("style:%s" % pref)
        elif tags:
            score -= 25
            why.append("style:CONFLICT(%s)" % ",".join(sorted(tags)))
        else:
            score += 8
            why.append("style:neutral")

    tri = m["polycount"]
    if 2000 <= tri <= 60000:
        score += 12
        why.append("tri:ok")
    elif tri < 2000:
        score += 4
        why.append("tri:low")
    else:
        score -= 6
        why.append("tri:high")

    return score, ",".join(why)


def main():
    models = api_models()
    print("Poly Haven 模型总数:", len(models))

    catalog_path = os.path.join(ROOT, "验收", "models", "catalog.json")
    with open(catalog_path, encoding="utf-8") as f:
        cat = json.load(f)
    types = sorted({it["type"] for g in cat["groups"] for it in g["items"]})
    print("目录 type 数:", len(types))

    out = {}
    covered, uncovered = [], []
    for t in types:
        spec = SPEC.get(t)
        if not spec:
            uncovered.append(t)
            continue
        cands = []
        for m in models:
            sc, why = score_candidate(spec, m)
            if sc > 0:
                cands.append({"slug": m["slug"], "tri": m["polycount"],
                              "dims_mm": m["dims_mm"], "score": round(sc, 1),
                              "why": why})
        cands.sort(key=lambda c: -c["score"])
        out[t] = {"candidates": cands[:8],
                  "size_mm": spec.get("size"),
                  "style": spec.get("style")}
        if cands:
            covered.append((t, cands[0]["slug"], cands[0]["score"]))
        else:
            uncovered.append(t)

    mp = os.path.join(ROOT, "assets", "external", "catalog_map.json")
    os.makedirs(os.path.dirname(mp), exist_ok=True)
    with open(mp, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)

    print("\n=== 已覆盖 %d / %d ===" % (len(covered), len(types)))
    for t, s, sc in covered:
        print("  %-18s -> %-32s (%s)" % (t, s, sc))
    print("\n=== 未覆盖 %d 个 ===" % len(uncovered))
    for t in uncovered:
        print("  ", t)
    print("\n->", mp)


if __name__ == "__main__":
    main()

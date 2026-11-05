"""为【Poly Haven 覆盖不到】的 type 生成多源候选（shep.bot 聚合 API）。

【分工】
  · build_catalog_map.py  → Poly Haven（CC0、质量高、带真实尺寸元数据）
  · build_gap_map.py      → shep.bot 聚合（PolyHaven/Kenney/3DAssets/PolyFork/
                            Grab3D/ShareTextures/BlenderKit…）补齐缺口

【v24 · 性能修复】
早期版本串行查询 ~250 个词，13 分钟还没跑完。
现在用【线程池并发】+【失败快速跳过】。

【v24 · 语义守卫（防止明显跑偏）】
"关键词命中"不等于"语义正确"。实测踩坑：
  · bedBench  → bench_vice_01（台钳，不是长凳）
  · hangingPlant → hanging_picture_frame_01（挂画框，不是吊兰）
  · coffeeMachine → coffee_table_round_01（茶几，不是咖啡机）
  · chest → treasure_chest（宝箱，不是五斗柜）
解法：每个 type 声明【必含词组】（标题里必须命中其一）与【禁含词】。

用法：python build_gap_map.py [--only type1,type2]
"""
import concurrent.futures as cf
import json
import os
import re
import sys
import threading

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, HERE)

import fetch_multi as FM   # noqa

PROVIDER_RANK = {
    "polyhaven": 0, "grab3d": 1, "sharetextures": 2, "polyfork": 3,
    "threedassets": 4, "blenderkit": 5, "kenney": 6, "quaternius": 7,
    "opengameart": 8, "fab": 9, "scenario": 10,
}

# =====================================================================
# type → (检索词列表, 必含词组, 禁含词)
# =====================================================================
QUERIES = {
    # ---------------- 卫浴 ----------------
    "toilet":         (["toilet"], ["toilet"], ["paper", "sign", "portable", "public", "block"]),
    "squat":          (["squat toilet"], ["squat"], []),
    "vanity":        (["bathroom vanity", "vanity cabinet"], ["vanity"], ["kit"]),
    "mirrorCabinet": (["medicine cabinet", "mirror cabinet"], ["cabinet"], ["medicine"]),
    "pedestalSink":  (["pedestal sink", "wash basin"], ["sink", "basin"], ["kitchen"]),
    "bathtub":       (["bathtub"], ["bathtub", "tub"], ["mat", "sign", "faucet"]),
    "freeTub":       (["freestanding bathtub", "oval bathtub"], ["bathtub"], []),
    "shower":        (["shower cabin", "shower enclosure"], ["shower"], ["head", "curtain"]),
    "showerScreen":  (["shower screen"], ["shower"], []),
    "showerSet":     (["shower faucet set", "shower system"], ["shower"], []),
    "towelWarmer":   (["heated towel rail", "towel rail"], ["towel"], []),
    "bathHeater":    (["bathroom ceiling heater", "bathroom fan"], ["bathroom"], []),
    "laundrySink":   (["utility sink"], ["sink"], []),
    "urinal":        (["urinal"], ["urinal"], []),
    "serviceSink":   (["service sink", "utility sink"], ["sink"], []),
    "lCounter":      (["l shaped kitchen counter"], ["counter", "kitchen"], []),
    "uCounter":      (["u shaped kitchen counter"], ["counter", "kitchen"], []),

    # ---------------- 厨电 ----------------
    "fridge":        (["refrigerator"], ["refrigerator", "fridge"], ["minibar", "parts"]),
    "freezer":       (["freezer"], ["freezer"], ["commercial", "chest ice"]),
    "dishwasher":    (["dishwasher"], ["dishwasher"], []),
    "tallOven":      (["built in oven", "wall oven"], ["oven"], ["microwave", "stove top"]),
    "hood":          (["range hood", "kitchen hood"], ["hood"], ["ventilation fan"]),
    "microwave":     (["microwave oven"], ["microwave"], []),
    "washer":        (["washing machine"], ["washing", "washer"], []),
    "dryer":         (["tumble dryer", "clothes dryer"], ["dryer"], []),
    "airPurifier":   (["air purifier"], ["purifier"], []),
    "robotVac":      (["robot vacuum"], ["vacuum"], ["car", "pool"]),
    "waterDispenser": (["water dispenser", "water cooler"], ["water", "dispenser", "cooler"], []),
    "purifier":      (["water purifier"], ["purifier"], []),
    "waterHeater":   (["water heater"], ["water", "heater"], ["radiator", "masonry"]),
    "miniHeater":    (["small water heater", "under sink water heater"], ["water", "heater"], []),
    "gasHeater":     (["gas water heater"], ["gas", "heater"], []),
    "boiler":        (["boiler"], ["boiler"], ["masonry", "water"]),
    "manifold":      (["heating manifold"], ["manifold"], []),
    "waterSoftener": (["water softener"], ["softener", "water"], []),
    "coffeeMachine": (["espresso machine", "coffee maker"], ["coffee", "espresso", "maker"], ["table", "cart"]),
    "wineFridge":    (["wine refrigerator", "wine cooler"], ["wine"], []),
    "acWall":        (["split air conditioner"], ["air", "conditioner"], ["car", "truck"]),
    "acFloor":       (["floor air conditioner"], ["air", "conditioner"], []),
    "mobileDisplay": (["large display screen", "presentation display"], ["display", "screen", "panel"], []),
    "printer":       (["office printer"], ["printer"], ["3d printing"]),

    # ---------------- 灯具 ----------------
    "floorLamp":     (["floor lamp"], ["floor", "lamp"], ["ceiling", "table", "desk"]),
    "deskLamp":      (["desk lamp"], ["desk", "lamp"], ["floor"]),
    "chandelier":    (["chandelier"], ["chandelier"], []),
    "arcLamp":       (["arc floor lamp"], ["arc", "lamp"], []),
    "lawnLamp":      (["garden lamp post", "outdoor lamp post"], ["lamp", "post"], ["street"]),

    # ---------------- 电器 / 娱乐 ----------------
    "wallTV":        (["wall mounted television", "flat screen television"], ["tv", "television"], ["cart", "stand"]),
    "projScreen":    (["projector screen"], ["projector", "screen"], []),
    "speaker":       (["floor standing speaker"], ["speaker"], ["car", "carpet"]),
    "fireplace":     (["electric fireplace"], ["fireplace"], ["hearth tool", "log"]),
    "piano":         (["upright piano"], ["piano"], ["grand"]),
    "grandPiano":    (["grand piano"], ["grand", "piano"], []),
    "billiards":     (["pool table"], ["pool", "billiard", "snooker"], []),
    "mahjong":       (["mahjong table"], ["mahjong"], []),
    "treadmill":     (["treadmill"], ["treadmill"], []),
    "sauna":         (["sauna"], ["sauna"], []),
    "bike":          (["exercise bike", "stationary bike"], ["exercise", "stationary", "spin"], ["bicycle", "motorcycle"]),
    "yogaMat":       (["yoga mat"], ["yoga", "mat"], []),
    "fishTank":      (["aquarium"], ["aquarium", "fish", "tank"], ["goldfish", "bowl"]),

    # ---------------- 软装 ----------------
    "rug":           (["area rug", "wool rug"], ["rug", "carpet"], ["military", "vehicle"]),
    "rugRound":      (["round rug"], ["rug", "carpet"], []),
    "doormat":       (["doormat", "door mat"], ["mat", "door"], ["bath", "mouse"]),
    "playMat":       (["play mat"], ["play", "mat"], ["mouse"]),
    "curtain":       (["window curtains"], ["curtain"], ["castle", "medieval", "stage", "noren", "camp", "japanese"]),
    "sheer":         (["sheer curtain"], ["sheer", "curtain"], []),
    "screenDivider": (["room divider", "folding screen"], ["divider", "screen"], ["projection", "shower"]),
    "plant":         (["houseplant", "potted plant"], ["plant"], ["tree", "forest", "bush", "flower", "field", "hedge"]),
    "hangingPlant":  (["hanging plant", "hanging planter"], ["plant"], ["picture", "frame", "art", "light"]),
    "floorVase":     (["floor vase", "tall vase"], ["vase"], ["antique"]),
    "wallArt":       (["wall art", "picture frame"], ["art", "picture", "frame"], ["dart", "target", "board"]),
    "wallClock":     (["wall clock"], ["wall", "clock"], ["telephone", "grandfather", "mantel", "alarm"]),
    "wallPanel":     (["wall panel", "wood slat panel"], ["panel", "slat"], []),
    "mirror":        (["wall mirror"], ["mirror"], ["ornate"]),

    # ---------------- 柜组 ----------------
    "dresser":       (["chest of drawers", "dresser"], ["dresser", "drawers"], []),
    "fileCabinet":   (["filing cabinet"], ["filing", "file", "cabinet"], []),
    "chest":         (["chest of drawers"], ["chest", "drawers"], ["treasure", "tool", "storage"]),
    "bookshelf":     (["bookshelf", "book case"], ["book", "shelf"], ["worn"]),
    "bookshelfLow":  (["low bookshelf", "short bookcase"], ["book", "shelf"], []),
    "wineCabinet":   (["wine cabinet", "wine cooler cabinet"], ["wine", "cabinet"], []),
    "displayCabinet": (["display cabinet", "glass display case"], ["display", "cabinet", "case"], []),
    "shoeCabinet":   (["shoe cabinet", "shoe rack"], ["shoe"], []),
    "hallCabinet":   (["entryway console cabinet"], ["entry", "console", "cabinet"], []),
    "cabWardrobe":   (["built in wardrobe", "closet cabinet"], ["wardrobe", "closet"], []),
    "cabSlide":      (["sliding door wardrobe"], ["sliding", "wardrobe"], []),
    "cabCorner":     (["corner wardrobe"], ["corner", "wardrobe"], []),
    "cabShoe":       (["shoe storage cabinet"], ["shoe"], []),
    "cabSideboard":  (["sideboard cabinet", "buffet cabinet"], ["sideboard", "buffet", "cabinet"], []),
    "cabTall":       (["tall bookshelf"], ["book", "shelf"], []),
    "cabBase":       (["base kitchen cabinet"], ["kitchen", "cabinet"], []),
    "cabWall":       (["wall cabinet kitchen"], ["wall", "cabinet", "kitchen"], []),
    "cabTV":         (["floating tv cabinet"], ["tv", "cabinet"], []),
    "coatRack":      (["coat rack", "coat stand"], ["coat"], []),
    "wardrobe2":     (["two door wardrobe"], ["wardrobe"], []),
    "wardrobe3":     (["three door wardrobe"], ["wardrobe"], []),
    "toyCabinet":    (["toy storage cabinet"], ["toy", "cabinet", "storage"], []),
    "lockers":       (["lockers"], ["locker"], []),
    "kitchenTrolley": (["kitchen trolley cart"], ["kitchen", "trolley", "cart"], []),
    "bathShelf":     (["bathroom shelf"], ["bathroom", "shelf"], []),
    "plantShelf":    (["plant stand"], ["plant", "stand"], []),
    "kitchenIsland": (["kitchen island"], ["kitchen", "island"], []),
    "island":        (["wardrobe island"], ["wardrobe", "island"], []),

    # ---------------- 桌组 ----------------
    "desk":          (["writing desk", "office desk"], ["desk"], ["lamp"]),
    "lDesk":         (["l shaped desk"], ["desk"], []),
    "kidsDesk":      (["kids desk"], ["desk"], []),
    "standingDesk":  (["standing desk", "height adjustable desk"], ["desk"], []),
    "officeDesk":    (["office desk"], ["desk", "office"], []),
    "deskBench2":    (["two person workstation"], ["desk", "workstation"], []),
    "deskBench4":    (["four person workstation", "double desk"], ["desk", "workstation"], []),
    "bossDesk":      (["executive desk"], ["desk", "executive"], []),
    "roundMeeting":  (["round meeting table"], ["round", "table", "meeting"], []),
    "conferenceTable": (["conference table"], ["conference", "table"], []),
    "reception":     (["reception desk"], ["reception", "desk"], []),
    "trainingTable": (["training table"], ["training", "table"], []),
    "curveTrainingTable": (["curved training table"], ["curved", "table"], []),
    "longTable":     (["long dining table"], ["dining", "table", "long"], []),
    "roundTable":    (["round dining table"], ["round", "table"], []),
    "ovalTable":     (["oval dining table"], ["oval", "table"], []),
    "diningTable4":  (["four seater dining table"], ["dining", "table"], []),
    "diningTable6":  (["six seater dining table"], ["dining", "table"], []),
    "roundTable10":  (["large round table"], ["round", "table", "large"], []),
    "barTable":      (["bar height table", "high table"], ["bar", "table", "high"], []),
    "sideTable":     (["side table"], ["side", "table"], []),
    "consoleTable":  (["console table"], ["console", "table"], []),
    "teaTable":      (["tea table"], ["tea", "table"], []),
    "barCounter":    (["bar counter"], ["bar", "counter"], []),
    "lectern":       (["lectern", "podium"], ["lectern", "podium"], []),
    "nestTables":    (["nesting tables"], ["nesting", "table"], []),
    "roundCoffee":   (["round coffee table"], ["coffee", "table"], []),
    "ovalCoffee":    (["oval coffee table"], ["coffee", "table"], []),
    "coffeeTable":   (["coffee table"], ["coffee", "table"], []),

    # ---------------- 椅凳组 ----------------
    "chair":         (["dining chair", "wooden dining chair"], ["chair"], ["office", "rocking", "barber", "school", "armchair", "folding", "stool"]),
    "officeChair":   (["office chair"], ["office", "chair"], []),
    "gamingChair":   (["gaming chair"], ["gaming", "chair"], []),
    "barStool":      (["bar stool"], ["bar", "stool"], []),
    "stool":         (["wooden stool"], ["stool"], ["school", "garden", "toilet", "folding"]),
    "entryBench":    (["entryway bench", "shoe bench"], ["bench", "entry", "shoe"], ["vise", "vice", "workbench"]),
    "shoeBench":     (["shoe bench"], ["bench", "shoe"], ["vise", "vice", "workbench"]),
    "trainingChair": (["stackable training chair"], ["chair"], ["office", "gaming"]),
    "armDiningChair": (["armchair dining chair"], ["chair", "arm"], ["office"]),

    # ---------------- 沙发组 ----------------
    "sofa":          (["modern sofa", "three seat sofa"], ["sofa"], ["chinese", "outdoor", "sectional", "car"]),
    "lSofa":         (["l shaped sofa", "sectional sofa"], ["sofa", "sectional"], []),
    "loveseat":      (["two seat sofa", "loveseat"], ["sofa", "loveseat"], ["chinese", "outdoor"]),
    "uSofa":         (["u shaped sofa"], ["sofa"], ["chinese"]),
    "curvedSofa":    (["curved sofa"], ["sofa", "curved"], []),
    "bendSofa":      (["modular sofa"], ["sofa", "modular"], []),
    "chaise":        (["chaise longue"], ["chaise"], []),
    "chaiseSofa":    (["chaise lounge sofa"], ["sofa", "chaise"], []),
    "beanbag":       (["bean bag chair"], ["bean", "bag"], []),
    "ottoman":       (["ottoman", "footstool"], ["ottoman", "footstool"], ["chinese"]),
    "rockingChair":  (["rocking chair"], ["rocking"], []),
    "hangingChair":  (["hanging chair", "swing chair"], ["hanging", "swing"], ["picture", "frame"]),
    "armchair":      (["armchair"], ["armchair"], ["chinese", "barber", "dining"]),
    "booth":         (["booth seating", "banquette"], ["booth", "banquette"], ["diner", "restaurant", "car"]),
    "lounge":        (["lounge chair"], ["lounge"], []),
    "theaterSofa":   (["cinema seating", "theater seating"], ["cinema", "theater", "seating"], []),
    "fourSofa":      (["four seat sofa"], ["sofa"], []),
    "singleSofa":    (["club armchair", "single sofa"], ["sofa", "armchair"], []),
    "readingChair":  (["reading chair"], ["reading", "armchair"], []),
    "dayBed":        (["day bed"], ["day", "bed"], ["vintage"]),
    "officeSofa":     (["office reception sofa"], ["sofa", "office"], []),

    # ---------------- 床组 ----------------
    "bed":           (["modern bed frame"], ["bed"], ["gothic", "bunk", "crib"]),
    "bed15":         (["double bed"], ["double", "bed"], ["bunk", "crib"]),
    "bed12":         (["single bed"], ["single", "bed"], ["bunk", "crib"]),
    "bed20":         (["king size bed"], ["king", "bed"], ["bunk", "crib"]),
    "kingBed":       (["king size bed"], ["king", "bed"], []),
    "kidsBed":       (["kids bed"], ["kid", "bed"], []),
    "roundBed":      (["round bed"], ["round", "bed"], []),
    "bunkBed":       (["bunk bed"], ["bunk"], []),
    "crib":          (["baby crib"], ["crib"], []),
    "tatami":        (["low platform bed"], ["platform", "bed"], []),
    "bayCushion":    (["window seat cushion"], ["cushion", "window"], ["pillow", "throw"]),
    "bedBench":      (["bed bench", "end of bed bench"], ["bench", "bed"], ["vise", "vice", "workbench", "picnic"]),
    "diningBench":   (["dining bench"], ["bench", "dining"], ["vise", "vice", "workbench", "picnic"]),

    # ---------------- 其他 ----------------
    "fan":           (["floor fan", "standing fan"], ["fan"], ["ceiling", "exhaust", "ventilation"]),
    "radiator":      (["radiator"], ["radiator"], ["car", "engine"]),
    "bin":           (["waste bin", "trash can"], ["bin", "trash", "waste"], ["tool", "composter", "laptop"]),
    "clothesRack":   (["clothes drying rack"], ["clothes", "rack", "drying"], ["shoe", "bike"]),
    "catTree":       (["cat tree", "cat tower"], ["cat", "tree"], ["concrete", "statue", "dog"]),
    "petBed":        (["pet bed", "dog bed"], ["pet", "dog", "bed"], ["bunk", "crib"]),

    # ---------------- 庭院 ----------------
    "car":           (["car"], ["car"], ["cart", "coffee", "menu", "toy", "slot", "shopping", "tram"]),
    "suv":           (["suv"], ["suv", "vehicle"], []),
    "carport":       (["carport", "car shelter"], ["carport", "shelter"], []),
    "bicycle":       (["bicycle"], ["bicycle"], ["exercise", "stationary", "motor", "spin"]),
    "pool":          (["swimming pool"], ["pool", "swimming"], ["ball", "game", "puzzle", "billiard", "table"]),
    "lawn":          (["grass ground", "lawn"], ["grass", "lawn"], ["mower"]),
    "stepStones":    (["stepping stones"], ["stepping", "stone"], []),
    "tree":          (["tree"], ["tree"], ["dead", "stump", "log", "forest"]),
    "shrub":         (["shrub"], ["shrub", "bush"], []),
    "gazebo":        (["gazebo"], ["gazebo"], []),
    "parasol":       (["parasol", "garden umbrella"], ["parasol", "umbrella"], ["beach"]),
    "sunLounger":    (["sun lounger", "deck chair"], ["lounger", "deck"], []),
    "swing":         (["garden swing"], ["swing"], []),
    "bbq":           (["barbecue grill"], ["barbecue", "bbq", "grill"], ["gas", "salad"]),
    "waterFeature":  (["waterfall"], ["waterfall", "water"], []),
    "fence":         (["fence"], ["fence"], ["chainlink"]),
    "gate":          (["garden gate"], ["gate"], ["latch", "airlock", "portal"]),
    "outdoorSet":    (["outdoor patio furniture set"], ["outdoor", "patio", "terrace"], []),

    # ---------------- 建筑 ----------------
    "stairU":        (["u shaped staircase"], ["stair"], []),
    "stairRun":      (["staircase"], ["stair"], []),
    "stairLanding":  (["stair landing"], ["stair", "landing"], []),
    "elevator":      (["elevator"], ["elevator", "lift"], []),
    "evCharger":     (["ev charger", "electric vehicle charging station"], ["charger", "charging"], []),
    "garageShelf":   (["garage shelving"], ["garage", "shelv"], []),
    "workbench":     (["workbench"], ["workbench", "work", "bench"], ["vise", "vice"]),
    "stage":         (["stage platform"], ["stage", "platform"], []),
    "slidingBoard":  (["sliding whiteboard"], ["whiteboard", "sliding"], []),
    "whiteboard":    (["whiteboard"], ["whiteboard"], []),
    "wifiAP":        (["wifi router", "ceiling access point"], ["router", "wifi", "access", "point"], []),
    "ceilingSpeaker": (["ceiling speaker"], ["ceiling", "speaker"], []),
    "supplyVent":    (["air vent grille"], ["vent", "grille"], ["duct", "hose"]),
    "returnVent":    (["air vent"], ["vent"], ["duct", "hose", "fan"]),
}


def semantic_ok(title, must_any, forbid):
    """标题语义校验：must_any 里至少命中一个词组，且 forbid 全部不命中。"""
    t = (title or "").lower()
    for f in forbid:
        if f in t:
            return False
    flat = t.replace(" ", "")
    for group in must_any:
        parts = [p for p in re.split(r"[^a-z0-9]+", group.lower()) if p]
        if not parts:
            continue
        if all(p in t for p in parts):
            return True
        if all(p in flat for p in parts):
            return True
    return False


_lock = threading.Lock()
_done = [0]


def query_one(item):
    t, (queries, must_any, forbid) = item
    best = []
    seen = set()
    for q in queries:
        try:
            res = FM.search(q, limit=25)
        except Exception:
            continue
        for r in res:
            if r["id"] in seen:
                continue
            if not semantic_ok(r.get("title"), must_any, forbid):
                continue
            pc = r.get("polyCount")
            if pc is not None and (pc < 30 or pc > 400000):
                continue
            fm = r.get("formats") or []
            if not any(x in fm for x in ("glb", "gltf", "blend", "fbx", "obj", "usd")):
                continue
            seen.add(r["id"])
            best.append(r)
    best.sort(key=lambda r: (PROVIDER_RANK.get(r["provider"], 50),
                              r.get("polyCount") or 500000))
    with _lock:
        _done[0] += 1
        print("[%3d] %-20s -> %s" % (_done[0], t,
                                     (best[0]["title"] or "")[:44] if best else "NONE"))
    return t, best


def main():
    only = None
    if "--only" in sys.argv:
        only = set(sys.argv[sys.argv.index("--only") + 1].split(","))

    pm_path = os.path.join(ROOT, "assets", "external", "catalog_map.json")
    ph_map = {}
    if os.path.exists(pm_path):
        with open(pm_path, encoding="utf-8") as f:
            ph_map = json.load(f)

    items = [(t, v) for t, v in QUERIES.items()
             if not (t in ph_map and ph_map[t].get("candidates"))
             and (only is None or t in only)]
    print("待查 type: %d（并发 12）" % len(items))

    out = {}
    with cf.ThreadPoolExecutor(max_workers=12) as ex:
        futs = {ex.submit(query_one, it): it[0] for it in items}
        for fu in cf.as_completed(futs):
            t = futs[fu]
            try:
                t, best = fu.result()
            except Exception:
                best = []
            if best:
                out[t] = {"source": "shep", "candidates": best[:6]}

    failed = [t for t, _ in items if t not in out]
    print("\n多源覆盖 %d 个；仍无候选 %d 个" % (len(out), len(failed)))
    if failed:
        print("  ", ", ".join(failed))

    gp = os.path.join(ROOT, "assets", "external", "gap_map.json")
    with open(gp, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print("->", gp)


if __name__ == "__main__":
    main()

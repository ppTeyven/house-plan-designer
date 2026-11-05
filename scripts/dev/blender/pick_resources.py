"""为每一款式挑选【语义正确 + 形变最小】的现成资源（v2：类别硬门控）。

【v1 的问题（实测）】
  只用关键词匹配，导致：
    roundBed  → coffee_table_round_01   （圆床配了张圆茶几）
    acFloor   → bleach_bottle           （立式空调配了瓶漂白剂）
    teaTable  → chinese_sofa            （茶几配了张沙发）
  这就是用户说的"逻辑上的不恰"。

【v2 的做法：两层门控】
  第 1 层【类别门控】—— 必须同属一个物理类目
    资源有 cats 字段（furniture/seating/table/shelves/appliances/...），
    款式声明它属于哪个类目，不同类目直接淘汰。
    额外再排除【非家具类目】（props/tools/food/weapons/...）
  第 2 层【关键词排序】—— 同类目内按语义关键词细分排序，
    复合词（如 "dining table"）优先于单词（"table"）。

【形变】
  三轴独立缩放，distort = max(s)/min(s)。
  阈值取 1.20 —— 依据 analyze_distort.py 的实测分布：
    阈值 1.10 → 41 项 / 1.15 → 57 / 1.20 → 65 / 1.25 → 73 / 1.40 → 92
  1.20 对应"最宽与最窄轴的缩放差不超过 20%"，肉眼基本不可辨。

【失败处理】
  过不了门控的款式 → needs_human，回退到几何生成（精确按目标尺寸建）。
  绝不静默塞一个"能看但不对"的模型。
"""
import os
import sys
import json
import re

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
CACHE = os.path.join(ROOT, "assets", "_asset_cache")
EXT = os.path.join(ROOT, "assets", "external")

import fit_item as FI

# =====================================================================
# 第 1 层：类别门控
# 款式 → 允许的 Polyhaven cats（空 = 不许用现成资源，走几何生成）
# =====================================================================
CLASS_OK = {
    # ---- 坐具 ----
    "sofa": ["seating"], "lSofa": ["seating"], "loveseat": ["seating"],
    "uSofa": ["seating"], "curvedSofa": ["seating"], "bendSofa": ["seating"],
    "chaise": ["seating"], "chaiseSofa": ["seating"], "beanbag": ["seating"],
    "ottoman": ["seating"], "rockingChair": ["seating"],
    "hangingChair": ["seating"], "armchair": ["seating"],
    "booth": ["seating"], "lounge": ["seating"], "theaterSofa": ["seating"],
    "fourSofa": ["seating"], "singleSofa": ["seating"],
    "readingChair": ["seating"], "dayBed": ["seating"],
    "officeSofa": ["seating"], "gamingChair": ["seating"],
    "chair": ["seating"], "barStool": ["seating"], "stool": ["seating"],
    "officeChair": ["seating"], "entryBench": ["seating"],
    "trainingChair": ["seating"], "armDiningChair": ["seating"],
    "shoeBench": ["seating"], "diningBench": ["seating"],

    # ---- 卧具 ----
    "bed18": ["bed", "seating"], "bed15": ["bed", "seating"],
    "bed12": ["bed", "seating"], "bed20": ["bed", "seating"],
    "kingBed": ["bed", "seating"], "kidsBed": ["bed", "seating"],
    "roundBed": ["bed"], "bunkBed": ["bed"], "crib": ["bed"],

    # ---- 桌 ----
    "diningTable": ["table"], "diningTable4": ["table"],
    "diningTable6": ["table"], "coffeeTable": ["table"],
    "roundCoffee": ["table"], "ovalCoffee": ["table"],
    "longTable": ["table"], "roundTable": ["table"],
    "roundTable10": ["table"], "ovalTable": ["table"],
    "desk": ["table", "office"], "lDesk": ["table", "office"],
    "kidsDesk": ["table", "office"], "trainingTable": ["table", "office"],
    "conferenceTable": ["table", "office"],
    "curveTrainingTable": ["table", "office"],
    "standingDesk": ["table", "office"], "officeDesk": ["table", "office"],
    "deskBench2": ["table", "office"], "deskBench4": ["table", "office"],
    "bossDesk": ["table", "office"], "roundMeeting": ["table", "office"],
    "teaTable": ["table"], "barTable": ["table"],
    "sideTable": ["table"], "nestTables": ["table"],
    "nightstand": ["table"], "lectern": ["table", "office"],
    "consoleTable": ["table"],

    # ---- 柜 / 架 ----
    "wardrobe": ["shelves"], "wardrobe2": ["shelves"], "wardrobe3": ["shelves"],
    "chest": ["shelves", "containers"], "dresser": ["shelves", "containers"],
    "sideboard": ["shelves", "containers"],
    "bookshelf": ["shelves"], "bookshelfLow": ["shelves"],
    "cabinet": ["shelves"], "counter": ["shelves", "containers"],
    "wineCabinet": ["shelves", "containers"],
    "displayCabinet": ["shelves"], "shoeCabinet": ["shelves"],
    "hallCabinet": ["shelves"], "cabWardrobe": ["shelves"],
    "cabSlide": ["shelves"], "cabCorner": ["shelves"], "cabShoe": ["shelves"],
    "cabSideboard": ["shelves"], "cabTall": ["shelves"],
    "cabBase": ["shelves"], "cabWall": ["shelves"], "cabTV": ["shelves"],
    "fileCabinet": ["shelves"], "toyCabinet": ["shelves"],
    "plantShelf": ["shelves"], "lockers": ["shelves", "containers"],
    "bathShelf": ["shelves"], "kitchenTrolley": ["shelves"],

    # ---- 厨卫 ----
    "kitchenIsland": ["shelves", "containers"], "island": ["shelves", "containers"],
    "barCounter": ["shelves", "containers"], "reception": ["shelves", "containers"],
    "pantryCounter": ["shelves", "containers"], "lCounter": ["shelves"],
    "uCounter": ["shelves"],

    # ---- 电器 ----
    "fridge": ["appliances"], "fridgeDouble": ["appliances"],
    "fridgeFrench": ["appliances"], "freezer": ["appliances"],
    "dishwasher": ["appliances"], "tallOven": ["appliances"],
    "hood": ["appliances"], "microwave": ["appliances"],
    "washer": ["appliances"], "dryer": ["appliances"],
    "wineFridge": ["appliances"], "coffeeMachine": ["appliances"],
    "robotVac": ["appliances"], "airPurifier": ["appliances"],
    "purifier": ["appliances"], "waterDispenser": ["appliances"],
    "acWall": ["appliances"], "acFloor": ["appliances"],
    "waterHeater": ["appliances"], "miniHeater": ["appliances"],
    "gasHeater": ["appliances"], "boiler": ["appliances"],
    "manifold": ["appliances"], "waterSoftener": ["appliances"],

    # ---- 灯 ----
    "floorLamp": ["lighting"], "deskLamp": ["lighting"],
    "chandelier": ["lighting"], "arcLamp": ["lighting"],
    "lawnLamp": ["lighting"],

    # ---- 装饰 ----
    "rug": ["ground cover"], "roundRug": ["ground cover"],
    "doormat": ["ground cover"], "playMat": ["ground cover"],
    "yogaMat": ["ground cover"], "tatami": ["ground cover"],
    "wallArt": ["wall decoration"], "wallArt3": ["wall decoration"],
    "wallClock": ["wall decoration", "decorative"],
    "wallPanel": ["wall decoration"], "mirror": ["wall decoration"],
    "mirrorCabinet": ["wall decoration", "shelves"],
    "projScreen": ["wall decoration"], "fireplace": ["wall decoration", "decorative"],
    "fishTank": ["decorative"], "whiteboard": ["wall decoration"],
    "vase": ["vases"], "floorVase": ["vases"],

    # ---- 植物 ----
    "plant": ["potted plants", "plants"], "bigPlant": ["potted plants", "plants", "trees"],
    "smallPlant": ["potted plants", "plants", "succulent"],
    "hangingPlant": ["potted plants", "plants"],
    "tree": ["trees"], "shrub": ["plants", "ground cover"],

    # ---- 电子 ----
    "wallTV": ["electronics"], "printer": ["electronics"],
    "mobileDisplay": ["electronics"], "speaker": ["electronics"],
    "wifiAP": ["electronics"], "ceilingSpeaker": ["electronics"],

    # ---- 户外 ----
    "gazebo": ["structures", "buildings"], "carport": ["structures", "buildings"],
    "carport2": ["structures", "buildings"], "parasol": ["decorative"],
    "sunLounger": ["decorative"], "swing": ["decorative"],
    "waterFeature": ["nature"], "stepStones": ["rocks"],
    "lawn": ["ground cover"], "pool": ["structures"],
    "garageShelf": ["shelves"], "workbench": ["tools", "shelves"],
    "fence": ["structures"], "gate": ["structures"],
    "outdoorSet": ["furniture", "seating", "table"],

    # ---- 娱乐 ----
    "piano": ["instrument"], "grandPiano": ["instrument"],
    "billiards": ["furniture", "table"], "mahjong": ["furniture", "table"],
    "sauna": ["structures"], "catTree": ["decorative"], "petBed": ["seating"],
    "trashBin": ["containers"], "clothesRack": ["shelves"],
    "coatRack": ["shelves"], "stage": ["structures"],
}

# =====================================================================
# 第 2 层：关键词（同类目内排序用；复合词优先）
# 格式：款式 → [(复合词, 权重), (单词, 权重)]
# 权重越高表示语义越贴近；命中即加权，得分高的优先。
# =====================================================================
KEYWORDS = {
    "sofa": [("sofa", 10), ("couch", 10), ("chinese sofa", 6)],
    "lSofa": [("sofa", 8), ("modular", 4), ("sectional", 4)],
    "loveseat": [("sofa", 8), ("loveseat", 10), ("chinese sofa", 4)],
    "uSofa": [("sofa", 8), ("corner", 5), ("modular", 4)],
    "curvedSofa": [("sofa", 8), ("curved", 6)],
    "bendSofa": [("sofa", 8), ("corner", 4)],
    "chaise": [("chaise", 10), ("daybed", 8), ("sofa", 5)],
    "chaiseSofa": [("chaise", 10), ("sofa", 6)],
    "beanbag": [("beanbag", 12), ("bean", 8)],
    "ottoman": [("ottoman", 12), ("stool", 6), ("footstool", 8)],
    "rockingChair": [("rockingchair", 12), ("rocking", 10)],
    "hangingChair": [("hanging", 8), ("swing", 6), ("egg", 6), ("chair", 4)],
    "armchair": [("armchair", 12), ("arm chair", 12)],
    "booth": [("booth", 10), ("banquette", 10), ("sofa", 4)],
    "lounge": [("lounge", 12), ("armchair", 6), ("chair", 3)],
    "theaterSofa": [("seat", 6), ("sofa", 5), ("cinema", 8)],
    "fourSofa": [("sofa", 9)],
    "singleSofa": [("armchair", 8), ("sofa", 5), ("chair", 4)],
    "readingChair": [("armchair", 8), ("lounge", 8), ("chair", 4)],
    "dayBed": [("daybed", 12), ("day bed", 12)],
    "officeSofa": [("sofa", 7), ("loveseat", 5)],
    "gamingChair": [("gaming", 12), ("chair", 6)],
    "chair": [("dining chair", 10), ("chair", 6), ("school chair", 6),
              ("painted wooden chair", 6), ("dining chair 02", 10)],
    "barStool": [("barstool", 12), ("bar stool", 12), ("bar chair", 10),
                 ("stool", 5)],
    "stool": [("stool", 10), ("footstool", 8)],
    "officeChair": [("office", 10), ("swivel", 10), ("desk chair", 10),
                    ("chair", 4)],
    "entryBench": [("bench", 12)],
    "trainingChair": [("school chair", 12), ("school", 8), ("chair", 4)],
    "armDiningChair": [("armchair", 10), ("arm chair", 10), ("chair", 3)],
    "shoeBench": [("bench", 10)],
    "diningBench": [("bench", 10)],

    "bed18": [("bed", 10)], "bed15": [("bed", 10)], "bed12": [("bed", 9)],
    "bed20": [("bed", 10)], "kingBed": [("bed", 10)],
    "kidsBed": [("bed", 6), ("crib", 10), ("bunk", 10)],
    "roundBed": [("bed", 10), ("round bed", 12)],
    "bunkBed": [("bunk", 12), ("bed", 5)],
    "crib": [("crib", 12), ("cot", 10), ("bed", 4)],

    "diningTable": [("dining table", 12), ("table", 5), ("dining", 6)],
    "diningTable4": [("dining table", 11), ("table", 5)],
    "diningTable6": [("dining table", 11), ("table", 5)],
    "coffeeTable": [("coffee table", 12), ("cocktail table", 10), ("table", 4)],
    "roundCoffee": [("coffee table", 10), ("round table", 10), ("table", 4)],
    "ovalCoffee": [("coffee table", 10), ("oval table", 12), ("table", 4)],
    "longTable": [("dining table", 8), ("table", 6), ("long table", 10)],
    "roundTable": [("round table", 12), ("tea table", 8), ("table", 5)],
    "roundTable10": [("round table", 11), ("table", 5)],
    "ovalTable": [("oval table", 12), ("table", 5)],
    "desk": [("desk", 12), ("workstation", 10), ("table", 3)],
    "lDesk": [("desk", 10), ("table", 3)],
    "kidsDesk": [("school desk", 12), ("desk", 8), ("kids", 8)],
    "trainingTable": [("school desk", 9), ("desk", 7), ("table", 4)],
    "conferenceTable": [("conference", 12), ("meeting", 10), ("table", 5)],
    "curveTrainingTable": [("conference", 8), ("table", 5), ("desk", 4)],
    "standingDesk": [("standing", 12), ("desk", 9)],
    "officeDesk": [("office desk", 12), ("desk", 9), ("metal office desk", 12)],
    "deskBench2": [("desk", 8), ("bench", 7), ("workstation", 6)],
    "deskBench4": [("desk", 7), ("bench", 6), ("workstation", 5)],
    "bossDesk": [("desk", 9), ("executive", 12), ("office", 8)],
    "roundMeeting": [("round table", 10), ("meeting", 8), ("table", 5)],
    "teaTable": [("tea table", 12), ("chinese", 6), ("table", 4)],
    "barTable": [("bar table", 12), ("high table", 10), ("table", 4)],
    "sideTable": [("side table", 12), ("end table", 12), ("table", 5)],
    "nestTables": [("nest", 10), ("side table", 8), ("table", 4)],
    "nightstand": [("nightstand", 12), ("bedside", 12), ("side table", 7),
                   ("table", 3)],
    "lectern": [("lectern", 12), ("podium", 12)],
    "consoleTable": [("console", 12), ("table", 4)],

    "wardrobe": [("wardrobe", 12), ("closet", 10), ("cabinet", 5),
                 ("armoire", 10)],
    "wardrobe2": [("wardrobe", 12), ("closet", 10), ("cabinet", 4)],
    "wardrobe3": [("wardrobe", 12), ("closet", 10), ("cabinet", 4)],
    "chest": [("chest", 12), ("dresser", 8), ("trunk", 10), ("cabinet", 4)],
    "dresser": [("dresser", 12), ("chest", 8), ("cabinet", 4)],
    "sideboard": [("sideboard", 12), ("buffet", 12), ("credenza", 12),
                  ("cabinet", 4)],
    "bookshelf": [("bookshelf", 12), ("bookcase", 12), ("shelf", 6),
                  ("shelves", 4)],
    "bookshelfLow": [("bookshelf", 10), ("shelf", 6)],
    "cabinet": [("cabinet", 12)],
    "counter": [("counter", 12), ("kitchen", 6), ("island", 6)],
    "wineCabinet": [("wine", 12), ("cabinet", 6), ("display", 6)],
    "displayCabinet": [("display", 12), ("cabinet", 6), ("vitrine", 12),
                       ("shelf", 5)],
    "shoeCabinet": [("shoe", 12), ("cabinet", 6)],
    "hallCabinet": [("hall", 10), ("cabinet", 6), ("entry", 8)],
    "cabWardrobe": [("wardrobe", 12), ("cabinet", 6)],
    "cabSlide": [("wardrobe", 10), ("sliding", 10), ("closet", 8)],
    "cabCorner": [("corner", 12), ("wardrobe", 8)],
    "cabShoe": [("shoe", 12), ("cabinet", 6)],
    "cabSideboard": [("sideboard", 12), ("cabinet", 5)],
    "cabTall": [("tall", 10), ("cabinet", 7), ("wardrobe", 6)],
    "cabBase": [("base", 10), ("cabinet", 7), ("counter", 6)],
    "cabWall": [("wall", 10), ("cabinet", 7), ("hanging", 6)],
    "cabTV": [("tv", 12), ("media", 8), ("cabinet", 6)],
    "fileCabinet": [("file", 12), ("locker", 10), ("cabinet", 6)],
    "toyCabinet": [("toy", 12), ("cabinet", 6), ("storage", 8)],
    "plantShelf": [("plant", 10), ("shelf", 7), ("rack", 6)],
    "lockers": [("locker", 12)],
    "bathShelf": [("bath", 8), ("towel", 8), ("shelf", 6)],
    "kitchenTrolley": [("trolley", 12), ("cart", 10), ("kitchen", 6)],

    "kitchenIsland": [("kitchen", 8), ("island", 12), ("counter", 6)],
    "island": [("island", 12), ("counter", 7)],
    "barCounter": [("bar", 10), ("counter", 8)],
    "reception": [("reception", 12), ("desk", 5), ("counter", 5)],
    "pantryCounter": [("pantry", 12), ("counter", 8)],
    "lCounter": [("counter", 10), ("l shaped", 12), ("kitchen", 6)],
    "uCounter": [("counter", 10), ("u shaped", 12), ("kitchen", 6)],

    "fridge": [("fridge", 12), ("refrigerator", 12)],
    "fridgeDouble": [("fridge", 11), ("refrigerator", 10), ("double", 6)],
    "fridgeFrench": [("fridge", 11), ("french", 12), ("refrigerator", 9)],
    "freezer": [("freezer", 12), ("fridge", 8)],
    "dishwasher": [("dishwasher", 12)],
    "tallOven": [("oven", 12), ("stove", 8), ("range", 8)],
    "hood": [("hood", 12), ("extractor", 8)],
    "microwave": [("microwave", 12)],
    "washer": [("washing machine", 12), ("washer", 10)],
    "dryer": [("dryer", 12), ("tumble", 10)],
    "wineFridge": [("wine", 10), ("fridge", 9), ("cooler", 8)],
    "coffeeMachine": [("coffee", 12), ("espresso", 12), ("machine", 5)],
    "robotVac": [("robot", 12), ("vacuum", 12), ("cleaner", 8)],
    "airPurifier": [("purifier", 12), ("cleaner", 6)],
    "purifier": [("purifier", 12), ("filter", 8)],
    "waterDispenser": [("dispenser", 12), ("water", 8), ("cooler", 6)],
    "acWall": [("air conditioner", 12), ("split", 10), ("ac", 6)],
    "acFloor": [("air conditioner", 12), ("floor", 8), ("ac", 6)],
    "waterHeater": [("water heater", 12), ("boiler", 10), ("tank", 6)],
    "miniHeater": [("space heater", 12), ("heater", 9)],
    "gasHeater": [("gas", 10), ("heater", 8), ("water", 6)],
    "boiler": [("boiler", 12)],
    "manifold": [("manifold", 12), ("valve", 8), ("pipe", 6)],
    "waterSoftener": [("softener", 12), ("water", 8), ("filter", 6)],

    "floorLamp": [("floor lamp", 12), ("lamp", 6), ("light", 4)],
    "deskLamp": [("desk lamp", 12), ("lamp", 6), ("lightbulb", 8)],
    "chandelier": [("chandelier", 12), ("lamp", 5), ("lantern", 6)],
    "arcLamp": [("arc lamp", 12), ("floor lamp", 8), ("lamp", 5)],
    "lawnLamp": [("street lamp", 12), ("post lamp", 12), ("lamp", 5),
                 ("lantern", 8)],

    "rug": [("rug", 12), ("carpet", 12)],
    "roundRug": [("round rug", 12), ("rug", 8), ("carpet", 8)],
    "doormat": [("mat", 10), ("rug", 6), ("carpet", 6)],
    "playMat": [("mat", 10), ("rug", 6)],
    "yogaMat": [("yoga", 12), ("mat", 8)],
    "tatami": [("tatami", 12), ("mat", 6)],
    "wallArt": [("picture", 12), ("painting", 12), ("poster", 10),
                ("art", 8), ("frame", 6)],
    "wallArt3": [("picture", 12), ("painting", 12), ("poster", 8),
                 ("frame", 6)],
    "wallClock": [("clock", 12)],
    "wallPanel": [("panel", 12), ("wainscot", 12), ("molding", 10),
                  ("wall", 6)],
    "mirror": [("mirror", 12)],
    "mirrorCabinet": [("mirror", 10), ("cabinet", 8), ("medicine", 10)],
    "projScreen": [("projector screen", 12), ("screen", 8)],
    "fireplace": [("fireplace", 12), ("hearth", 12)],
    "fishTank": [("aquarium", 12), ("fish tank", 12), ("tank", 8)],
    "whiteboard": [("whiteboard", 12), ("board", 6)],
    "vase": [("vase", 12)],
    "floorVase": [("vase", 10), ("urn", 10), ("pot", 5)],

    "plant": [("plant", 12), ("potted", 8), ("shrub", 6)],
    "bigPlant": [("plant", 10), ("tree", 8), ("potted", 6), ("shrub", 5)],
    "smallPlant": [("succulent", 12), ("plant", 8), ("potted", 6)],
    "hangingPlant": [("hanging", 12), ("ivy", 10), ("plant", 6)],
    "tree": [("tree", 12), ("pine", 12), ("palm", 12), ("oak", 10)],
    "shrub": [("shrub", 12), ("bush", 12), ("hedge", 12), ("plant", 5)],

    "wallTV": [("television", 12), ("tv", 12), ("monitor", 10)],
    "printer": [("printer", 12)],
    "mobileDisplay": [("display", 12), ("monitor", 10), ("screen", 8)],
    "speaker": [("speaker", 12)],
    "wifiAP": [("router", 12), ("access point", 12), ("antenna", 10)],
    "ceilingSpeaker": [("speaker", 10), ("ceiling", 8)],

    "gazebo": [("gazebo", 12), ("pavilion", 12), ("shelter", 8)],
    "carport": [("carport", 12), ("canopy", 12), ("shelter", 8)],
    "carport2": [("carport", 12), ("canopy", 10), ("shelter", 7)],
    "parasol": [("parasol", 12), ("umbrella", 12), ("awning", 10),
                ("sunshade", 12)],
    "sunLounger": [("lounger", 12), ("deck chair", 12), ("sunbed", 12),
                   ("recliner", 10)],
    "swing": [("swing", 12), ("hammock", 12)],
    "waterFeature": [("waterfall", 12), ("fountain", 12), ("pond", 10)],
    "stepStones": [("stone", 8), ("step", 10), ("paving", 10), ("paver", 10)],
    "lawn": [("grass", 12), ("lawn", 12), ("turf", 12)],
    "pool": [("pool", 12), ("swimming", 12)],
    "garageShelf": [("garage", 10), ("shelf", 8), ("rack", 8)],
    "workbench": [("workbench", 12), ("workshop", 10), ("bench", 6)],
    "fence": [("fence", 12), ("railing", 10), ("balustrade", 10)],
    "gate": [("gate", 12)],
    "outdoorSet": [("outdoor", 10), ("patio", 10), ("garden", 10),
                   ("terrace", 10), ("table", 4), ("chair", 4)],

    "piano": [("piano", 12), ("upright", 8)],
    "grandPiano": [("grand piano", 12), ("piano", 8)],
    "billiards": [("billiard", 12), ("pool table", 12), ("snooker", 12)],
    "mahjong": [("mahjong", 12)],
    "sauna": [("sauna", 12)],
    "catTree": [("cat", 12), ("scratching", 10), ("tree", 6)],
    "petBed": [("pet", 12), ("cat", 8), ("dog", 8), ("bed", 5)],
    "trashBin": [("trash", 12), ("bin", 10), ("waste", 10), ("garbage", 10)],
    "clothesRack": [("clothes", 12), ("garment", 12), ("hanger", 10),
                    ("rack", 6)],
    "coatRack": [("coat", 12), ("hanger", 10), ("rack", 7)],
    "stage": [("stage", 12), ("platform", 8)],
}

# 明确禁止的类目（家具类绝不能从这些里挑）
BANNED_CATS = {"props", "tools", "food", "dishes", "weapons", "firearms",
               "ships", "books", "creature", "plants", "trees", "ground cover",
               "rocks", "flowers", "succulent", "potted plants", "plants"}


def toks(text):
    s = (text or "").lower()
    s = re.sub(r"[_\-]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def score_resource(key, model):
    """语义得分：命中关键词的权重之和。无命中返回 -1。"""
    kws = KEYWORDS.get(key)
    if not kws:
        return -1
    blob = toks(model["id"]) + " " + toks(model.get("cats", ""))
    # 复合词优先：把下划线也变成空格后再匹配
    blob2 = blob + " " + toks(model["id"].replace("_", " "))
    best = 0
    for kw, w in kws:
        if kw in blob2:
            # 复合词（多词）额外加权
            score = w * (1 + 0.6 * (len(kw.split()) - 1))
            best = max(best, score)
    return best


def cats_of(model):
    return set(c.strip() for c in str(model.get("cats", "")).split(",") if c.strip())


def pick(key, target, models, max_distort=1.20):
    """返回 (resource_id, distort, score, src_dims) 或 None。"""
    allow = CLASS_OK.get(key)
    if not allow:
        return None
    best = None
    for m in models:
        if not (m.get("w") and m.get("d") and m.get("h")):
            continue
        c = cats_of(m)
        if not (c & set(allow)):
            continue
        if c & BANNED_CATS and not (c & {"ground cover"}):
            continue
        sc = score_resource(key, m)
        if sc <= 0:
            continue
        s = [target[0] / m["w"], target[1] / m["d"], target[2] / m["h"]]
        dist = max(s) / min(s)
        # 排序键：先看语义分（高者优），同分看形变（小者优）
        k = (-round(sc), round(dist, 4))
        if best is None or k < best[0]:
            best = (k, m["id"], dist, sc, [m["w"], m["d"], m["h"]],
                    m.get("tri"))
    if best is None:
        return None
    _, rid, dist, sc, dims, tri = best
    return {"resource": rid, "distort": round(dist, 3), "score": sc,
            "src_dims": dims, "tri": tri}


def main():
    sizes = FI.load_sizes()
    with open(os.path.join(EXT, "ph_all_models.json"), encoding="utf-8-sig") as f:
        models = json.load(f)

    picked, needs_human = {}, []
    for key, target in sorted(sizes.items()):
        r = pick(key, target, models)
        if r and r["distort"] <= 1.20:
            r["target"] = target
            picked[key] = r
        else:
            needs_human.append({
                "key": key, "target": target,
                "reason": "no_class_candidate" if not r else "distort",
                "best_distort": r["distort"] if r else None,
                "best_resource": r["resource"] if r else None,
            })

    with open(os.path.join(CACHE, "pick_report.json"), "w", encoding="utf-8") as f:
        json.dump({"picked": picked, "needs_human": needs_human},
                  f, ensure_ascii=False, indent=1)

    print("挑选成功 %d / 回退几何生成 %d（共 %d）"
          % (len(picked), len(needs_human), len(sizes)))
    print()
    print("=== 资源复用分布 ===")
    usage = {}
    for k, v in picked.items():
        usage.setdefault(v["resource"], []).append(k)
    for rid, ks in sorted(usage.items(), key=lambda x: -len(x[1])):
        print("  %-30s x%-3d %s" % (rid, len(ks), ", ".join(ks[:8])))
    print()
    print("=== 回退几何生成（%d）===" % len(needs_human))
    for n in sorted(needs_human, key=lambda x: x["key"]):
        print("  %-18s %-18s target=%s best=%s"
              % (n["key"], n["reason"], n["target"], n["best_resource"]))


if __name__ == "__main__":
    main()

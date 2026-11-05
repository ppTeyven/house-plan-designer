"""为每一款式挑选现成资源 —— v5 终版（严格语义门控）。

【v4 的问题（实测）】
  L2 档（仅品类命中）仍产生语义错误：
    printer → lightbulb_led、catTree → brass_vase_02、
    trashBin → ceramic_vase_01、parasol → chinese_chandelier
  原因：品类门控太宽（"containers"里混了花瓶和铁桶）。

【v5 的规则：关键词必须命中（L1），否则几何生成】
  库里 521 个模型里，家具类只有 85 个。
  卫浴（马桶/浴缸/台盆）、地毯、楼梯、台球桌、钢琴、升降晾衣架… 库里根本没有。
  对这些品类，几何生成【不是妥协，而是最优解】：
    · 尺寸精确等于目标值（形变恒为 1.0）
    · 语义绝对正确（是马桶就是马桶）
  而硬套一个"看起来像"的东西反而违背用户要求。

【最终分配原则】
  L1（关键词命中 + 比例达标）→ 用现成资源，形状与细节是真的
  L2（关键词命中但比例不达标）→ 几何生成（精确尺寸）
  无关键词命中 → 几何生成

【数据】
  assets/external/ph_all_models.json —— 521 个模型的 id/cats/tri/w/d/h（实测）
  reference/catalog-sizes.json      —— 251 个款式的目标尺寸（唯一真源）
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
from pick_resources import CLASS_OK, cats_of

# 【摆位修正后的资源尺寸】——优先于原样尺寸使用。
# 有些资源的零件是侧躺/散落的，原样包围盒失真，
# 会导致"本来很合适的资源"被误杀。详见 measure_posed.py。
_POSED_PATH = os.path.join(CACHE, "ph_dims_posed.json")
POSE_DIMS = {}
if os.path.exists(_POSED_PATH):
    try:
        with open(_POSED_PATH, encoding="utf-8") as f:
            _pd = json.load(f)
        for _k, _v in _pd.items():
            POSE_DIMS[_k] = [_v["w"], _v["d"], _v["h"]]
    except Exception:
        POSE_DIMS = {}


# =====================================================================
# 严格语义表：款式 → 必须命中的关键词（命中 id 或 cats）
# 只列 Polyhaven 库中真实存在的品类；库里没有的品类不写在这里，
# 会自动落到几何生成。
# =====================================================================
REQUIRE = {
    # ---------------- 坐具 ----------------
    "sofa": ["sofa"], "lSofa": ["sofa"], "loveseat": ["sofa"],
    "uSofa": ["sofa"], "curvedSofa": ["sofa"], "bendSofa": ["sofa"],
    "chaise": ["sofa", "daybed"], "chaiseSofa": ["sofa", "daybed"],
    "beanbag": [], "ottoman": ["ottoman", "stool"],
    "rockingChair": ["rockingchair"], "hangingChair": [],
    "armchair": ["armchair", "arm chair"], "booth": ["sofa"],
    "lounge": ["lounge"], "theaterSofa": ["sofa", "seat"],
    "fourSofa": ["sofa"], "singleSofa": ["armchair", "sofa", "chair"],
    "readingChair": ["armchair", "lounge", "chair"],
    "dayBed": ["daybed"], "officeSofa": ["sofa", "loveseat"],
    "gamingChair": ["gaming"],
    "chair": ["chair"], "barStool": ["barstool", "bar chair", "bar stool"],
    "stool": ["stool"], "officeChair": ["office", "swivel", "desk chair"],
    "entryBench": ["bench"], "trainingChair": ["school chair", "school"],
    "armDiningChair": ["armchair", "arm chair"], "shoeBench": ["bench"],
    "diningBench": ["bench"],

    # ---------------- 卧具 ----------------
    "bed18": ["bed"], "bed15": ["bed"], "bed12": ["bed"],
    "bed20": ["bed"], "kingBed": ["bed"], "kidsBed": ["bed", "crib"],
    "roundBed": [], "bunkBed": ["bunk"], "crib": ["crib"],

    # ---------------- 桌 ----------------
    "diningTable": ["dining table", "table"],
    "diningTable4": ["dining table", "table"],
    "diningTable6": ["dining table", "table"],
    "coffeeTable": ["coffee table"], "roundCoffee": ["coffee table", "round table"],
    "ovalCoffee": ["coffee table", "oval table"],
    "longTable": ["dining table", "table"], "roundTable": ["round table", "tea table", "table"],
    "roundTable10": ["round table", "table"],
    "ovalTable": ["oval table", "table"],
    "desk": ["desk", "workstation"], "lDesk": ["desk"],
    "kidsDesk": ["school desk", "desk"], "trainingTable": ["school desk", "desk"],
    "conferenceTable": ["conference", "meeting"],
    "curveTrainingTable": ["conference", "meeting"],
    "standingDesk": ["standing"], "officeDesk": ["office desk", "metal office desk", "desk"],
    "deskBench2": ["desk", "workstation"], "deskBench4": ["desk", "workstation"],
    "bossDesk": ["desk"], "roundMeeting": ["round table", "meeting"],
    "teaTable": ["tea table"], "barTable": ["bar table", "high table"],
    "sideTable": ["side table", "end table"], "nestTables": ["nest"],
    "nightstand": ["nightstand", "bedside", "side table"],
    "lectern": ["lectern", "podium"], "consoleTable": ["console"],

    # ---------------- 柜 / 架 ----------------
    "wardrobe": ["wardrobe", "closet", "cabinet", "armoire"],
    "wardrobe2": ["wardrobe", "closet", "cabinet"],
    "wardrobe3": ["wardrobe", "closet", "cabinet"],
    "chest": ["chest of drawers", "dresser", "commode", "chest"],
    # 【关键】"commode" 是复合词（等级 2，精确品类）：
    #   Polyhaven 的五斗柜 GothicCommode_01 / chinese_commode 的 cats 含 "commode"，
    #   而 "chest" 会命中 metal_tool_chest（工具箱）—— 梳妆台配工具箱是语义错配。
    "dresser": ["dresser", "commode", "chest of drawers", "chest"],
    "sideboard": ["sideboard", "buffet", "credenza", "commode"],
    "bookshelf": ["bookshelf", "bookcase", "shelf", "shelves"],
    "bookshelfLow": ["bookshelf", "bookcase", "shelf", "shelves"],
    "cabinet": ["cabinet"], "counter": ["counter", "kitchen", "island"],
    "wineCabinet": ["wine", "cabinet"], "displayCabinet": ["display", "vitrine", "cabinet"],
    "shoeCabinet": ["shoe"], "hallCabinet": ["hall", "entry", "cabinet"],
    "cabWardrobe": ["wardrobe", "cabinet"], "cabSlide": ["wardrobe", "sliding", "closet"],
    "cabCorner": ["corner"], "cabShoe": ["shoe"],
    "cabSideboard": ["sideboard", "cabinet"], "cabTall": ["tall", "cabinet", "wardrobe"],
    "cabBase": ["base", "counter", "kitchen"], "cabWall": ["wall", "cabinet", "hanging"],
    "cabTV": ["tv", "media"], "fileCabinet": ["file", "locker"],
    "toyCabinet": ["toy", "storage"],
    "plantShelf": ["plant", "shelf", "rack"],
    "lockers": ["locker"], "bathShelf": ["bath", "towel", "shelf"],
    "kitchenTrolley": ["trolley", "cart"],

    # ---------------- 台面 / 中岛 ----------------
    "kitchenIsland": ["island", "kitchen", "counter"],
    "island": ["island", "counter"], "barCounter": ["bar", "counter"],
    "reception": ["reception"], "pantryCounter": ["pantry", "counter"],
    "lCounter": ["counter", "kitchen", "l shaped"],
    "uCounter": ["counter", "kitchen", "u shaped"],

    # ---------------- 电器 ----------------
    "fridge": ["fridge", "refrigerator"], "fridgeDouble": ["fridge", "refrigerator"],
    "fridgeFrench": ["fridge", "refrigerator"], "freezer": ["freezer", "fridge"],
    "dishwasher": ["dishwasher"], "tallOven": ["oven", "stove", "range"],
    "hood": ["hood", "extractor"], "microwave": ["microwave"],
    "washer": ["washing machine", "washer"], "dryer": ["dryer", "tumble"],
    "wineFridge": ["wine", "fridge", "cooler"],
    "coffeeMachine": ["coffee", "espresso", "kettle"],
    "robotVac": ["robot", "vacuum", "cleaner"],
    "airPurifier": ["purifier", "cleaner"], "purifier": ["purifier", "filter"],
    "waterDispenser": ["dispenser", "cooler"],
    "acWall": ["air conditioner", "aircon", "split"],
    "acFloor": ["air conditioner", "aircon", "floor"],
    "waterHeater": ["water heater", "boiler"],
    "miniHeater": ["space heater", "heater", "kettle"],
    "gasHeater": ["gas", "heater"], "boiler": ["boiler"],
    "manifold": ["manifold", "valve"], "waterSoftener": ["softener", "filter"],

    # ---------------- 灯 ----------------
    # 【关键】"floor lamp"/"desk lamp" 是精确品类（等级 2）；
    # 单用 "lamp" 会命中 vintage_oil_lamp（油灯）这种桌面小摆件。
    "floorLamp": ["floor lamp", "lamp", "oil lamp"],
    "deskLamp": ["desk lamp", "lamp", "sconce"],
    "chandelier": ["chandelier"], "arcLamp": ["arc lamp", "floor lamp"],
    "lawnLamp": ["street lamp", "post lamp", "lamp", "lantern", "diya"],

    # ---------------- 装饰 ----------------
    "rug": [], "roundRug": [], "doormat": [], "playMat": [], "yogaMat": [],
    "tatami": [],
    "wallArt": ["picture", "painting", "poster", "art", "frame"],
    "wallArt3": ["picture", "painting", "poster", "art", "frame"],
    "wallClock": ["clock"], "wallPanel": ["panel", "wainscot", "molding"],
    "mirror": ["mirror"], "mirrorCabinet": ["mirror", "medicine"],
    "projScreen": ["projector screen", "screen", "board"],
    "fireplace": ["fireplace", "hearth"], "fishTank": ["aquarium", "fish tank", "tank"],
    "whiteboard": ["whiteboard", "chalkboard"],
    "vase": ["vase"], "floorVase": ["vase", "urn", "jug"],
    "alarmClock": ["clock", "alarm"], "mantelClock": ["clock", "mantel"],
    "doormat": [], "coatrack": [],

    # ---------------- 植物 ----------------
    # 【关键】室内绿植必须命中 "potted"（盆栽，含盆），
    # 不能只靠 "plant" —— 因为 Polyhaven 的 trees 分类里
    # fir_tree_01 / pine_sapling_medium 等【整棵树】的 cats 也含 "plant"，
    # 只匹配 "plant" 会让 19 米高的雪松被缩放成 1.4 米的室内绿植
    # （实测：plant 被选成 fir_tree_01，bigPlant 被选成 pine_sapling_medium）。
    # "potted" 只出现在真正带花盆的资源上，语义精确。
    "plant": ["potted plant"], "bigPlant": ["potted plant"],
    "smallPlant": ["succulent", "potted plant"],
    "hangingPlant": ["hanging", "ivy"],
    "tree": ["tree", "pine", "palm", "quiver"], "shrub": ["shrub", "bush", "hedge"],

    # ---------------- 电子 ----------------
    "wallTV": ["television", "tv", "monitor"], "printer": ["printer"],
    "mobileDisplay": ["display", "monitor", "screen"],
    "speaker": ["speaker"], "wifiAP": ["router", "access point", "antenna"],
    "ceilingSpeaker": ["speaker"],

    # ---------------- 户外 ----------------
    "gazebo": ["gazebo", "pavilion"], "carport": ["carport", "canopy"],
    "carport2": ["carport", "canopy"],
    "parasol": ["parasol", "umbrella", "awning", "sunshade"],
    "sunLounger": ["lounger", "deck chair", "sunbed", "recliner"],
    "swing": ["swing", "hammock"],
    "waterFeature": ["waterfall", "fountain", "pond"],
    "stepStones": ["stone", "step", "paving", "paver"],
    "lawn": ["grass", "lawn", "turf"], "pool": ["pool", "swimming"],
    "garageShelf": ["garage", "shelf", "rack"],
    "workbench": ["workbench", "workshop", "bench"],
    "fence": ["fence", "chainlink"], "gate": ["gate"],
    "outdoorSet": ["outdoor", "patio", "garden", "terrace"],

    # ---------------- 娱乐 / 其他 ----------------
    "piano": ["piano"], "grandPiano": ["grand piano", "piano"],
    "billiards": ["billiard", "pool table", "snooker"],
    "mahjong": ["mahjong"], "sauna": ["sauna"],
    "catTree": ["cat"], "petBed": ["pet", "cat", "dog", "bed"],
    "trashBin": ["trash", "bin", "waste", "garbage", "jerrycan"],
    "clothesRack": ["clothes", "garment", "hanger"],
    "coatRack": ["coat", "hanger"], "stage": ["stage", "platform"],
}


# =====================================================================
# 【v6】排除词表 —— 命中即淘汰（不是降级）
#
# 【为什么需要】
#   Polyhaven 的资源 id 常带修饰词，修饰词会改变品类语义：
#     metal_tool_chest   → 命中 "chest"，但它是【工具箱】，不是五斗柜
#     vintage_oil_lamp   → 命中 "lamp"，但它是【油灯摆件】，不是落地灯
#     metal_office_desk  → 命中 "desk"/"table"，但它是【办公桌】，不是餐桌
#   只靠关键词匹配，这些会伪装成命中。用户的原话是
#   "必须保证整栋房子里所有的家具之间都没有违和感" +
#   "摆放在屋子里不能有任何逻辑上的不恰" —— 所以必须显式排除。
#
# 【原则】
#   只写【实测发现的真实错配】，不凭空臆造。
#   每个排除词都对应 pick_report.json 里的一条具体错配记录。
# =====================================================================
EXCLUDE = {
    # 梳妆台/五斗柜 —— 不能配工具箱
    "dresser": ("tool", "treasure"),
    "chest": ("tool", "treasure"),
    # 落地灯 —— 不能配油灯/煤油灯摆件
    "floorLamp": ("oil", "kerosene", "vintage"),
    "lawnLamp": ("oil", "kerosene", "vintage"),
    # 餐桌 —— 不能配办公桌/工业台
    "diningTable": ("office", "industrial", "tool", "portable"),
    "diningTable4": ("office", "industrial", "tool", "portable"),
    "diningTable6": ("office", "industrial", "tool", "portable"),
    "longTable": ("office", "industrial", "tool", "portable"),
    "ovalTable": ("office", "industrial", "tool", "portable"),
    "coffeeTable": ("office", "industrial", "tool", "portable"),
    "roundCoffee": ("office", "industrial", "tool", "portable"),
    "roundTable": ("office", "industrial", "tool", "portable"),
    "roundTable10": ("office", "industrial", "tool", "portable"),
    # 书架 —— 不能配工业货架
    "bookshelf": ("industrial", "steel"),
    # 室内绿植 —— 不能配整棵树
    "plant": ("tree", "pine", "fir", "palm", "quiver", "sapling"),
    "bigPlant": ("tree", "pine", "fir", "palm", "quiver", "sapling"),
    "smallPlant": ("tree", "pine", "fir", "palm", "quiver", "sapling"),
}


# =====================================================================
# 【v6】精确语义命中的放宽阈值。
#
# 【为什么需要】
#   语义精确命中的资源（如 dining_table / potted_plant_01）往往尺寸
#   与目标差 20%~35%（因为它们是"真实世界的标准尺寸"，而目标尺寸是
#   目录里给的具体款式的尺寸）。旧逻辑把这些直接淘汰，
#   结果让泛命中资源顶替 —— 餐桌配成办公桌、绿植配成雪松。
#
# 【阈值依据】
#   1.40 = 三轴缩放比最大/最小。
#   经验判据：1.40 时最宽与最窄轴差 40%，
#   在家具尺度下（如餐桌 1600×900×750 → 2256×1390×877）
#   视觉上仍能接受；超过 1.40 才明显"被拉扁"。
#   命中率为 43→? 见 pick_report.json 的 semantic_level 字段分布。
#
# 【约束】
#   只对【语义等级=2（精确品类命中】】放宽；
#   泛命中（等级 1）仍用原阈值 1.12~1.35。
#   两阶段都无解 → 返回 None → 走几何生成（尺寸精确，语义绝对正确）。
HARD_TH = 1.40


def toks(text):
    s = (text or "").lower()
    s = re.sub(r"[_\-]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def toks_split(text):
    """在 toks() 的基础上【额外】按驼峰/数字边界再切一刀。

    【为什么需要】
      Polyhaven 的资源 id 常常是「品类名 + 编号」的连写形式：
        GothicCommode_01 → "gothiccommode 01"
        ClassicNightstand_01 → "classicnightstand 01"
        Sofa_01 → "sofa 01"
      连写会让精确关键词失配：
        "commode" 匹配不到 "gothiccommode 01"（没有空格），
        于是 dresser 只能命中 "chest" → 配出 metal_tool_chest（工具箱）。
      这里把驼峰边界切开：
        GothicCommode_01 → "gothic commode 01"
        Sofa_01 → "sofa 01"（本来就对）
      这样 "commode" / "nightstand" 这类精确品类词才能命中。
    """
    s = text or ""
    # 【顺序关键】必须【先切驼峰再小写】——
    # 反过来的话 toks() 已经把 "GothicCommode" 变成 "gothiccommode"，
    # 驼峰边界信息丢失，切分正则永远不匹配（这是实测踩到的坑）。
    s = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", s)
    s = re.sub(r"[_\-]+", " ", s)
    s = re.sub(r"(?<=[A-Za-z])(?=\d)", " ", s)
    s = re.sub(r"(?<=\d)(?=[A-Za-z])", " ", s)
    s = s.lower()
    return re.sub(r"\s+", " ", s).strip()


def keyword_hit(key, model):
    """关键词是否命中该资源。返回 (命中词, 权重, 语义等级) 或 (None, 0, 0)。

    复合词权重更高（"dining table" 比 "table" 更精确）。

    【语义等级】v6 新增 —— 区分"精确命中品类"与"泛命中大类"：
      2 = 精确品类（"dining table" / "potted plant"）
      1 = 品类内的合理变体（"table"）
      0 = 未命中
    排序时【等级优先于形变】：一个精确命中但形变 1.6 的资源，
    应该好过一个泛命中且形变 1.1 的资源 —— 因为后者是"办公桌当餐桌"。
    """
    reqs = REQUIRE.get(key)
    if not reqs:
        return None, 0, 0
    # 【两种分词都试】连写 id 需要驼峰切分（GothicCommode → gothic commode），
    # 复合关键词需要在连续词序上匹配（"dining table"）。
    id_toks = toks_split(model["id"])
    blob = id_toks + " | " + toks(model.get("cats", ""))
    best, bestw, bestlvl = None, 0, 0
    for kw in reqs:
        if kw not in blob:
            continue
        # 【排除词】资源 id 里的修饰词会改变语义：
        #   metal_tool_chest 命中 "chest"，但 "tool" 说明它是工具箱，不是五斗柜。
        #   vintage_oil_lamp 命中 "lamp"，但 "oil" 说明它是油灯，不是落地灯。
        #   metal_office_desk 命中 "desk"/"table"，但 "office" 说明它是办公桌。
        # 命中任一排除词 → 该资源直接出局（不是降级，是淘汰）。
        bad = EXCLUDE.get(key) or ()
        if any(b in id_toks for b in bad):
            continue
        w = 10 + 5 * (len(kw.split()) - 1)
        # 多词复合词 = 精确品类；单词 = 泛命中
        lvl = 2 if len(kw.split()) > 1 else 1
        if w > bestw:
            best, bestw, bestlvl = kw, w, lvl
    return best, bestw, bestlvl


def thin_axes(t):
    mx = max(t)
    return [i for i in range(3) if t[i] < mx * 0.15]


def distort_of(target, src):
    t, s = list(target), list(src)
    thin = thin_axes(t)
    axes = [i for i in range(3) if i not in thin] or [0, 1, 2]
    sc = [t[i] / s[i] for i in axes if s[i] > 0]
    if not sc:
        return 999.0, 0
    return max(sc) / min(sc), len(axes)


def flatness(t):
    return min(t) / max(t) if max(t) else 0.0


def shape_ok(target, src):
    ft, fs = flatness(target), flatness(src)
    if ft < 0.12:
        return fs < 0.30
    if ft < 0.45:
        return fs < 0.60
    return fs > 0.18


def threshold_for(target):
    """按【三轴】形状特征决定形变阈值。

    【为什么必须看三轴】
      旧实现只看宽深的宽高比 ar，对"细高"和"扁宽"两类判断失准：
        trashBin 目标 300×300×600（细高）
          只看宽深 → ar=1.0 → 阈值 1.12
          但垃圾桶的现成资源是 613×556×977（同样细高）
          三轴缩放比 0.49/0.54/0.61 → 形变 1.255（肉眼几乎看不出）
      所以细高/扁宽件要放宽到 1.30，其余保持 1.20/1.35。
    """
    w, d, h = target
    ar = max(w, d) / max(1, min(w, d))
    # 三轴最扁的那一维（相对最大轴）
    flat = min(w, d, h) / max(w, d, h)
    if ar > 2.2:
        return 1.35
    if flat < 0.55:
        # 细高 / 扁宽（厚度或高度远小于其它两轴）→ 放宽
        return 1.30
    if ar < 1.15:
        return 1.12
    return 1.20


def pick(key, target, models):
    """返回 info dict 或 None。

    【v6 两阶段选择 —— 语义优先】
      旧逻辑（单阶段）：候选按形变硬淘汰（dist > th 即出局），
      再按 (语义权重, 形变) 排序。
      后果：语义最精确的资源往往形变略超阈值而被淘汰，
      剩下"办公桌"这种泛命中资源顶替 —— 餐桌配成办公桌、
      梳妆台配成工具箱、客厅绿植配成 19 米雪松。
      这正是用户说的"逻辑上的不恰"。

      新逻辑：
        阶段一：只在【语义等级 = 精确命中(2)】的候选里选，
                阈值放宽到 HARD_TH（1.40）—— 因为精确命中优先于形变完美。
        阶段二：若阶段一为空，再用【泛命中(1)】候选，
                阈值回到原 th（1.12~1.35）。
        两阶段都空 → 返回 None → 走几何生成（精确尺寸，语义绝对正确）。

      这样：
        diningTable → dining_table（精确命中，形变 1.321，在 1.40 内）
                      而不是 metal_office_desk（泛命中）
        plant       → potted_plant_01（精确命中"potted plant"）
                      而不是 fir_tree_01（泛命中"plant"）
    """
    allow = CLASS_OK.get(key)
    if not allow:
        return None
    th = threshold_for(target)

    # ---- 收集通过形状门控的候选 ----
    cands = []
    for m in models:
        if not (m.get("w") and m.get("d") and m.get("h")):
            continue
        c = cats_of(m)
        if not (c & set(allow)):
            continue
        kw, kw_w, kw_lvl = keyword_hit(key, m)
        if not kw:
            continue
        src = POSE_DIMS.get(m["id"]) or [m["w"], m["d"], m["h"]]
        if not shape_ok(target, src):
            continue
        dist, naxes = distort_of(target, src)
        cands.append((kw_lvl, kw_w, dist, kw, m, src, naxes))

    # ---- 阶段一：精确命中 ----
    exact = [c for c in cands if c[0] == 2]
    if exact:
        pool, lim = exact, HARD_TH
    else:
        pool, lim = [c for c in cands if c[0] == 1], th

    best = None
    for kw_lvl, kw_w, dist, kw, m, src, naxes in pool:
        if dist > lim:
            continue
        # 语义等级 → 语义权重 → 形变
        k = (-kw_lvl, -kw_w, round(dist, 4))
        if best is None or k < best[0]:
            best = (k, m, dist, kw, kw_w, naxes, kw_lvl, lim)
    # 【修复】阶段一【有候选但全部超形变阈值】时，必须回落阶段二，
    # 而不是直接返回 None。
    # 实测 bug：diningTable4 有 23 个 table 类候选，
    # 其中 dining_table 精确命中但形变 1.608 > HARD_TH(1.40)，
    # 于是整轮放弃 → 该款式被丢进"几何生成"白模列表。
    # 正确做法：精确命中都不合格时，退回泛命中（等级 1），
    # 用更严格的 th 阈值重新挑 —— 语义略泛但有真实贴图，
    # 远好过"几何白模"。
    if best is None and exact:
        pool, lim = [c for c in cands if c[0] == 1], th
        for kw_lvl, kw_w, dist, kw, m, src, naxes in pool:
            if dist > lim:
                continue
            k = (-kw_lvl, -kw_w, round(dist, 4))
            if best is None or k < best[0]:
                best = (k, m, dist, kw, kw_w, naxes, kw_lvl, lim)
    if best is None:
        return None
    _, m, dist, kw, kw_w, naxes, kw_lvl, lim = best
    src = POSE_DIMS.get(m["id"]) or [m["w"], m["d"], m["h"]]
    return {"resource": m["id"], "distort": round(dist, 3),
            "keyword": kw, "src_dims": src, "semantic_level": kw_lvl,
            "tri": m.get("tri"), "cats": m.get("cats"),
            "axes": naxes, "threshold": lim}


def main():
    sizes = FI.load_sizes()
    # 【尺寸真源】ph_dims.json —— 从 GLB 实测的世界包围盒。
    # 【为什么不用 ph_all_models.json】那份文件轴序混用
    # （有的 Y-up、有的 Z-up），实测 13/40 与 GLB 不一致，
    # 会导致"挑选时合格、构建时被拒"。详见 measure_ph.py。
    dims_path = os.path.join(CACHE, "ph_dims.json")
    if not os.path.exists(dims_path):
        raise SystemExit("缺少 %s —— 先运行 python measure_ph.py" % dims_path)
    with open(dims_path, encoding="utf-8") as f:
        measured = json.load(f)

    models = []
    for rid, d in measured.items():
        models.append({"id": rid, "cats": d.get("cats", ""),
                       "w": d["w"], "d": d["d"], "h": d["h"],
                       "tri": d.get("tri")})
    print("资源池 %d 个（实测尺寸） / 目标款式 %d 个" % (len(models), len(sizes)))

    picked, geo = {}, []
    for key, target in sorted(sizes.items()):
        r = pick(key, list(target), models)
        if r:
            r["target"] = list(target)
            picked[key] = r
        else:
            geo.append(key)

    with open(os.path.join(CACHE, "pick_report.json"), "w", encoding="utf-8") as f:
        json.dump({"picked": picked, "geo_fallback": geo},
                  f, ensure_ascii=False, indent=1)

    print("现成资源 %d / 几何生成 %d / 共 %d"
          % (len(picked), len(geo), len(sizes)))
    print()
    ds = sorted(v["distort"] for v in picked.values())
    if ds:
        print("形变 min=%.3f p50=%.3f p90=%.3f max=%.3f"
              % (ds[0], ds[len(ds) // 2], ds[int(len(ds) * 0.9)], ds[-1]))
    print()
    print("=== 现成资源映射 ===")
    for k, v in sorted(picked.items()):
        print("  %-18s -> %-30s d=%.3f/th=%.2f kw=%-14s %s"
              % (k, v["resource"], v["distort"], v["threshold"],
                 v["keyword"], v["src_dims"]))
    print()
    print("=== 几何生成（%d）===" % len(geo))
    print("  " + ", ".join(geo))


if __name__ == "__main__":
    main()

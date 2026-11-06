"""材质角色体系的【唯一真源】—— 角色名、贴图映射、语义判定都在这里。

【为什么必须有这个文件（手册第 2 条：不新增类型映射散落）】
  之前角色规则散落在 4 个文件里，彼此不一致，实测造成两类严重错配：

  ① normalize_glb.ROLE_BY_HINT / embed_pbr.NAME_ROLE 用【子串匹配】：
       "metal_trash_can" 含子串 "ash"（来自 "trash"）
       → 命中 ("ash", "wood_oak") → 铁桶被判成【白橡木】
     实测 12 个 PH 模型的原始 PolyHaven 贴图因此被错误角色覆盖，
     或材质直接错配。这是"乱码"的直接来源之一。

  ② 猜不到关键字就【兜底返回 fabric_oat】：
       dining_table / GothicCabinet_01 / CoffeeTable_01 / WoodenChair_01
       全都猜不出 → 全打成 U_fabric_oat（燕麦布）
     → 木餐桌、衣柜、咖啡桌渲染成米色布家具。

  本模块提供【按词元精确匹配】的判定：
     · 先把材质名切成词元（_ / - / 空格 / 驼峰边界）
     · 只在【完整词元】上匹配，绝不做子串匹配
     · 匹配不到时返回 None（由调用方决定如何处理，绝不静默兜底）

【角色 → 贴图】
  ROLE_TEX 是角色到 ambientCG 扫描贴图前缀的唯一映射。
  玻璃不贴图（玻璃要有折射/透明，不能用表面扫描图硬凑）。

用法：
  from roles import role_from_name, ROLE_TEX, ROLE_METAL
  role_from_name("metal_trash_can")   -> 'metal_black'
  role_from_name("potted_plant_01_pot") -> 'ceramic_white'
  role_from_name("dining_table")      -> None   （不猜，交给上层按类型定）
"""
import re

# =====================================================================
# 角色 → ambientCG 扫描贴图前缀（唯一真源）
# =====================================================================
ROLE_TEX = {
    "wood_oak": "role_wood_oak",
    "wood_walnut": "role_wood_walnut",
    "fabric_oat": "role_fabric_oat",
    "fabric_oat_d": "role_fabric_oat_dark",
    "fabric_cream": "role_fabric_cream",
    "fabric_grey": "role_fabric_grey",
    "metal_black": "role_metal_black",
    "metal_steel": "role_metal_steel",
    "metal_brass": "role_metal_brass",
    "ceramic_white": "role_ceramic_white",
    "stone_light": "role_stone_light",
    "stone_dark": "role_stone_dark",
    "leaf": "role_leaf",
    "leaf_dark": "role_leaf",
    # 草坪（地面草皮）—— 与 leaf（叶片）区分：
    #   leaf  = 树叶/灌木（Leaf001 扫描叶片）
    #   grass = 草皮地面（Grass004 草地）
    # 两者纹理完全不同：叶片有叶脉与透光，草皮是密集短草。
    "grass": "role_grass",
}

# 各角色的物理金属度（写进 ORM 的 B 通道）
ROLE_METAL = {
    "wood_oak": 0.0, "wood_walnut": 0.0,
    "fabric_oat": 0.0, "fabric_oat_d": 0.0,
    "fabric_cream": 0.0, "fabric_grey": 0.0,
    "metal_black": 0.85, "metal_steel": 0.92, "metal_brass": 0.95,
    "ceramic_white": 0.0,
    "stone_light": 0.0, "stone_dark": 0.0,
    "leaf": 0.0, "leaf_dark": 0.0,
    "grass": 0.0,
}

# 不贴图的材质（玻璃靠折射，不能用表面扫描图）
NO_TEXTURE_ROLES = {"glass_clear"}

# =====================================================================
# 词元切分
# =====================================================================
_CAMEL = re.compile(r"(?<=[a-z0-9])(?=[A-Z])")
_SEP = re.compile(r"[_\-\s.]+")


def tokens(name):
    """把材质名切成小写词元列表。

    例：
      "metal_trash_can"    -> ['metal', 'trash', 'can']
      "potted_plant_01_pot"-> ['potted', 'plant', '01', 'pot']
      "GothicCabinet_01"   -> ['gothic', 'cabinet', '01']
      "modern_coffee_table_02_wood" -> ['modern','coffee','table','02','wood']
    """
    if not name:
        return []
    s = _CAMEL.sub(" ", name)
    s = _SEP.sub(" ", s)
    return [t for t in s.lower().split() if t]


def _has_token(toks, word):
    """词元完全相等匹配（不是子串！）。"""
    return word in toks


def _has_phrase(toks, phrase):
    """词元序列匹配（短语，如 'dining table'）。"""
    words = phrase.split()
    n = len(words)
    return any(toks[i:i + n] == words for i in range(len(toks) - n + 1))


# =====================================================================
# 词元 → 角色规则（按优先级从高到低）
#
# 【规则形式】(匹配器, 角色)
#   匹配器是 (kind, value)：
#     ('tok', 'wood')  → 存在完整词元 'wood'
#     ('phr', 'dining table') → 存在连续词元 'dining table'
#     ('suffix', 'leaves') → 最后一个词元是 'leaves'
#
# 【为什么要区分 suffix】
#   PolyHaven 的命名规范里，后缀直接说明部件材质：
#     potted_plant_01_pot     → 陶瓷花盆
#     potted_plant_01_leaves  → 叶片
#     vintage_cabinet_01_glass→ 玻璃
#     fancy_picture_frame_01_canvas → 画布
#   但 'pot' 同时出现在 'potted' 里 —— 只有【末尾词元】才是真信号。
# =====================================================================
_RULES = [
    # --- 1. PolyHaven 部件后缀（最精确，优先级最高） ---
    ("suffix", "leaves", "leaf"),
    ("suffix", "leaf", "leaf"),
    ("suffix", "foliage", "leaf"),
    ("suffix", "flowers", "leaf"),
    ("suffix", "flower", "leaf"),
    ("suffix", "pot", "ceramic_white"),
    ("suffix", "planter", "ceramic_white"),
    ("suffix", "glass", "glass_clear"),
    ("suffix", "crystal", "glass_clear"),
    ("suffix", "mirror", "glass_clear"),
    ("suffix", "canvas", "fabric_cream"),
    ("suffix", "cloth", "fabric_oat"),
    ("suffix", "fabric", "fabric_oat"),
    ("suffix", "upholstery", "fabric_oat"),
    ("suffix", "leather", "fabric_grey"),
    ("suffix", "velvet", "fabric_grey"),
    ("suffix", "cushion", "fabric_oat"),
    ("suffix", "paper", "fabric_cream"),
    ("suffix", "shade", "fabric_cream"),
    ("suffix", "wood", "wood_walnut"),
    ("suffix", "timber", "wood_oak"),
    ("suffix", "steel", "metal_steel"),
    ("suffix", "iron", "metal_black"),
    ("suffix", "brass", "metal_brass"),
    ("suffix", "chrome", "metal_steel"),
    ("suffix", "stone", "stone_light"),
    ("suffix", "marble", "stone_light"),
    ("suffix", "concrete", "stone_light"),
    ("suffix", "ceramic", "ceramic_white"),
    ("suffix", "porcelain", "ceramic_white"),

    # --- 2. 词元精确匹配：木 ---
    ("tok", "walnut", "wood_walnut"),
    ("tok", "oak", "wood_oak"),
    ("tok", "wood", "wood_walnut"),
    ("tok", "wooden", "wood_walnut"),
    ("tok", "timber", "wood_oak"),
    ("tok", "plywood", "wood_oak"),
    ("tok", "veneer", "wood_oak"),
    ("tok", "teak", "wood_walnut"),
    ("tok", "birch", "wood_oak"),
    ("tok", "mahogany", "wood_walnut"),
    ("tok", "bamboo", "wood_oak"),
    ("tok", "rattan", "wood_walnut"),
    ("tok", "cane", "wood_oak"),
    ("tok", "wenge", "wood_walnut"),
    ("tok", "ash", "wood_oak"),          # 完整词元 'ash'（白蜡木）才算
    ("tok", "pine", "wood_oak"),
    # --- 2a. 家具成品词（Polyhaven 整件资源名里没有材质词，只有品类词） ---
    # vintage_cabinet_01_a / painted_wooden_cabinet_02 等：按品类兜底为木，
    # 否则 role=None → 材质名保持原样 → 前端 kv() 只认 U_ 前缀而不给 PBR → 看着像贴图丢了。
    # 【注意】只收"几乎一定是木"的柜类词；桌/椅/办公桌材质不定（木/金属/塑料都有），
    # 必须留给上层按款式类型定，绝不能在这里硬判成木（metal_office_desk 就是反例）。
    ("tok", "cabinet", "wood_walnut"),
    ("tok", "wardrobe", "wood_walnut"),
    ("tok", "closet", "wood_walnut"),
    ("tok", "drawer", "wood_walnut"),
    ("tok", "dresser", "wood_walnut"),
    ("tok", "shelf", "wood_oak"),
    ("tok", "shelves", "wood_oak"),
    ("tok", "bookcase", "wood_walnut"),
    ("tok", "sideboard", "wood_walnut"),
    ("tok", "credenza", "wood_walnut"),
    ("tok", "cupboard", "wood_walnut"),
    ("tok", "nightstand", "wood_walnut"),
    ("tok", "clock", "wood_walnut"),
    ("tok", "heliophila", "leaf"),
    ("tok", "flower", "leaf"),
    ("tok", "heleo", "leaf"),
    ("tok", "kettle", "metal_steel"),
    ("tok", "heater", "metal_black"),

    # --- 2b. 画框 / 镜框：木框 ---
    # 【实测】wallArt 用的是 PolyHaven 的 fancy_picture_frame_01，
    #   原始材质名里既没有 'wood' 也没有木材词元
    #   → role_from_name 返回 None → 材质名保持原样
    #   → ORM 修正逻辑因角色未知而跳过 → 灰度粗糙度图仍直挂
    #     metallicRoughnessTexture → 金属度被误读成 0.544 → 脏污反光。
    # 画框在语义上就是木框，按短语优先判定。
    ("phr", "picture frame", "wood_walnut"),
    ("phr", "picture frames", "wood_walnut"),
    ("phr", "art frame", "wood_walnut"),
    ("phr", "photo frame", "wood_walnut"),
    ("tok", "frame", "wood_walnut"),

    # --- 3. 词元精确匹配：布 ---
    ("tok", "linen", "fabric_cream"),
    ("tok", "cotton", "fabric_cream"),
    ("tok", "wool", "fabric_oat"),
    ("tok", "felt", "fabric_grey"),
    ("tok", "velvet", "fabric_grey"),
    ("tok", "leather", "fabric_grey"),
    ("tok", "suede", "fabric_grey"),
    ("tok", "canvas", "fabric_cream"),
    ("tok", "cloth", "fabric_oat"),
    ("tok", "fabric", "fabric_oat"),
    ("tok", "textile", "fabric_oat"),
    ("tok", "uphol", "fabric_oat"),
    ("tok", "cushion", "fabric_oat"),
    ("tok", "fiber", "fabric_grey"),

    # --- 4. 词元精确匹配：金属 ---
    ("tok", "brass", "metal_brass"),
    ("tok", "gold", "metal_brass"),
    ("tok", "copper", "metal_brass"),
    ("tok", "bronze", "metal_brass"),
    ("tok", "chrome", "metal_steel"),
    ("tok", "aluminium", "metal_steel"),
    ("tok", "aluminum", "metal_steel"),
    ("tok", "steel", "metal_steel"),
    ("tok", "iron", "metal_black"),
    ("tok", "metal", "metal_black"),
    ("tok", "metallic", "metal_black"),
    ("tok", "powder", "metal_black"),
    ("tok", "painted", "metal_black"),
    ("tok", "rust", "metal_black"),

    # --- 5. 词元精确匹配：陶瓷 / 石 / 玻璃 ---
    ("tok", "ceramic", "ceramic_white"),
    ("tok", "porcelain", "ceramic_white"),
    ("tok", "concrete", "stone_light"),
    ("tok", "stone", "stone_light"),
    ("tok", "marble", "stone_light"),
    ("tok", "granite", "stone_dark"),
    ("tok", "slate", "stone_dark"),
    ("tok", "travertine", "stone_light"),
    ("tok", "terrazzo", "stone_light"),
    ("tok", "glass", "glass_clear"),
    ("tok", "mirror", "glass_clear"),

    # --- 6. 词元精确匹配：植物 ---
    ("tok", "leaf", "leaf"),
    ("tok", "leaves", "leaf"),
    ("tok", "foliage", "leaf"),
    ("tok", "plant", "leaf"),
    ("tok", "grass", "grass"),
    ("tok", "lawn", "grass"),
    ("tok", "moss", "leaf"),

    # --- 7. 短语（多词，优先于单词） ---
    ("phr", "dining table", "wood_walnut"),
    ("phr", "coffee table", "wood_walnut"),
    ("phr", "side table", "wood_walnut"),
    ("phr", "tea table", "wood_walnut"),
    ("phr", "console table", "wood_walnut"),
    ("phr", "rattan weave", "wood_walnut"),
    ("phr", "steel frame", "metal_steel"),
    ("phr", "metal frame", "metal_black"),
    ("phr", "potted plant", "leaf"),
]

# 编译成 (kind, value, role) 三元组
_COMPILED = []
for _kind, _val, _role in _RULES:
    if _kind == "phr":
        _COMPILED.append(("phr", _val.split(), _role))
    else:
        _COMPILED.append((_kind, _val, _role))


def role_from_name(name):
    """按材质名猜角色。**猜不到返回 None，绝不兜底 fabric_oat。**

    【为什么绝不兜底】
      猜错时静默给 fabric_oat 会让木家具变成布家具 ——
      这种错误在渲染图里"看着有材质"，但语义完全错，
      比直接留空更危险（用户说"乱码"指的就是这种）。
      返回 None 让上层【显式】决定：按款式类型定，或标记为待定。
    """
    toks = tokens(name)
    if not toks:
        return None
    # 后缀规则先判（PolyHaven 部件命名最精确）
    for kind, val, role in _COMPILED:
        if kind == "suffix" and toks[-1] == val:
            return role
    # 短语优先
    for kind, val, role in _COMPILED:
        if kind == "phr" and _has_phrase(toks, " ".join(val)):
            return role
    # 单词元
    for kind, val, role in _COMPILED:
        if kind == "tok" and _has_token(toks, val):
            return role
    return None


if __name__ == "__main__":
    # 自检：这些是实测踩过的坑
    cases = [
        ("metal_trash_can", "metal_black"),      # 不能因 'ash' 判成木
        ("metal_trash_can_rust", "metal_black"),
        ("wooden_crate_01", "wood_walnut"),
        ("potted_plant_01_pot", "ceramic_white"),
        ("potted_plant_01_leaves", "leaf"),
        ("potted_plant_02_leaves", "leaf"),
        ("vintage_cabinet_01_glass", "glass_clear"),
        ("fancy_picture_frame_01_canvas", "fabric_cream"),
        ("fancy_picture_frame_01", "wood_walnut"),   # 画框 → 木框
        ("modern_coffee_table_02_wood", "wood_walnut"),
        ("vintage_microwave_glass", "glass_clear"),
        ("basecolor_classic_chandelier_1", None),  # 猜不出就返回 None
        ("dining_table", "wood_walnut"),    # 短语 'dining table' → 木
        ("GothicCabinet_01", "wood_walnut"),  # 柜类词兜底 → 木（否则前端不给 PBR）
        ("WoodenChair_01", "wood_walnut"),
        ("CoffeeTable_01", "wood_walnut"),  # 短语 'coffee table' → 木
        ("side_table_01", "wood_walnut"),
        ("chinese_tea_table", "wood_walnut"),
        ("metal_office_desk", "metal_black"),
        ("bar_chair_round_01", None),        # 椅子材质猜不出 → 交上层按类型定
        ("school_chair_01", None),
    ]
    bad = 0
    for name, expect in cases:
        got = role_from_name(name)
        ok = got == expect
        if not ok:
            bad += 1
        print("  %-34s -> %-14s (期望 %-14s) %s"
              % (name, got, expect, "OK" if ok else "!!! 不符"))
    print("\n不符 %d / %d" % (bad, len(cases)))

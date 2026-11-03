"""全屋统一色板（palette）—— 所有家具共用同一套配色，保证配套不违和。

设计原则：
  · 木质：同一胡桃木/白橡木两种基色，全屋不混用第三种木色
  · 布料：燕麦米色为主色系，抱枕用低饱和暖色点缀（不超过 3 种）
  · 金属：哑光黑 + 黄铜两种，柜门拉手统一哑光黑，装饰件统一黄铜
  · 玻璃/陶瓷：中性灰白，不抢视觉
所有建模脚本从 palette 取色，禁止各自定义颜色。
"""

PAL = {
    # ---- 木质（家具主体，全屋统一） ----
    "wood_walnut":  "#6B4A2D",   # 胡桃木（主）
    "wood_walnut_d": "#54391F",   # 胡桃木深（缝隙/阴影层/踢脚）
    "wood_oak":     "#B08D5F",   # 白橡（次要，用于餐桌/床架）
    "wood_oak_d":   "#8E6E47",   # 白橡深

    # ---- 布料（沙发/床/椅，暖米色系） ----
    "fabric_oat":    "#C9BBA6",   # 燕麦米（主布料）
    "fabric_oat_d":  "#9D8F7A",   # 燕麦米深（底座/踢脚/内衬）
    "fabric_cream":  "#F2EDE2",   # 米白（抱枕/床品/搭毯）
    "fabric_grey":   "#9AA0A6",   # 冷灰（现代简约款）

    # ---- 抱枕点缀色（低饱和，暖色为主，最多 3 种） ----
    "accent_terracotta": "#D4743A",  # 陶土橙
    "accent_sage":      "#7E9273",  # 灰绿
    "accent_indigo":    "#4A6B8A",  # 靛蓝
    "accent_mustard":   "#C99A3E",  # 芥末黄（点缀）

    # ---- 金属 ----
    "metal_black":  "#22252A",   # 哑光黑（柜门拉手/脚/支架）
    "metal_brass":  "#A8843E",   # 黄铜（装饰脚/花器/灯饰）
    "metal_steel":  "#8A9096",   # 不锈钢（卫浴/厨房）

    # ---- 玻璃 / 陶瓷 / 石材 ----
    "glass_clear": "#CFD8DC",
    "ceramic_white": "#F4F5F3",
    "stone_light": "#C6C3BC",
    "stone_dark": "#4C4A47",

    # ---- 缝线 ----
    "thread_oat": "#D8CDB8",
    "thread_dark": "#6D6354",

    # ---- 植物 ----
    "leaf": "#4F7A45",
    "leaf_dark": "#356030",
    "soil": "#3A2E26",
}

# 各家具的材质角色映射（建模脚本引用这里的角色名）
ROLES = {
    "sofa": {
        "main": "fabric_oat", "dark": "fabric_oat_d", "welt": "metal_black",
        "thread": "thread_oat", "leg": "wood_walnut", "metal": "metal_brass",
        "accent": ["accent_terracotta", "accent_sage"],
    },
    "bed": {
        "main": "fabric_oat", "dark": "fabric_oat_d", "welt": "metal_black",
        "thread": "thread_oat", "leg": "wood_walnut", "metal": "metal_brass",
        "accent": ["accent_terracotta", "accent_indigo"],
    },
    "chair": {
        "main": "fabric_oat", "dark": "fabric_oat_d", "welt": "metal_black",
        "thread": "thread_oat", "leg": "wood_walnut", "metal": "metal_brass",
        "accent": [],
    },
    "diningTable": {
        "main": "wood_oak", "dark": "wood_oak_d", "welt": "metal_black",
        "thread": "thread_oat", "leg": "wood_oak", "metal": "metal_brass",
        "accent": [],
    },
    "coffeeTable": {
        "main": "wood_walnut", "dark": "wood_walnut_d", "welt": "metal_black",
        "thread": "thread_oat", "leg": "wood_walnut", "metal": "metal_brass",
        "accent": [],
    },
    "tvCabinet": {
        "main": "wood_walnut", "dark": "wood_walnut_d", "welt": "metal_black",
        "thread": "thread_oat", "leg": "wood_walnut", "metal": "metal_black",
        "accent": [],
    },
    "wardrobe": {
        "main": "wood_walnut", "dark": "wood_walnut_d", "welt": "metal_black",
        "thread": "thread_oat", "leg": "wood_walnut", "metal": "metal_black",
        "accent": [],
    },
    "nightstand": {
        "main": "wood_walnut", "dark": "wood_walnut_d", "welt": "metal_black",
        "thread": "thread_oat", "leg": "wood_walnut", "metal": "metal_brass",
        "accent": [],
    },
    "cabinet": {
        "main": "wood_walnut", "dark": "wood_walnut_d", "welt": "metal_black",
        "thread": "thread_oat", "leg": "wood_walnut", "metal": "metal_black",
        "accent": [],
    },
}


def hexof(role_or_key):
    """按角色名或色板 key 取十六进制颜色"""
    if role_or_key in PAL:
        return PAL[role_or_key]
    for r in ROLES.values():
        if role_or_key in r.values():
            for v in r.values():
                if isinstance(v, list):
                    if role_or_key in v:
                        return PAL[role_or_key]
                elif v == role_or_key:
                    return PAL[role_or_key]
    raise KeyError("unknown palette key: %s" % role_or_key)
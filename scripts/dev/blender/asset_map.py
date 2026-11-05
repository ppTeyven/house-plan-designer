"""251 项目录 → 资源映射表（单一真源）。

【为什么单独一张表】
  验收站 catalog.json 有 251 个款式 key（如 lSofa / loveseat / fourSofa ...），
  但现成资源库的模型是【品类级】的（如 "Sofa_01" / "sofa_03"）。
  两者不是一一对应。一张显式的映射表解决：
    · 哪款用哪个资源
    · 该资源的朝向修正（yaw 旋转）
    · 该资源的尺寸修正（相对原型的缩放/目标尺寸）
    · 该款是否为占位（无合适现成资源时显式标注，不静默复用）

【维度基准】
  catalog.json 的 key 是唯一真源；尺寸来自 make_manifest.py 的 SPEC 区间
  （真实家具尺寸区间，非拍脑袋）。
  type → SPEC 键的映射与 catalog 一致（cat 字段）。

【输出】assets/_asset_cache/asset_map.json
"""
import os
import sys
import json

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
ACC = os.path.join(ROOT, "验收")
CACHE = os.path.join(ROOT, "assets", "_asset_cache")


def load_catalog():
    with open(os.path.join(ACC, "models", "catalog.json"), encoding="utf-8") as f:
        return json.load(f)


def all_keys(cat):
    out = []
    for g in cat["groups"]:
        for it in g["items"]:
            out.append((it["key"], it["type"], it["name"], g["name"]))
    return out


# =====================================================================
# 【第一部分】Polyhaven 可用资源 → 品类
# Polyhaven 的家具类模型清单（来自 survey 前的初筛，真实面数以 survey 为准）
#   沙发: Sofa_01, sofa_02, sofa_03, chinese_sofa, mid_century_lounge_chair
#   椅:  ArmChair_01, GreenChair_01, WoodenChair_01, SchoolChair_01, BarberShopChair_01,
#        dining_chair_02, chinese_armchair, metal_stool_01/02/03, folding_wooden_stool,
#        bar_chair_round_01, painted_wooden_chair_01/02, gallinera_chair,
#        plastic_monobloc_chair_01, rockingchair_01
#   桌:  CoffeeTable_01, WoodenTable_01/02/03, dining_table, round_wooden_table_01/02,
#        small_wooden_table_01, side_table_01, side_table_tall_01, chinese_console_table,
#        chinese_tea_table, painted_wooden_table, industrial_coffee_table,
#        gothic_coffee_table, modern_coffee_table_01/02, coffee_table_round_01,
#        school_desk, metal_office_desk, outdoor_table_chair_set_01, wooden_picnic_table
#   床:  GothicBed_01, old_bed_frame, vintage_day_bed
#   柜:  GothicCabinet_01, GothicCommode_01, chinese_cabinet, chinese_commode,
#        drawer_cabinet, modern_wooden_cabinet, painted_wooden_cabinet/02,
#        vintage_cabinet_01, steel_frame_shelves_01/02/03, Shelf_01, classic_console_01,
#        wooden_bookshelf_worn, wooden_display_shelves_01, painted_wooden_shelves,
#        industrial_storage_cart, tool_chest, metal_toolbox
#   灯:  Chandelier_01/02/03, chinese_chandelier, caged_hanging_light, ceiling_fan,
#        desk_lamp_arm_01, hanging_industrial_lamp, industrial_caged_sconce,
#        industrial_wall_lamp, industrial_wall_sconce, lantern_01, lantern_chandelier_01,
#        modern_ceiling_lamp_01, mounted_fluorescent_lights, pull_chain_light_socket,
#        wooden_lantern_01, vintage_oil_lamp, street_lamp_01/02, antique_ceramic_vase_01
#   摆件: Ottoman_01, Rockingchair_01, classic_console_01, vintage_day_bed,
#        wardrobe?(无), throw_pillows_01, potted_plant_01/02/04, planter_pot_clay,
#        potted_plant_01, ceramic_vase_01..04, antique_ceramic_vase_01,
#        fancy_picture_frame_01/02, hanging_picture_frame_01/02/03,
#        standing_picture_frame_01/02, mantel_clock_01, wall_clock, alarm_clock_01,
#        security_camera_01, projector_screen, television_01/02, vintage_microwave,
#        electric_stove, large_castle_door, large_iron_gate, rollershutter_door,
#        modular_chainlink_fence, modular_street_seating, street_lamp_01/02
# =====================================================================

# 款式 key → (资源ID, 资源库, yaw_deg, 目标最大边mm 或 None=用原型原尺寸, 说明)
#   yaw_deg : 资源自身朝向 → 房间约定的"正面朝 +Y 或 -Y"
#   size_mm : 若给出，则强制缩放到该最大边（保证比例与摆放合理）
#   None    : 表示"该款暂无独立资源，待定"
PH = "polyhaven"

MAP = {
    # ================= 沙发组 =================
    "sofa":        ("Sofa_01", PH, 0, 2265, "三人沙发基准，改造型软包"),
    "lSofa":       ("sofa_03", PH, 0, 2800, "L 形（若为直排则做模块化拼装）"),
    "loveseat":    ("sofa_02", PH, 0, 1800, "双人沙发"),
    "uSofa":       (None, None, 0, None, "U 形：需 3 段拼接"),
    "curvedSofa":  (None, None, 0, None, "弧形：Polyhaven 无"),
    "bendSofa":    (None, None, 0, None, "异形组合：Polyhaven 无"),
    "chaise":      ("sofa_02", PH, 0, 1800, "贵妃椅（沙发模块）"),
    "beanbag":     (None, None, 0, None, "懒人沙发：无"),
    "ottoman":     ("Ottoman_01", PH, 0, 600, "圆脚凳"),
    "rockingChair": ("Rockingchair_01", PH, 0, 700, "摇椅"),
    "hangingChair": (None, None, 0, None, "吊椅：无"),
    "armchair":    ("ArmChair_01", PH, 0, 850, "单人沙发"),
    "booth":       (None, None, 0, None, "卡座：需定制"),
    "lounge":      ("mid_century_lounge_chair", PH, 0, 780, "休闲椅"),
    "theaterSofa": (None, None, 0, None, "影院三连座：需拼接"),
    "fourSofa":    ("Sofa_01", PH, 0, 2600, "四人沙发（加宽）"),
    "singleSofa":  ("sofa_02", PH, 0, 1000, "单人位"),
    "chaiseSofa":  ("sofa_03", PH, 0, 2600, "贵妃位"),
    "readingChair": ("GreenChair_01", PH, 0, 750, "阅读椅"),
    "dayBed":      ("vintage_day_bed", PH, 0, 2000, "罗汉床"),
    "officeSofa":  ("Sofa_01", PH, 0, 2000, "办公接待"),

    # ================= 椅凳组 =================
    "chair":       ("WoodenChair_01", PH, 0, 460, "餐椅"),
    "barStool":    ("bar_chair_round_01", PH, 0, 400, "吧椅"),
    "stool":       ("chinese_stool", PH, 0, 400, "圆凳/化妆凳"),
    "officeChair": ("metal_stool_01", PH, 0, 600, "办公椅（近似）"),
    "gamingChair": (None, None, 0, None, "电竞椅：无"),
    "entryBench":  ("wooden_picnic_table", PH, 0, 900, "换鞋凳（长凳近似）"),
    "trainingChair": ("SchoolChair_01", PH, 0, 450, "培训椅"),
    "armDiningChair": ("chinese_armchair", PH, 0, 600, "扶手餐椅"),
    "shoeBench":   ("wooden_picnic_table", PH, 0, 1200, "穿鞋凳"),
    "diningBench": ("wooden_picnic_table", PH, 0, 1400, "餐凳"),

    # ================= 床组 =================
    "bed18":       ("GothicBed_01", PH, 0, 2000, "双人床 1.8m"),
    "bed15":       ("GothicBed_01", PH, 0, 1700, "双人床 1.5m"),
    "bed12":       ("old_bed_frame", PH, 0, 1300, "单人床 1.2m"),
    "bed20":       ("GothicBed_01", PH, 0, 2200, "双人床 2.0m"),
    "roundBed":    (None, None, 0, None, "圆床：无"),
    "bunkBed":     (None, None, 0, None, "上下床：无"),
    "crib":        (None, None, 0, None, "婴儿床：无"),
    "tatami":      (None, None, 0, None, "榻榻米：几何生成"),
    "kingBed":     ("GothicBed_01", PH, 0, 2400, "King 2.2m"),
    "kidsBed":     ("old_bed_frame", PH, 0, 1100, "儿童床"),
    "nightstand":  ("ClassicNightstand_01", PH, 0, 520, "床头柜"),
    "bedBench":    ("Ottoman_01", PH, 0, 1200, "床尾凳"),
    "bayCushion":  (None, None, 0, None, "飘窗垫：几何生成"),

    # ================= 桌组 =================
    "diningTable": ("dining_table", PH, 0, 1800, "餐桌"),
    "coffeeTable": ("CoffeeTable_01", PH, 0, 1200, "茶几"),
    "roundCoffee": ("coffee_table_round_01", PH, 0, 1000, "圆茶几"),
    "ovalCoffee":  ("modern_coffee_table_02", PH, 0, 1200, "椭圆茶几"),
    "longTable":   ("WoodenTable_01", PH, 0, 2600, "长餐桌"),
    "roundTable":  ("round_wooden_table_01", PH, 0, 1400, "圆餐桌"),
    "ovalTable":   ("WoodenTable_03", PH, 0, 2000, "椭圆餐桌"),
    "consoleTable": ("chinese_console_table", PH, 0, 1200, "玄关桌"),
    "sideTable":   ("side_table_01", PH, 0, 500, "边几"),
    "kitchenIsland": (None, None, 0, None, "中岛台：无"),
    "island":      (None, None, 0, None, "衣帽岛台：无"),
    "teaTable":    ("chinese_tea_table", PH, 0, 1200, "茶台"),
    "barCounter":  (None, None, 0, None, "吧台：无"),
    "barTable":    ("chinese_tea_table", PH, 0, 1100, "吧台桌"),
    "lectern":     (None, None, 0, None, "讲台：无"),
    "trainingTable": ("SchoolDesk_01", PH, 0, 2400, "培训桌"),
    "curveTrainingTable": (None, None, 0, None, "弧形培训桌：无"),
    "conferenceTable": ("dining_table", PH, 0, 3000, "会议桌"),
    "desk":        ("metal_office_desk", PH, 0, 1400, "书桌"),
    "lDesk":       (None, None, 0, None, "L 形书桌：需拼接"),
    "kidsDesk":    ("SchoolDesk_01", PH, 0, 1000, "儿童学习桌"),
    "standingDesk": ("metal_office_desk", PH, 0, 1400, "升降书桌"),
    "officeDesk":  ("metal_office_desk", PH, 0, 1400, "办公桌"),
    "deskBench2": ("SchoolDesk_01", PH, 0, 1400, "两人工位"),
    "deskBench4": ("SchoolDesk_01", PH, 0, 2800, "四人工位"),
    "bossDesk":    (None, None, 0, None, "大班台：无"),
    "roundMeeting": ("round_wooden_table_02", PH, 0, 1200, "圆形洽谈桌"),
    "reception":   (None, None, 0, None, "前台：无"),
    "nestTables":  ("coffee_table_round_01", PH, 0, 700, "组合圆茶几"),
    "diningTable4": ("dining_table", PH, 0, 1200, "四人餐桌"),
    "diningTable6": ("dining_table", PH, 0, 2000, "六人餐桌"),
    "roundTable10": ("round_wooden_table_01", PH, 0, 2000, "十人圆桌"),
    "deskBench2b": (None, None, 0, None, ""),

    # ================= 柜组 =================
    "wardrobe":    ("GothicCabinet_01", PH, 0, 1630, "衣柜"),
    "chest":       ("GothicCommode_01", PH, 0, 1000, "五斗柜"),
    "dresser":     ("chinese_commode", PH, 0, 1200, "梳妆台"),
    "fileCabinet": ("drawer_cabinet", PH, 0, 500, "文件柜"),
    "bookshelf":   ("wooden_bookshelf_worn", PH, 0, 900, "书架"),
    "tvCabinet":   ("modern_wooden_cabinet", PH, 0, 1820, "电视柜"),
    "sideboard":   ("painted_wooden_cabinet_02", PH, 0, 1800, "餐边柜"),
    "wineCabinet": ("vintage_cabinet_01", PH, 0, 700, "酒柜"),
    "displayCabinet": ("chinese_cabinet", PH, 0, 1200, "展示柜"),
    "shoeCabinet": ("drawer_cabinet", PH, 0, 900, "鞋柜"),
    "hallCabinet": ("Shelf_01", PH, 0, 1000, "玄关柜"),
    "cabWardrobe": ("GothicCabinet_01", PH, 0, 1800, "定制衣柜"),
    "cabSlide":    (None, None, 0, None, "推拉门衣柜：无"),
    "cabCorner":   (None, None, 0, None, "转角衣柜：需拼接"),
    "cabShoe":     ("drawer_cabinet", PH, 0, 900, "定制鞋柜"),
    "cabSideboard": ("painted_wooden_cabinet_02", PH, 0, 1800, "定制餐边柜"),
    "cabTall":     ("steel_frame_shelves_01", PH, 0, 2000, "书柜/高柜"),
    "cabBase":     (None, None, 0, None, "地柜：无"),
    "cabWall":     (None, None, 0, None, "吊柜：无"),
    "cabTV":       (None, None, 0, None, "悬空电视柜：无"),
    "coatRack":    (None, None, 0, None, "衣帽架：无"),
    "wardrobe2":   ("GothicCabinet_01", PH, 0, 1100, "两门衣柜"),
    "wardrobe3":   ("GothicCabinet_01", PH,0, 1500, "三门衣柜"),
    "toyCabinet":  ("drawer_cabinet", PH, 0, 900, "儿童玩具柜"),
    "bookshelfLow": ("steel_frame_shelves_02", PH, 0, 900, "矮书架"),
    "lockers":     ("steel_frame_shelves_03", PH, 0, 1200, "储物柜"),
    "kitchenTrolley": ("industrial_storage_cart", PH, 0, 800, "厨房推车"),
    "bathShelf":   ("steel_frame_shelves_03", PH, 0, 700, "置物架"),
    "plantShelf":  ("painted_wooden_shelves", PH, 0, 900, "花架"),

    # ================= 灯具 =================
    "floorLamp":   ("street_lamp_01", PH, 0, 1600, "落地灯"),
    "deskLamp":    ("desk_lamp_arm_01", PH, 0, 450, "台灯"),
    "lawnLamp":    ("street_lamp_02", PH, 0, 800, "草坪灯"),
    "chandelier":  ("Chandelier_01", PH, 0, 1200, "大吊灯"),
    "arcLamp":     ("hanging_industrial_lamp", PH, 0, 1800, "钓鱼灯"),

    # ================= 电器 =================
    "fireplace":   (None, None, 0, None, "电壁炉：无"),
    "wallTV":      ("Television_01", PH, 0, 1300, "壁挂电视"),
    "projScreen":  ("projector_screen", PH, 0, 2400, "投影幕"),
    "speaker":     (None, None, 0, None, "落地音箱：无"),

    # ================= 卫浴 =================
    "toilet":      (None, None, 0, None, "马桶：无"),
    "wallToilet":  (None, None, 0, None, "壁挂马桶：无"),
    "squatToilet": (None, None, 0, None, "蹲便器：无"),
    "vanity":      ("GothicCommode_01", PH, 0, 1200, "浴室柜"),
    "doubleVanity": ("GothicCommode_01", PH, 0, 1800, "双盆浴室柜"),
    "mirrorCabinet": (None, None, 0, None, "镜柜：无"),
    "pedestalSink": (None, None, 0, None, "立柱盆：无"),
    "freeTub":     (None, None, 0, None, "独立浴缸：无"),
    "bathtub":     (None, None, 0, None, "浴缸：无"),
    "shower":      (None, None, 0, None, "淋浴房：几何生成"),
    "showerScreen": (None, None, 0, None, "淋浴隔断：几何生成"),
    "showerSet":   (None, None, 0, None, "恒温淋浴：无"),
    "towelWarmer": (None, None, 0, None, "毛巾架：无"),
    "bathHeater":  (None, None, 0, None, "浴霸：无"),
    "laundrySink": (None, None, 0, None, "洗衣池：无"),
    "urinal":      (None, None, 0, None, "小便器：无"),
    "serviceSink": (None, None, 0, None, "拖布池：无"),
    "pantryCounter": ("drawer_cabinet", PH, 0, 1200, "茶水间台面"),
    "counter":     ("drawer_cabinet", PH, 0, 2400, "一字橱柜"),
    "lCounter":    (None, None, 0, None, "L 形橱柜：需拼接"),
    "uCounter":    (None, None, 0, None, "U 形橱柜：需拼接"),

    # ================= 厨电 =================
    "fridge":      ("vintage_microwave", PH, 0, 700, "冰箱（近似）"),
    "fridgeDouble": (None, None, 0, None, "对开门：无"),
    "fridgeFrench": (None, None, 0, None, "法式多门：无"),
    "freezer":     (None, None, 0, None, "冰柜：无"),
    "dishwasher":  (None, None, 0, None, "洗碗机：无"),
    "tallOven":    ("electric_stove", PH, 0, 600, "电器高柜"),
    "hood":        (None, None, 0, None, "油烟机：无"),
    "microwave":   ("vintage_microwave", PH, 0, 500, "微波炉"),
    "coffeeMachine": (None, None, 0, None, "咖啡机：无"),
    "wineFridge":  ("vintage_microwave", PH, 0, 400, "红酒柜"),
    "waterDispenser": ("vintage_electric_kettle", PH, 0, 350, "饮水机"),
    "washer":      (None, None, 0, None, "洗衣机：无"),
    "dryer":       (None, None, 0, None, "烘干机：无"),
    "airPurifier": (None, None, 0, None, "空气净化器：无"),
    "robotVac":    (None, None, 0, None, "扫地机：无"),
    "acWall":      ("exterior_aircon_unit", PH, 0, 900, "挂机空调"),
    "acFloor":     ("exterior_aircon_unit", PH, 0, 400, "柜机空调"),
    "waterHeater": (None, None,0, None, "热水器：无"),
    "miniHeater":  (None, None, 0, None, "小厨宝：无"),
    "gasHeater":   (None, None, 0, None, "燃气热水器：无"),
    "boiler":      (None, None, 0, None, "壁挂炉：无"),
    "manifold":    (None, None, 0, None, "分集水器：无"),
    "waterSoftener": (None, None, 0, None, "软水机：无"),
    "purifier":    (None, None, 0, None, "净水器：无"),

    # ================= 娱乐 =================
    "fishTank":    (None, None, 0, None, "鱼缸：几何生成"),
    "piano":       (None, None, 0, None, "立式钢琴：无"),
    "grandPiano":  (None, None, 0, None, "三角钢琴：无"),
    "treadmill":   (None, None, 0, None, "跑步机：无"),
    "billiards":   (None, None, 0, None, "台球桌：无"),
    "mahjong":     (None, None, 0, None, "麻将桌：无"),
    "sauna":       (None, None, 0, None, "桑拿：无"),
    "bike":        (None, None, 0, None, "动感单车：无"),
    "yogaMat":     (None, None, 0, None, "瑜伽垫：几何生成"),

    # ================= 办公 =================
    "mobileDisplay": (None, None, 0, None, "会议平板：无"),
    "printer":     (None, None, 0, None, "打印机：无"),

    # ================= 其他 =================
    "mirror":      (None, None, 0, None, "穿衣镜：无"),
    "fan":         ("ceiling_fan", PH, 0, 1300, "落地扇（吊扇近似）"),
    "radiator":    (None, None, 0, None, "暖气片：无"),
    "trashBin":    ("metal_trash_can", PH, 0, 350, "垃圾桶"),
    "clothesRack": (None, None, 0, None, "晾衣架：无"),
    "catTree":     (None, None, 0, None, "猫爬架：无"),
    "petBed":      (None, None, 0, None, "宠物窝：无"),

    # ================= 建筑 =================
    "stairU":      (None, None, 0, None, "楼梯：几何生成"),
    "stairRun":    (None, None, 0, None, "梯段：几何生成"),
    "stairLanding": (None, None, 0, None, "平台：几何生成"),
    "elevator":    (None, None, 0, None, "电梯：无"),
    "evCharger":   (None, None, 0, None, "充电桩：无"),
    "garageShelf": ("worn_metal_rack", PH, 0, 1800, "车库储物架"),
    "workbench":   ("tool_cart", PH, 0, 1600, "工具台"),
    "stage":       (None, None, 0, None, "地台：几何生成"),
    "slidingBoard": ("standing_chalkboard_01", PH, 0, 2400, "升降黑板"),
    "whiteboard":  ("standing_chalkboard_01", PH, 0, 1600, "移动白板"),
    "wifiAP":      (None, None, 0, None, "吸顶AP：几何生成"),
    "ceilingSpeaker": (None, None, 0, None, "扬声器：几何生成"),
    "supplyVent":  (None, None, 0, None, "送风口：几何生成"),
    "returnVent":  (None, None, 0, None, "回风口：几何生成"),

    # ================= 庭院 =================
    "car":         (None, None, 0, None, "轿车：无"),
    "suv":         (None, None, 0, None, "SUV：无"),
    "carport":     (None, None, 0, None, "车棚：几何生成"),
    "carport2":    (None, None,0, None, "车棚：几何生成"),
    "bicycle":     (None, None, 0, None, "自行车：无"),
    "pool":        (None, None, 0, None, "泳池：几何生成"),
    "lawn":        (None, None, 0, None, "草坪：几何生成"),
    "stepStones":  (None, None, 0, None, "汀步：几何生成"),
    "tree":        (None, None, 0, None, "乔木：几何生成"),
    "shrub":       ("shrub_01", PH, 0, 800, "灌木球"),
    "gazebo":      (None, None, 0, None, "凉亭：无"),
    "parasol":     (None, None, 0, None, "遮阳伞：无"),
    "sunLounger":  (None, None, 0, None, "躺椅：无"),
    "swing":       (None, None, 0, None, "秋千：无"),
    "bbq":         (None, None, 0, None, "烧烤台：无"),
    "waterFeature": (None, None, 0, None, "叠水景墙：无"),
    "fence":       ("modular_chainlink_fence", PH, 0, 3000, "围栏"),
    "gate":        ("large_iron_gate", PH, 0, 3000, "大门"),
    "outdoorSet":  ("outdoor_table_chair_set_01", PH, 0, 1800, "户外桌椅"),

    # ================= 软装 =================
    "rug":         (None, None, 0, None, "地毯：几何+程序化褶皱"),
    "roundRug":    (None, None, 0, None, "圆地毯：几何+褶皱"),
    "doormat":     (None, None, 0, None, "地垫：几何+褶皱"),
    "playMat":     (None, None, 0, None, "爬行垫：几何+褶皱"),
    "curtain":     (None, None, 0, None, "窗帘：几何生成"),
    "sheer":       (None, None, 0, None, "纱帘：几何生成"),
    "screenDivider": ("chinese_screen_panels", PH, 0, 1800, "屏风"),
    "plant":       ("potted_plant_01", PH, 0, 1200, "绿植"),
    "bigPlant":    ("potted_plant_02", PH, 0, 2000, "大型绿植"),
    "smallPlant":  ("potted_plant_04", PH, 0, 500, "小盆栽"),
    "hangingPlant": (None, None, 0, None, "吊兰：几何生成"),
    "floorVase":   ("ceramic_vase_01", PH, 0, 700, "落地花瓶"),
    "wallPanel":   (None, None, 0, None, "墙面造型板：几何生成"),
    "wallArt":     ("fancy_picture_frame_01", PH, 0, 900, "装饰画"),
    "wallArt3":    ("hanging_picture_frame_01", PH, 0, 1500, "装饰画三联"),
    "wallClock":   ("wall_clock", PH, 0, 400, "挂钟"),
    "screenDivider2": (None, None, 0, None, ""),
    "rug3":        (None, None, 0, None, ""),

    # ================= 自由体（25 项）=====================
    # 这些本来就是参数化几何体（立方/球/柱/旋转体/拉伸体），
    # 不是"现成资源"能覆盖的品类 —— 由 geo_gen.py 按参数生成，
    # 天然具备真实几何（可细分到任意面数），因此不属于"缺资源"。
    "freeBox":       (None, None, 0, None, "几何生成：立方体"),
    "freeRoundBox":  (None, None, 0, None, "几何生成：圆角方块"),
    "freePlatform":  (None, None, 0, None, "几何生成：地台"),
    "freeWallBlock": (None, None, 0, None, "几何生成：背景墙凸块"),
    "freeCeilBlock": (None, None, 0, None, "几何生成：吊顶造型块"),
    "freeCyl":       (None, None, 0, None, "几何生成：圆柱"),
    "freeRoundStage": (None, None, 0, None, "几何生成：圆形地台"),
    "freeHalfCyl":   (None, None, 0, None, "几何生成：半圆柱"),
    "freeTube":      (None, None, 0, None, "几何生成：圆管/圆环隔断"),
    "freeSphere":    (None, None, 0, None, "几何生成：球体"),
    "freeHemi":      (None, None, 0, None, "几何生成：半球/穹顶"),
    "freeCone":      (None, None, 0, None, "几何生成：圆锥"),
    "freePyramid":   (None, None, 0, None, "几何生成：四棱锥"),
    "freeWedge":     (None, None, 0, None, "几何生成：楔形/坡道"),
    "freeArch":      (None, None, 0, None, "几何生成：拱门"),
    "freeArcWall":   (None, None, 0, None, "几何生成：弧形墙"),
    "freeSlats":     (None, None, 0, None, "几何生成：木格栅"),
    "freeGlassScreen": (None, None, 0, None, "几何生成：长虹玻璃隔断"),
    "freeSteps":     (None, None, 0, None, "几何生成：台阶"),
    "freeTorus":     (None, None, 0, None, "几何生成：圆环/环形灯"),
    "freeLightBox":  (None, None, 0, None, "几何生成：发光灯带/灯箱"),
    "freeMirror":    (None, None, 0, None, "几何生成：镜面板"),
    "freeVase":      (None, None, 0, None, "几何生成：旋转体·花瓶"),
    "freeColumn":    (None, None, 0, None, "几何生成：旋转体·罗马柱"),
    "freeExtrude":   (None, None, 0, None, "几何生成：拉伸体（画轮廓）"),
}


def load_pick_report():
    """读取 pick_resources_v5.py 的挑选结果（现成资源路由的唯一真源）。

    【为什么以它为准】
      早期版本在 MAP 里手写资源绑定，结果出现三类问题：
        · 一品类共用一个资源 → 比例崩坏（双人床/King 床同款）
        · 资源 ID 大小写写错 → 下载 404
        · 语义错配 → 换鞋凳配了张沙发
      改由挑选器按【语义 + 比例】双重门控产出，本表只保留
      【几何生成路线】的说明与朝向微调。

    报告不存在时返回空 dict（调用方显式处理，不静默降级）。
    """
    p = os.path.join(CACHE, "pick_report.json")
    if not os.path.exists(p):
        return {}
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def main():
    cat = load_catalog()
    keys = all_keys(cat)
    print("catalog 条目总数:", len(keys))

    # ---- 现成资源：来自挑选器（语义+比例双门控）----
    report = load_pick_report()
    picked = report.get("picked", {}) if report else {}

    missing = []
    out = {}
    for key, typ, name, group in keys:
        old = MAP.get(key)
        if old:
            _, _, yaw, size, note = (list(old) + [None] * 5)[:5]
        else:
            yaw, size, note = 0, None, "未在映射表中"
            missing.append(key)

        pk = picked.get(key)
        if pk:
            rid = pk["resource"]
            src = PH
            note = "%s（形变 %.2f，匹配 %s）" % (
                note.split("（")[0] if "（" in note else note,
                pk["distort"], pk.get("keyword", ""))
            size = pk["target"][0]
        else:
            rid, src = None, None

        out[key] = {
            "key": key, "type": typ, "name": name, "group": group,
            "resource": rid, "source": src, "yaw": yaw or 0, "size_mm": size,
            "note": note,
            "route": "ph" if rid else "geo",
            "target_whd": pk["target"] if pk else None,
            "distort": pk["distort"] if pk else None,
        }

    have = sum(1 for v in out.values() if v["resource"])
    print("已绑定资源: %d / %d" % (have, len(out)))
    print("无现成资源（需几何生成或另行采购）: %d" % (len(out) - have))
    if missing:
        print("映射表未覆盖:", missing)

    os.makedirs(CACHE, exist_ok=True)
    dest = os.path.join(CACHE, "asset_map.json")
    with open(dest, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print("写入", dest)

    # 分组统计
    print()
    print("=== 分组覆盖率 ===")
    from collections import defaultdict
    g = defaultdict(lambda: [0, 0])
    for v in out.values():
        g[v["group"]][0] += 1
        if v["resource"]:
            g[v["group"]][1] += 1
    for k in sorted(g, key=lambda x: -(g[x][0] - g[x][1])):
        t, h = g[k]
        print("  %-6s %3d/%-3d  (%5.1f%%)" % (k, h, t, 100.0 * h / t))


if __name__ == "__main__":
    main()

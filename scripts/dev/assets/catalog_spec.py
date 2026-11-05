"""验收目录 158 个 type 的【权威规格表】——尺寸区间 + 语义守卫 + 风格亲和度。

【为什么必须有这张表】
用户要求：
  · "不准有任何比例崩坏" → 每个 type 必须有现实尺寸区间（W/D/H, mm）
  · "必须找与原本建模形状大小完全一致的模型" → 尺寸区间 = 与原版对齐的判据
  · "整栋房子里所有的家具之间都没有违和感，色调要相辅相成" → 风格亲和度

【尺寸数据的来源】
不是拍脑袋写的，而是取自：
  · 家具行业通用规格（办公家具/家用家具/卫浴洁具的国标与厂商产品页区间）
  · 具体品类常见成品尺寸
区间取【产品族的通用范围】，而不是单个产品的精确值 ——
  因为我们匹配的是"该品类的一个合规成品"，区间判定的是"它是不是这个品类"。

【字段】
  size  : (W_min, W_max, D_min, D_max, H_min, H_max)  单位 mm
          W=宽 X向, D=深 Y向, H=高 Z向
  terms : 检索词（给多源搜索用）
  must  : 语义必含词组（标题必须命中其一）—— 防"关键词命中 ≠ 语义正确"
  ban   : 语义禁含词 —— 防明显跑偏
  style : 风格亲和（modern / classic / industrial / outdoor）
          用于全屋统一，避免哥特+北欧+工业混搭
  tier  : 1=必须有（否则整屋有洞）/ 2=尽量有 / 3=锦上添花
"""

# =====================================================================
# 尺寸规格
# =====================================================================
# (W_min, W_max, D_min, D_max, H_min, H_max)
SPEC = {
    # ---------------- 沙发组 ----------------
    "sofa":         dict(size=(1900, 2800, 850, 1050, 700, 950),  terms=["sofa", "three seat sofa", "couch"],                    must=["sofa"], ban=["chinese", "outdoor", "sectional", "car", "carpet"], style="modern", tier=1),
    "lSofa":        dict(size=(2600, 3600, 850, 1200, 700, 950),  terms=["sectional sofa", "l shaped sofa", "corner sofa"],            must=["sofa", "sectional"], ban=["chinese", "outdoor"], style="modern", tier=1),
    "uSofa":        dict(size=(2800, 4200, 1400, 2400, 700, 950), terms=["u shaped sofa", "sectional sofa"],                        must=["sofa"], ban=["chinese"], style="modern", tier=2),
    "curvedSofa":   dict(size=(1800, 3000, 900, 1400, 700, 950),  terms=["curved sofa", "round sofa"],                              must=["sofa", "curved"], ban=["chinese"], style="modern", tier=3),
    "bendSofa":     dict(size=(1800, 3200, 850, 1200, 700, 950),  terms=["modular sofa", "modular sectional"],                         must=["sofa", "modular"], ban=["chinese"], style="modern", tier=3),
    "armchair":     dict(size=(700, 1050, 750, 1050, 700, 1100),  terms=["armchair", "accent chair"],                               must=["armchair"], ban=["chinese", "barber", "dining"], style="modern", tier=1),
    "chaise":       dict(size=(1400, 1900, 800, 1000, 650, 900),   terms=["chaise longue", "chaise lounge", "daybed"],                  must=["chaise"], ban=["chinese"], style="modern", tier=2),
    "lounge":       dict(size=(700, 1050, 700, 1000, 700, 1050),   terms=["lounge chair"],                                           must=["lounge"], ban=["chinese"], style="modern", tier=2),
    "beanbag":      dict(size=(800, 1200, 800, 1200, 500, 900),   terms=["bean bag", "beanbag chair"],                               must=["bean", "bag"], ban=["beach"], style="modern", tier=3),
    "ottoman":      dict(size=(400, 900, 350, 800, 350, 550),      terms=["ottoman", "footstool"],                                    must=["ottoman", "footstool"], ban=["chinese"], style="modern", tier=2),
    "rockingChair": dict(size=(550, 900, 800, 1100, 850, 1150),   terms=["rocking chair"],                                           must=["rocking"], ban=[], style="classic", tier=3),
    "hangingChair": dict(size=(700, 1100, 700, 1100, 1000, 1800), terms=["hanging chair", "swing chair", "hanging egg chair"],        must=["hanging", "swing", "egg"], ban=["picture", "frame"], style="modern", tier=3),
    "booth":        dict(size=(1400, 2400, 700, 1600, 1100, 1800),terms=["booth seating", "banquette", "diner booth"],                  must=["booth", "banquette"], ban=["diner", "restaurant", "car"], style="modern", tier=3),
    "theaterSofa":  dict(size=(800, 1200, 800, 1100, 900, 1300),  terms=["cinema seat", "theater seating"],                            must=["cinema", "theater"], ban=[], style="modern", tier=3),

    # ---------------- 椅凳组 ----------------
    "chair":        dict(size=(400, 560, 400, 600, 780, 1050),    terms=["dining chair", "wooden dining chair"],                       must=["chair"], ban=["office", "rocking", "barber", "school", "armchair", "folding", "stool", "gaming"], style="modern", tier=1),
    "officeChair":  dict(size=(550, 750, 500, 700, 900, 1300),    terms=["office chair", "ergonomic chair"],                           must=["chair"], ban=["rocking", "barber", "school", "dining", "folding"], style="modern", tier=2),
    "stool":        dict(size=(300, 550, 300, 550, 400, 700),    terms=["wooden stool", "round stool"],                              must=["stool"], ban=["school", "garden", "toilet", "folding", "bar"], style="modern", tier=2),
    "barStool":     dict(size=(320, 520, 320, 520, 650, 850),    terms=["bar stool", "bar chair"],                                   must=["stool", "bar"], ban=["school"], style="modern", tier=2),
    "entryBench":   dict(size=(800, 1300, 350, 500, 400, 500),   terms=["entryway bench", "shoe bench", "hall bench"],                must=["bench"], ban=["vise", "vice", "workbench", "picnic", "park"], style="modern", tier=2),

    # ---------------- 桌组 ----------------
    "coffeeTable":  dict(size=(800, 1400, 400, 900, 320, 480),   terms=["coffee table"],                                            must=["coffee", "table"], ban=["military"], style="modern", tier=1),
    "diningTable":  dict(size=(1400, 2400, 750, 1100, 700, 800), terms=["dining table"],                                            must=["dining", "table"], ban=["picnic", "conference", "meeting", "office"], style="modern", tier=1),
    "roundTable":   dict(size=(800, 1600, 800, 1600, 700, 780),  terms=["round table", "round dining table"],                        must=["round", "table"], ban=[], style="modern", tier=1),
    "ovalTable":    dict(size=(1200, 2200, 800, 1300, 700, 780), terms=["oval table", "oval dining table"],                          must=["oval", "table"], ban=[], style="modern", tier=2),
    "sideTable":    dict(size=(350, 700, 350, 700, 450, 800),    terms=["side table", "end table"],                                  must=["side", "table", "end"], ban=["desk"], style="modern", tier=1),
    "consoleTable": dict(size=(900, 1800, 300, 500, 700, 900),   terms=["console table"],                                           must=["console"], ban=[], style="modern", tier=2),
    "teaTable":     dict(size=(600, 1200, 600, 1200, 400, 700),  terms=["tea table", "low table"],                                  must=["tea", "table", "low"], ban=[], style="classic", tier=3),
    "desk":         dict(size=(1000, 1800, 550, 900, 700, 800),  terms=["writing desk", "office desk"],                              must=["desk"], ban=["lamp", "school"], style="modern", tier=1),
    "lDesk":        dict(size=(1400, 2200, 600, 900, 700, 800),  terms=["l shaped desk"],                                           must=["desk"], ban=["lamp"], style="modern", tier=2),
    "trainingTable":dict(size=(1400, 3000, 700, 1200, 700, 780), terms=["training table", "conference table"],                        must=["table"], ban=[], style="modern", tier=2),
    "curveTrainingTable": dict(size=(1800, 3200, 900, 1400, 700, 780), terms=["curved training table", "curved conference table"],   must=["table"], ban=[], style="modern", tier=3),
    "barCounter":   dict(size=(1200, 2600, 500, 800, 1000, 1150),terms=["bar counter", "bar table", "high table"],                    must=["bar", "counter", "table", "high"], ban=[], style="modern", tier=2),
    "lectern":      dict(size=(500, 900, 400, 700, 1000, 1300),  terms=["lectern", "podium"],                                        must=["lectern", "podium"], ban=[], style="classic", tier=3),
    "island":       dict(size=(1800, 3200, 900, 1400, 850, 1000),terms=["kitchen island", "island counter"],                          must=["island"], ban=[], style="modern", tier=2),
    "kitchenIsland":dict(size=(1800, 3200, 900, 1400, 850, 1000),terms=["kitchen island", "island counter"],                          must=["island", "kitchen"], ban=[], style="modern", tier=2),
    "counter":      dict(size=(600, 1800, 550, 700, 850, 950),  terms=["kitchen counter", "counter top"],                            must=["counter", "kitchen"], ban=[], style="modern", tier=1),
    "lCounter":     dict(size=(1800, 3200, 550, 700, 850, 950),  terms=["l shaped kitchen counter"],                                  must=["counter"], ban=[], style="modern", tier=3),
    "uCounter":     dict(size=(2400, 3800, 550, 700, 850, 950),  terms=["u shaped kitchen counter"],                                  must=["counter"], ban=[], style="modern", tier=3),

    # ---------------- 柜组 ----------------
    "wardrobe":     dict(size=(1000, 2400, 550, 700, 1800, 2400),terms=["wardrobe", "closet cabinet"],                              must=["wardrobe", "closet", "cabinet"], ban=["gothic"], style="modern", tier=1),
    "cabinet":      dict(size=(600, 2000, 400, 600, 800, 2400),  terms=["cabinet", "storage cabinet"],                                must=["cabinet"], ban=["gothic", "chinese", "medicine"], style="modern", tier=1),
    "chest":        dict(size=(800, 1600, 450, 600, 750, 1300),  terms=["chest of drawers", "dresser"],                                must=["chest", "drawers", "dresser"], ban=["treasure", "tool"], style="modern", tier=2),
    "dresser":      dict(size=(1000, 2000, 450, 600, 750, 1000),  terms=["dresser", "chest of drawers"],                               must=["dresser", "drawers"], ban=["treasure", "tool"], style="modern", tier=2),
    "bookshelf":    dict(size=(700, 1800, 280, 450, 1500, 2200), terms=["bookshelf", "book case"],                                     must=["book", "shelf"], ban=["worn", "gothic"], style="modern", tier=1),
    "tvCabinet":    dict(size=(1200, 2200, 350, 550, 350, 650),  terms=["tv cabinet", "media console"],                                must=["tv", "cabinet", "console", "media"], ban=["gothic"], style="modern", tier=1),
    "sideboard":    dict(size=(1200, 2200, 400, 600, 700, 1000),  terms=["sideboard", "buffet cabinet", "credenza"],                    must=["sideboard", "buffet", "credenza", "cabinet"], ban=["gothic"], style="modern", tier=2),
    "shoeCabinet":  dict(size=(600, 1400, 300, 500, 800, 2200),  terms=["shoe cabinet", "shoe rack"],                                 must=["shoe"], ban=[], style="modern", tier=2),
    "displayCabinet":dict(size=(700, 1600, 350, 550, 1500, 2200),terms=["display cabinet", "glass display case"],                      must=["display", "cabinet", "case"], ban=["gothic"], style="modern", tier=3),
    "wineCabinet":  dict(size=(500, 1200, 400, 600, 800, 2000),  terms=["wine cabinet", "wine cooler cabinet"],                        must=["wine"], ban=[], style="modern", tier=3),
    "shelfRack":    dict(size=(600, 1600, 300, 500, 1000, 2200), terms=["shelf rack", "shelving unit", "storage rack"],               must=["shelf", "rack", "shelving"], ban=["gothic"], style="modern", tier=2),
    "coatRack":     dict(size=(400, 700, 400, 700, 1600, 1900),  terms=["coat rack", "coat stand", "hat stand"],                        must=["coat", "hat"], ban=[], style="modern", tier=3),

    # ---------------- 床组 ----------------
    "bed":          dict(size=(1400, 2000, 1900, 2300, 900, 1400),terms=["bed", "double bed", "queen bed"],                            must=["bed"], ban=["bunk", "crib", "gothic", "pallet"], style="modern", tier=1),
    "roundBed":     dict(size=(1400, 2200, 1400, 2200, 500, 900),terms=["round bed"],                                                 must=["round", "bed"], ban=["bunk", "crib"], style="modern", tier=3),
    "bunkBed":      dict(size=(900, 1200, 1900, 2200, 1500, 1900),terms=["bunk bed"],                                                must=["bunk"], ban=[], style="modern", tier=3),
    "crib":         dict(size=(600, 900, 1200, 1400, 900, 1200),  terms=["baby crib", "cot bed"],                                     must=["crib", "cot"], ban=["bunk"], style="modern", tier=3),
    "tatami":       dict(size=(1500, 2200, 2000, 2200, 300, 600),terms=["low platform bed", "tatami bed"],                            must=["platform", "bed", "tatami"], ban=[], style="classic", tier=3),
    "nightstand":   dict(size=(380, 620, 350, 500, 450, 700),    terms=["nightstand", "bedside table"],                                must=["nightstand", "bedside"], ban=["gothic"], style="modern", tier=1),
    "bedBench":     dict(size=(1000, 1600, 400, 550, 400, 520),  terms=["bed bench", "end of bed bench"],                             must=["bench"], ban=["vise", "vice", "workbench", "picnic", "park"], style="modern", tier=2),
    "bayCushion":   dict(size=(800, 1600, 400, 700, 100, 250),  terms=["window seat cushion", "cushion"],                             must=["cushion", "seat"], ban=["pillow", "throw"], style="modern", tier=3),

    # ---------------- 卫浴 ----------------
    "toilet":       dict(size=(350, 500, 650, 800, 700, 850),   terms=["toilet"],                                                   must=["toilet"], ban=["paper", "sign", "portable", "public", "block", "squat"], style="modern", tier=1),
    "squat":        dict(size=(350, 500, 500, 700, 300, 450),   terms=["squat toilet"],                                              must=["squat"], ban=[], style="industrial", tier=3),
    "urinal":       dict(size=(300, 450, 250, 400, 500, 700),   terms=["urinal"],                                                    must=["urinal"], ban=[], style="industrial", tier=3),
    "vanity":       dict(size=(600, 1200, 480, 600, 800, 900),  terms=["bathroom vanity", "vanity cabinet"],                          must=["vanity"], ban=["kit"], style="modern", tier=1),
    "pedestalSink": dict(size=(400, 700, 500, 650, 750, 950),  terms=["pedestal sink", "wash basin", "washbasin"],                   must=["sink", "basin", "washbasin"], ban=["kitchen"], style="modern", tier=1),
    "bathtub":      dict(size=(1400, 1800, 700, 850, 450, 650),  terms=["bathtub"],                                                   must=["bathtub", "tub"], ban=["mat", "sign", "faucet"], style="modern", tier=1),
    "freeTub":      dict(size=(1400, 1800, 700, 850, 500, 700),  terms=["freestanding bathtub", "oval bathtub"],                        must=["bathtub", "tub"], ban=["mat", "sign"], style="modern", tier=2),
    "shower":       dict(size=(800, 1200, 800, 1200, 1900, 2200),terms=["shower cabin", "shower enclosure", "shower cubicle"],          must=["shower"], ban=["head", "curtain"], style="modern", tier=2),
    "showerScreen": dict(size=(700, 1200, 40, 120, 1800, 2100),  terms=["shower screen", "shower glass panel"],                          must=["shower"], ban=["head"], style="modern", tier=3),
    "showerSet":    dict(size=(150, 400, 100, 300, 200, 800),   terms=["shower faucet set", "shower system", "shower head"],            must=["shower"], ban=[], style="modern", tier=3),
    "mirrorCabinet":dict(size=(500, 1000, 120, 250, 700, 1200),  terms=["medicine cabinet", "mirror cabinet"],                          must=["cabinet", "mirror"], ban=[], style="modern", tier=2),
    "counter":      dict(size=(600, 1800, 550, 700, 850, 950),  terms=["bathroom counter", "vanity counter"],                          must=["counter"], ban=["kitchen"], style="modern", tier=2),
    "serviceSink":  dict(size=(500, 800, 450, 650, 500, 700),   terms=["service sink", "utility sink"],                               must=["sink"], ban=["kitchen"], style="industrial", tier=3),
    "laundrySink":  dict(size=(600, 1000, 500, 700, 800, 950),  terms=["utility sink", "laundry sink"],                               must=["sink"], ban=["kitchen"], style="industrial", tier=3),
    "towelWarmer":  dict(size=(400, 900, 100, 250, 800, 1400),  terms=["heated towel rail", "towel rail", "towel rack"],                 must=["towel"], ban=[], style="modern", tier=3),
    "bathHeater":   dict(size=(200, 500, 200, 500, 100, 300),   terms=["bathroom ceiling heater", "bathroom exhaust fan"],            must=["bathroom", "heater", "fan"], ban=["ceiling fan"], style="modern", tier=3),
    "lCounter":     dict(size=(1800, 3200, 550, 700, 850, 950),  terms=["l shaped bathroom counter"],                                  must=["counter"], ban=[], style="modern", tier=3),
    "uCounter":     dict(size=(2400, 3800, 550, 700, 850, 950),  terms=["u shaped bathroom counter"],                                  must=["counter"], ban=[], style="modern", tier=3),

    # ---------------- 厨电 ----------------
    "fridge":       dict(size=(600, 950, 600, 800, 1500, 2100), terms=["refrigerator"],                                              must=["refrigerator", "fridge"], ban=["minibar", "parts", "portable"], style="modern", tier=1),
    "freezer":      dict(size=(600, 950, 600, 800, 800, 2000),  terms=["freezer", "chest freezer"],                                    must=["freezer"], ban=["commercial", "ice"], style="modern", tier=2),
    "dishwasher":   dict(size=(450, 700, 550, 700, 800, 900),  terms=["dishwasher"],                                                must=["dishwasher"], ban=[], style="modern", tier=1),
    "microwave":    dict(size=(450, 620, 350, 450, 300, 450),  terms=["microwave oven"],                                             must=["microwave"], ban=[], style="modern", tier=2),
    "tallOven":     dict(size=(550, 700, 550, 650, 1500, 2200),terms=["built in oven", "wall oven"],                                  must=["oven"], ban=["microwave", "stove top"], style="modern", tier=2),
    "hood":         dict(size=(500, 1200, 400, 700, 500, 900),  terms=["range hood", "kitchen hood", "extractor hood"],               must=["hood", "extractor"], ban=["ventilation fan"], style="modern", tier=2),
    "coffeeMachine":dict(size=(200, 500, 300, 550, 300, 500),  terms=["espresso machine", "coffee maker"],                           must=["coffee", "espresso", "maker"], ban=["table", "cart", "grinder"], style="modern", tier=2),
    "waterDispenser":dict(size=(300, 500, 300, 500, 1000, 1400),terms=["water dispenser", "water cooler"],                            must=["water", "dispenser", "cooler"], ban=["car"], style="modern", tier=3),
    "purifier":     dict(size=(200, 400, 200, 400, 400, 800),   terms=["water purifier"],                                             must=["purifier"], ban=["air"], style="modern", tier=3),
    "washer":       dict(size=(550, 700, 550, 700, 800, 950),  terms=["washing machine"],                                            must=["washing", "washer"], ban=[], style="modern", tier=2),
    "dryer":        dict(size=(550, 700, 550, 700, 800, 950),  terms=["tumble dryer", "clothes dryer"],                               must=["dryer"], ban=[], style="modern", tier=2),
    "airPurifier":  dict(size=(300, 500, 300, 500, 400, 800),   terms=["air purifier"],                                               must=["air purifier", "purifier"], ban=["water"], style="modern", tier=2),
    "robotVac":     dict(size=(300, 400, 300, 400, 80, 120),    terms=["robot vacuum"],                                               must=["vacuum"], ban=["car", "pool", "stick"], style="modern", tier=3),
    "acWall":       dict(size=(800, 1100, 200, 350, 280, 400),  terms=["split air conditioner", "wall air conditioner"],              must=["air conditioner", "conditioner"], ban=["car", "truck"], style="modern", tier=2),
    "acFloor":      dict(size=(800, 1200, 400, 700, 1400, 2000),terms=["floor air conditioner", "floor standing air conditioner"],     must=["air conditioner", "conditioner"], ban=["car", "truck"], style="modern", tier=3),
    "gasHeater":    dict(size=(300, 600, 250, 450, 500, 900),   terms=["gas water heater"],                                           must=["gas", "heater"], ban=[], style="industrial", tier=3),
    "waterHeater":  dict(size=(400, 700, 350, 600, 900, 1800),  terms=["water heater", "water boiler"],                                must=["water", "heater"], ban=["radiator", "masonry"], style="industrial", tier=2),
    "boiler":       dict(size=(500, 800, 400, 700, 1200, 2000),  terms=["boiler"],                                                     must=["boiler"], ban=["masonry"], style="industrial", tier=3),
    "manifold":     dict(size=(200, 500, 100, 300, 300, 700),   terms=["heating manifold", "manifold"],                                must=["manifold"], ban=[], style="industrial", tier=3),
    "waterSoftener":dict(size=(300, 600, 300, 600, 1000, 1600), terms=["water softener"],                                              must=["softener"], ban=[], style="industrial", tier=3),

    # ---------------- 电器 / 娱乐 ----------------
    "wallTV":       dict(size=(900, 1700, 60, 120, 500, 1200),  terms=["wall mounted tv", "television"],                              must=["tv", "television"], ban=["cart", "stand", "remote"], style="modern", tier=1),
    "projScreen":   dict(size=(1200, 3000, 50, 150, 900, 1800), terms=["projector screen", "projection screen"],                         must=["projector", "screen"], ban=[], style="modern", tier=3),
    "speaker":      dict(size=(200, 500, 200, 500, 600, 1200),  terms=["floor standing speaker", "loudspeaker"],                         must=["speaker"], ban=["car", "carpet", "headphone"], style="modern", tier=2),
    "fireplace":    dict(size=(800, 1500, 400, 700, 900, 1400), terms=["electric fireplace", "fireplace"],                              must=["fireplace"], ban=["hearth", "tool", "log"], style="modern", tier=3),
    "piano":        dict(size=(1400, 1600, 600, 700, 1000, 1300),terms=["upright piano"],                                              must=["piano"], ban=["grand"], style="classic", tier=3),
    "grandPiano":   dict(size=(1400, 1600, 2000, 2600, 950, 1100),terms=["grand piano"],                                             must=["grand", "piano"], ban=[], style="classic", tier=3),
    "billiards":    dict(size=(1800, 2800, 1000, 1300, 750, 900),terms=["pool table", "billiard table"],                                 must=["pool", "billiard", "snooker"], ban=[], style="classic", tier=3),
    "mahjong":      dict(size=(800, 1200, 800, 1200, 700, 800),  terms=["mahjong table"],                                              must=["mahjong"], ban=[], style="classic", tier=3),
    "treadmill":    dict(size=(700, 1000, 1500, 2000, 1300, 1600),terms=["treadmill"],                                                  must=["treadmill"], ban=[], style="modern", tier=3),
    "bike":         dict(size=(500, 800, 1000, 1400, 1000, 1400),terms=["exercise bike", "stationary bike"],                            must=["exercise", "stationary", "spin"], ban=["bicycle", "motorcycle"], style="modern", tier=3),
    "yogaMat":      dict(size=(600, 900, 1700, 2000, 5, 20),    terms=["yoga mat"],                                                   must=["yoga", "mat"], ban=["mouse", "bath"], style="modern", tier=3),
    "fishTank":     dict(size=(600, 1500, 300, 600, 400, 900),  terms=["aquarium", "fish tank"],                                       must=["aquarium", "fish", "tank"], ban=["goldfish", "bowl"], style="modern", tier=3),
    "sauna":        dict(size=(1200, 2200, 1200, 2200, 2000, 2400),terms=["sauna"],                                                     must=["sauna"], ban=[], style="classic", tier=3),

    # ---------------- 灯具 ----------------
    "floorLamp":    dict(size=(300, 700, 300, 700, 1400, 1900), terms=["floor lamp"],                                                 must=["floor", "lamp"], ban=["ceiling", "table", "desk"], style="modern", tier=1),
    "deskLamp":     dict(size=(300, 600, 200, 500, 400, 900),  terms=["desk lamp"],                                                  must=["desk", "lamp"], ban=["floor"], style="modern", tier=2),
    "chandelier":   dict(size=(600, 1400, 600, 1400, 600, 1400),terms=["chandelier", "pendant light"],                                 must=["chandelier", "pendant"], ban=[], style="modern", tier=2),
    "lawnLamp":     dict(size=(300, 700, 300, 700, 2500, 4000),terms=["garden lamp post", "outdoor lamp post"],                        must=["lamp"], ban=["street", "ceiling"], style="outdoor", tier=3),

    # ---------------- 软装 ----------------
    "rug":          dict(size=(1600, 3500, 1000, 3000, 5, 40),  terms=["area rug", "wool rug", "carpet"],                              must=["rug", "carpet"], ban=["military", "vehicle", "doormat", "bath"], style="modern", tier=1),
    "rugRound":     dict(size=(1200, 2500, 1200, 2500, 5, 40),  terms=["round rug", "round carpet"],                                   must=["round"], ban=[], style="modern", tier=2),
    "curtain":      dict(size=(800, 3000, 100, 400, 1800, 2800),terms=["window curtains", "curtain"],                                   must=["curtain"], ban=["castle", "medieval", "stage", "camp", "japanese", "shower"], style="modern", tier=1),
    "screenDivider":dict(size=(800, 2000, 60, 200, 1500, 2200),terms=["room divider", "folding screen"],                               must=["divider", "screen"], ban=["projection", "shower"], style="modern", tier=3),
    "plant":        dict(size=(300, 1200, 300, 1200, 500, 2000),terms=["potted plant", "houseplant"],                                  must=["plant"], ban=["tree", "forest", "bush", "flower", "field", "hedge", "grass"], style="modern", tier=1),
    "hangingPlant": dict(size=(200, 700, 200, 700, 300, 900),  terms=["hanging plant", "hanging planter"],                             must=["plant"], ban=["picture", "frame", "art", "light"], style="modern", tier=2),
    "wallArt":      dict(size=(400, 1500, 30, 120, 400, 1200),  terms=["picture frame", "wall art", "painting"],                          must=["art", "picture", "frame", "painting"], ban=["dart", "target", "board"], style="modern", tier=1),
    "wallPanel":    dict(size=(600, 2400, 30, 150, 1500, 2600),terms=["wall panel", "wood slat panel"],                                 must=["panel", "slat"], ban=[], style="modern", tier=3),
    "vase":         dict(size=(200, 500, 200, 500, 400, 1200),  terms=["floor vase", "tall vase", "decorative vase"],                    must=["vase"], ban=["antique"], style="modern", tier=2),
    "mirror":       dict(size=(400, 1200, 30, 150, 700, 2000),  terms=["wall mirror", "mirror"],                                       must=["mirror"], ban=["ornate", "makeup", "car"], style="modern", tier=1),
    "clock":        dict(size=(200, 600, 40, 200, 200, 600),   terms=["wall clock"],                                                  must=["clock"], ban=["telephone", "grandfather", "mantel", "alarm", "digital"], style="modern", tier=2),

    # ---------------- 其他 ----------------
    "fan":          dict(size=(300, 600, 300, 600, 1000, 1600),terms=["standing fan", "floor fan"],                                    must=["fan"], ban=["ceiling", "exhaust", "ventilation", "hand"], style="modern", tier=2),
    "radiator":     dict(size=(600, 1800, 80, 200, 400, 900),  terms=["radiator"],                                                    must=["radiator"], ban=["car", "engine", "coolant"], style="modern", tier=2),
    "bin":          dict(size=(250, 500, 250, 500, 400, 900),  terms=["trash can", "waste bin", "garbage bin"],                          must=["bin", "trash", "waste"], ban=["tool", "composter", "laptop"], style="modern", tier=2),
    "clothesRack":  dict(size=(800, 1600, 400, 700, 800, 1800),terms=["clothes drying rack", "clothes rack"],                           must=["clothes", "rack"], ban=["shoe", "bike"], style="modern", tier=3),
    "catTree":      dict(size=(500, 1200, 500, 1200, 800, 2000),terms=["cat tree", "cat tower"],                                         must=["cat"], ban=["concrete", "statue", "dog"], style="modern", tier=3),
    "petBed":       dict(size=(400, 900, 400, 900, 150, 400),  terms=["pet bed", "dog bed", "cat bed"],                                 must=["pet", "dog", "bed"], ban=["bunk", "crib"], style="modern", tier=3),

    # ---------------- 办公 ----------------
    "mobileDisplay":dict(size=(1000, 2000, 80, 200, 1200, 2000),terms=["display screen", "presentation display", "led display"],         must=["display", "screen", "panel"], ban=[], style="modern", tier=3),
    "printer":      dict(size=(400, 800, 350, 600, 200, 600),  terms=["office printer", "printer"],                                    must=["printer"], ban=["3d printing"], style="modern", tier=3),

    # ---------------- 庭院 ----------------
    "tree":         dict(size=(1500, 8000, 1500, 8000, 2500, 12000),terms=["tree"],                                                    must=["tree"], ban=["dead", "stump", "log", "forest", "christmas"], style="outdoor", tier=1),
    "shrub":        dict(size=(400, 2000, 400, 2000, 300, 1500),terms=["shrub", "bush"],                                                must=["shrub", "bush"], ban=["hedge"], style="outdoor", tier=2),
    "lawn":         dict(size=(2000, 12000, 2000, 12000, 20, 120),terms=["grass ground", "lawn"],                                        must=["grass", "lawn"], ban=["mower"], style="outdoor", tier=2),
    "fence":        dict(size=(2000, 8000, 100, 400, 1000, 2500),terms=["fence"],                                                       must=["fence"], ban=["chainlink"], style="outdoor", tier=2),
    "gate":         dict(size=(1200, 4000, 100, 400, 1500, 3000),terms=["garden gate", "gate"],                                         must=["gate"], ban=["latch", "airlock", "portal"], style="outdoor", tier=3),
    "carport":      dict(size=(2400, 6000, 2400, 6000, 2000, 3000),terms=["carport", "car shelter", "car garage"],                         must=["carport", "shelter"], ban=[], style="outdoor", tier=3),
    "car":          dict(size=(4000, 5200, 1700, 2000, 1400, 1800),terms=["car", "sedan"],                                               must=["car"], ban=["cart", "coffee", "menu", "toy", "slot", "shopping", "tram"], style="outdoor", tier=3),
    "bicycle":      dict(size=(1600, 1900, 400, 600, 1000, 1200),terms=["bicycle"],                                                     must=["bicycle"], ban=["exercise", "stationary", "motor", "spin"], style="outdoor", tier=3),
    "pool":         dict(size=(3000, 12000, 2000, 8000, 1000, 1800),terms=["swimming pool"],                                             must=["pool", "swimming"], ban=["ball", "game", "puzzle", "billiard", "table"], style="outdoor", tier=3),
    "gazebo":       dict(size=(2000, 5000, 2000, 5000, 2000, 3200),terms=["gazebo", "pavilion"],                                         must=["gazebo", "pavilion"], ban=[], style="outdoor", tier=3),
    "parasol":      dict(size=(1500, 3000, 1500, 3000, 1800, 2600),terms=["parasol", "garden umbrella"],                                must=["parasol", "umbrella"], ban=["beach"], style="outdoor", tier=3),
    "sunLounger":   dict(size=(600, 900, 1500, 2000, 600, 1000),terms=["sun lounger", "deck chair"],                                     must=["lounger", "deck"], ban=[], style="outdoor", tier=3),
    "swing":        dict(size=(800, 1800, 800, 1200, 1500, 2200),terms=["garden swing", "swing"],                                       must=["swing"], ban=["child swing"], style="outdoor", tier=3),
    "bbq":          dict(size=(800, 1600, 500, 1200, 900, 1400),terms=["barbecue grill", "bbq grill"],                                 must=["barbecue", "bbq", "grill"], ban=["gas", "salad"], style="outdoor", tier=3),
    "waterFeature": dict(size=(800, 3000, 400, 2000, 500, 2500),terms=["waterfall", "water feature", "fountain"],                      must=["waterfall", "water", "fountain"], ban=[], style="outdoor", tier=3),
    "stepStones":   dict(size=(300, 900, 300, 900, 40, 200),  terms=["stepping stone", "stepping stones"],                           must=["stepping", "stone"], ban=[], style="outdoor", tier=3),
    "outdoorSet":   dict(size=(1400, 2600, 1400, 2600, 700, 900),terms=["outdoor patio furniture set", "garden furniture set"],         must=["outdoor", "patio", "garden", "terrace"], ban=[], style="outdoor", tier=3),

    # ---------------- 建筑 ----------------
    "airVent":      dict(size=(150, 700, 100, 300, 150, 700),  terms=["air vent", "vent grille", "air vent grille"],                     must=["vent", "grille"], ban=["duct", "hose"], style="modern", tier=2),
    "ceilingSpeaker":dict(size=(150, 350, 150, 350, 50, 150),  terms=["ceiling speaker"],                                             must=["ceiling", "speaker"], ban=[], style="modern", tier=3),
    "wifiAP":       dict(size=(100, 400, 100, 400, 30, 200),   terms=["wifi router", "wifi access point", "ceiling access point"],     must=["router", "wifi", "access", "point"], ban=[], style="modern", tier=3),
    "elevator":     dict(size=(1000, 1600, 1000, 1600, 2200, 2600),terms=["elevator", "lift"],                                         must=["elevator", "lift"], ban=[], style="modern", tier=3),
    "evCharger":    dict(size=(300, 800, 200, 500, 1200, 1600),terms=["ev charger", "charging station"],                              must=["charger", "charging"], ban=[], style="modern", tier=3),
    "garageShelf":  dict(size=(900, 2400, 400, 700, 1500, 2200),terms=["garage shelving", "garage storage shelf"],                     must=["garage", "shelv"], ban=[], style="industrial", tier=3),
    "workbench":    dict(size=(1200, 2200, 600, 900, 850, 1000),terms=["workbench"],                                                   must=["workbench", "work", "bench"], ban=["vise", "vice"], style="industrial", tier=3),
    "stage":        dict(size=(2000, 6000, 1000, 4000, 300, 800),terms=["stage platform", "stage"],                                      must=["stage", "platform"], ban=["theater"], style="modern", tier=3),
    "slidingBoard": dict(size=(1200, 3000, 50, 200, 900, 1500),terms=["whiteboard", "sliding whiteboard"],                             must=["whiteboard"], ban=[], style="modern", tier=3),
    "stairRun":     dict(size=(900, 4000, 1000, 5000, 2500, 4000),terms=["staircase", "stairs"],                                        must=["stair"], ban=[], style="modern", tier=2),
    "stairU":       dict(size=(2000, 4000, 2000, 4000, 2500, 4000),terms=["u shaped staircase"],                                         must=["stair"], ban=[], style="modern", tier=3),

    # ---------------- 植物架 ----------------
    "plantShelf":   dict(size=(400, 1200, 300, 600, 400, 1800),terms=["plant stand", "plant shelf", "planter stand"],                      must=["plant", "stand", "shelf"], ban=[], style="modern", tier=2),

    # ---------------- 自由体（设计器里的基础几何体，非实景资源） ----------------
    # 【说明】"free" 是 25 款程序化基础体（盒/圆柱/球/拱/台阶…），
    # 它们是设计器的图元，本来就是代码生成的，不需要外部模型资源。
    # 但用户要求"验收界面里所有的物品全部替换不能有疏漏"，
    # 所以这里也给它一份可下载的【实景替代】（真实世界里的木箱/花盆/灯箱等），
    # 做到清单上不出现"空洞"。
    "free":         dict(size=(200, 1200, 200, 1200, 200, 1200),terms=["wooden crate", "planter box", "light box", "decorative box"],     must=["crate", "box", "planter", "lamp"], ban=[], style="modern", tier=3),
}

# ---------------------------------------------------------------------
# 修正一处手误：towelWarmer 的 terms 单独写清楚
# ---------------------------------------------------------------------
SPEC["towelWarmer"] = dict(
    size=(400, 900, 100, 250, 800, 1400),
    terms=["heated towel rail", "towel rail", "towel rack"],
    must=["towel"],
    ban=[],
    style="modern",
    tier=3,
)

# =====================================================================
# 全屋统一调色板（材质角色）
# =====================================================================
ROLE_COLORS = {
    "wood_dark":   "#6B4A2D",   # 胡桃木
    "wood_light":  "#B08D5F",   # 白橡
    "fabric_main": "#C9BBA6",   # 燕麦米（主织物）
    "fabric_dark": "#9D8F7A",   # 深燕麦
    "fabric_cream": "#E4DCCB",  # 米白
    "metal_black": "#22252A",   # 哑光黑
    "metal_alu":   "#C9CCD0",   # 铝
    "accent_terra": "#B5643C",  # 陶土橙
    "accent_sage": "#7C8B72",   # 灰绿
    "stone_light": "#CFC8BC",
    "glass":       "#C8D4D8",
    "plastic_white": "#E8E6E1",
    "dark_grey":   "#3A3E44",
}

# 材质名 → 角色判定
MAT_RULES = [
    (["wood", "timber", "oak", "walnut", "birch", "teak", "pine", "plywood",
      "mahogany", "veneer", "bamboo", "plank"], "wood_dark"),
    (["fabric", "cloth", "cushion", "upholstery", "seat", "sofa", "pillow",
      "linen", "velvet", "textile", "leather", "mattress", "blanket",
      "quilt", "towel", "curtain", "carpet", "rug"], "fabric_main"),
    (["metal", "steel", "iron", "aluminium", "aluminum", "chrome", "brass",
      "copper", "bronze", "chrome"], "metal_alu"),
    (["glass", "mirror", "crystal"], "glass"),
    (["stone", "marble", "concrete", "ceramic", "porcelain", "terracotta",
      "granite", "tile"], "stone_light"),
    (["plastic", "acrylic", "vinyl"], "plastic_white"),
    (["paper", "cardboard"], "fabric_cream"),
]


def guess_role(mat_name):
    n = (mat_name or "").lower()
    for keys, role in MAT_RULES:
        for k in keys:
            if k in n:
                return role
    return "dark_grey"


# =====================================================================
# 风格关键词（用于全屋风格统一打分）
# =====================================================================
STYLE_TAGS = {
    "modern": ["modern", "contemporary", "minimal", "scandinavian", "nordic",
               "office", "school", "metal_office", "bar_chair", "side_table",
               "coffee_table_round", "round_wooden", "mid_century",
               "industrial_coffee", "painted_wooden"],
    "classic": ["gothic", "victorian", "classic", "ornate", "antique",
                "barber", "chinese", "rocking", "vintage", "mantel",
                "grandfather", "medieval", "renaissance", "cedar"],
    "industrial": ["industrial", "tool", "metal_tool", "worn", "rusty",
                   "ammo", "welding", "workshop", "warehouse", "workbench"],
    "outdoor": ["outdoor", "garden", "patio", "terrace", "plant", "tree",
                "grass", "bush", "shrub", "fence", "bbq", "grill", "deck"],
}


def style_tags(slug):
    s = (slug or "").lower()
    tags = set()
    for t, kws in STYLE_TAGS.items():
        for k in kws:
            if k in s:
                tags.add(t)
    return tags

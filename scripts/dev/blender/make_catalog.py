"""生成验收站完整目录：251 款家具全部列出，标注每款的建模状态与所属组。

数据来源：
  · 目录与中文名：从 assets/template.html 的家具调色板正则挖出（真实存在的款式）
  · 状态与体检数据：从 assets/furnlib/manifest.json（真实 GLB 解析）
  · 配色：统一色板 palette.py，保证配套不违和
"""
import json, os, re, sys, pathlib
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = pathlib.Path(HERE).parent.parent.parent      # scripts/dev/blender → 项目根
ACC = ROOT / "验收"
MODELS = ACC / "models"

# ---------- 1. 从模板挖调色板（真实款式清单） ----------
t = (ROOT / "assets" / "template.html").read_text(encoding="utf-8")
palette_items = re.findall(r'\{key:"([^"]+)",type:"([^"]+)",name:"([^"]+)"', t)

# type → 中文组名
GROUP_CN = {
    "sofa": "沙发组", "lSofa": "沙发组", "uSofa": "沙发组", "curvedSofa": "沙发组",
    "bendSofa": "沙发组", "armchair": "沙发组", "chaise": "沙发组", "lounge": "沙发组",
    "beanbag": "沙发组", "ottoman": "沙发组", "rockingChair": "沙发组",
    "hangingChair": "沙发组", "theaterSofa": "沙发组", "booth": "沙发组",
    "bed": "床组", "roundBed": "床组", "bunkBed": "床组", "crib": "床组",
    "tatami": "床组", "bedBench": "床组", "nightstand": "床组", "bayCushion": "床组",
    "diningTable": "桌组", "roundTable": "桌组", "ovalTable": "桌组",
    "coffeeTable": "桌组", "desk": "桌组", "lDesk": "桌组", "trainingTable": "桌组",
    "curveTrainingTable": "桌组", "sideTable": "桌组", "consoleTable": "桌组",
    "mahjong": "桌组", "billiards": "桌组", "teaTable": "桌组", "lectern": "桌组",
    "barCounter": "桌组", "kitchenIsland": "桌组", "island": "桌组",
    "chair": "椅凳组", "officeChair": "椅凳组", "barStool": "椅凳组", "stool": "椅凳组",
    "entryBench": "椅凳组",
    "wardrobe": "柜组", "cabinet": "柜组", "chest": "柜组", "bookshelf": "柜组",
    "tvCabinet": "柜组", "sideboard": "柜组", "wineCabinet": "柜组",
    "displayCabinet": "柜组", "shoeCabinet": "柜组", "shelfRack": "柜组",
    "dresser": "柜组", "coatRack": "柜组", "planterShelf": "柜组", "plantShelf": "柜组",
    "free": "自由体", "rug": "软装", "rugRound": "软装", "curtain": "软装",
    "wallArt": "软装", "plant": "软装", "hangingPlant": "软装", "vase": "软装",
    "clock": "软装", "wallPanel": "软装", "screenDivider": "软装",
    "floorLamp": "灯具", "deskLamp": "灯具", "chandelier": "灯具", "lawnLamp": "灯具",
    "fireplace": "电器", "wallTV": "电器", "projScreen": "电器", "speaker": "电器",
    "fridge": "厨电", "freezer": "厨电", "dishwasher": "厨电", "microwave": "厨电",
    "tallOven": "厨电", "hood": "厨电", "coffeeMachine": "厨电", "waterDispenser": "厨电",
    "purifier": "厨电", "washer": "厨电", "dryer": "厨电", "airPurifier": "厨电",
    "robotVac": "厨电", "acWall": "厨电", "acFloor": "厨电", "gasHeater": "厨电",
    "waterHeater": "厨电", "boiler": "厨电", "manifold": "厨电", "waterSoftener": "厨电",
    "piano": "娱乐", "grandPiano": "娱乐", "billiards": "娱乐", "mahjong": "娱乐",
    "treadmill": "娱乐", "bike": "娱乐", "yogaMat": "娱乐", "sauna": "娱乐",
    "fishTank": "娱乐", "outdoorSet": "庭院", "parasol": "庭院", "sunLounger": "庭院",
    "swing": "庭院", "bbq": "庭院", "waterFeature": "庭院", "fence": "庭院",
    "gate": "庭院", "gazebo": "庭院", "tree": "庭院", "shrub": "庭院",
    "lawn": "庭院", "pool": "庭院", "stepStones": "庭院", "carport": "庭院",
    "car": "庭院", "bicycle": "庭院",
    "toilet": "卫浴", "squat": "卫浴", "urinal": "卫浴", "vanity": "卫浴",
    "bathtub": "卫浴", "freeTub": "卫浴", "shower": "卫浴", "showerScreen": "卫浴",
    "showerSet": "卫浴", "mirrorCabinet": "卫浴", "pedestalSink": "卫浴",
    "laundrySink": "卫浴", "serviceSink": "卫浴", "towelWarmer": "卫浴",
    "bathHeater": "卫浴", "counter": "卫浴", "lCounter": "卫浴", "uCounter": "卫浴",
    "stairRun": "建筑", "stairU": "建筑", "elevator": "建筑", "slidingBoard": "建筑",
    "airVent": "建筑", "wifiAP": "建筑", "ceilingSpeaker": "建筑", "evCharger": "建筑",
    "garageShelf": "建筑", "workbench": "建筑", "stage": "建筑",
    "mobileDisplay": "办公", "printer": "办公", "loft": "办公", "tent": "户外",
}

# ---------- 2. 读已有建模状态 ----------
built = {}
mf = MODELS / "manifest.json"
if mf.exists():
    man = json.load(open(mf, encoding="utf-8"))
    for it in man.get("items", []):
        built[it["key"]] = it

# 【关键】manifest 里每件模型带一个显式的 cat 字段，
# 指明它绑定到目录中的【哪一个具体款式条目】。
# 不能用「按 type 兜底匹配」—— 那会把 1 件模型广播到该 type 的所有款式上
# （实测 bug：8 件模型被标成 26 款达标，"双人沙发"显示三人沙发的 2240mm）。
# 绑定关系由 make_manifest.py 的 SPEC[].cat 唯一定义，此处只做单向读取。
CAT_TO_BUILT = {}
for mkey, b in built.items():
    cat = b.get("cat")
    if cat:
        if cat in CAT_TO_BUILT:
            raise RuntimeError(
                "目录条目 %r 被多个模型绑定：%r / %r（绑定必须唯一）"
                % (cat, CAT_TO_BUILT[cat]["key"], mkey))
        CAT_TO_BUILT[cat] = b

# ---------- 3. 组装目录 ----------
groups = defaultdict(list)
seen = set()
for key, typ, name in palette_items:
    if key in seen:
        continue
    seen.add(key)
    g = GROUP_CN.get(typ, "其他")
    # 只认【显式 cat 绑定】的那一款；同 type 的其它款式保持"待建模"
    b = CAT_TO_BUILT.get(key)
    groups[g].append({
        "key": key,
        "type": typ,
        "name": name,
        "group": g,
        "file": (b or {}).get("file"),
        "status": (b or {}).get("status", "none"),
        "tris": (b or {}).get("tris", 0),
        "checks": (b or {}).get("checks", []),
        "ref": (b or {}).get("ref"),
        "refTitle": (b or {}).get("refTitle"),
        "refNote": (b or {}).get("refNote", ""),
    })

out = {
    "generated": __import__("datetime").datetime.now().isoformat(timespec="seconds"),
    "total": sum(len(v) for v in groups.values()),
    "groups": [{"name": g, "items": items} for g, items in sorted(groups.items())],
}
with open(MODELS / "catalog.json", "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=1)

print(f"catalog -> {MODELS / 'catalog.json'}")
print(f"total items = {out['total']}  groups = {len(out['groups'])}")
for g in out["groups"]:
    n = sum(1 for i in g["items"] if i["status"] == "ok")
    w = sum(1 for i in g["items"] if i["status"] == "warn")
    print(f"  {g['name']:<10} {len(g['items']):>3} 款  ok={n} warn={w}")
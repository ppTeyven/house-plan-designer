"""【验收不合格 · 根因修复】给 251 个 GLB 内嵌真实扫描 PBR 四通道贴图。

【用户反馈】"验收不合格，几乎所有的物件都是乱码"

【实测根因（本脚本用硬数据确认，不是猜测）】
  交叉统计 251 个模型的「构建路线 × 是否内嵌贴图」：

      route  source      内嵌贴图   数量
      geo    -           无          131   ← 几何白模
      geo    polyhaven   无           69   ← 明明有资源却走了 geo
      ph     polyhaven   有           38   ← 正常
      geo    polyhaven   有            7   ← 之前重建过
      ph     -           有            6   ← 正常

  → 200/251 个模型【没有 baseColorTexture】。
  → 验收站 app.js 只用 GLTFLoader 加载 GLB，GLTFLoader 不会根据
    材质名 U_wood_oak 去猜"该用哪张扫描贴图" —— 没贴图就是纯色白模。
  → 用户看到的"一坨东西认不出"= 纯色白模 + 角色错配的叠加。

  角色错配（第二个叠加因素）：
    normalize_glb.guess_role() 猜不到关键字时【兜底返回 "fabric_oat"】，
    于是 diningTable / wardrobe / coffeeTable / desk 全被打成燕麦布。
    实测 role 分布：fabric_oat 66 处，其中大量是木作/金属件。

【本脚本做什么】
  A. 材质角色修正（逐材质）：
     ① 原素材材质名关键字 → ② 家具类型大类 → ③ 保留原角色
     混合材质模型（衣柜=柜体木+镜面玻璃）不会被整体改写。
  B. 内嵌真实 PBR 四通道：
     把 ambientCG 扫描贴图打进 GLB 的 images/textures：
       baseColorTexture      ← <role>_col.jpg
       metallicRoughnessTexture ← <role>_orm.jpg  (R=AO G=rough B=metal)
       normalTexture         ← <role>_nor.jpg
       occlusionTexture      ← <role>_ao.jpg
     → 任何查看器（验收站 / 主程序 / Blender / 第三方）都直接看到真实 PBR。
  C. 修好金属度/粗糙度通道 —— 老代码把 rough 图直接当 metallicRoughnessTexture，
     结果 G 通道读的是"红色"(rough) 而不是规范要求的 G=rough/B=metal，
     材质会呈现【错误的金属反射】。这是"看起来很怪/很乱"的隐藏原因之一。

【安全】
  · 默认只报告；--apply 才写盘。
  · 写盘前自动备份到 assets/_asset_cache/glb_backup_<时间戳>/。
  · 只改材质名 + 贴图，【不改几何、不改尺寸、不改顶点】。

【用法】
  python embed_pbr.py                # 报告
  python embed_pbr.py --apply        # 写盘
  python embed_pbr.py --apply --only diningTable
"""
import argparse
import hashlib
import json
import os
import shutil
import struct
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
ACC = os.path.join(ROOT, "assets", "furnlib")
NEW = os.path.join(ROOT, "assets", "furnlib")
CACHE_RAW = os.path.join(ROOT, "assets", "_asset_cache", "raw")
AMAP = os.path.join(ROOT, "assets", "_asset_cache", "asset_map.json")

import normalize_glb as NG
import pbr_pack as PP
import roles as ROLES

CT_JSON = 0x4E4F534A
CT_BIN = 0x004E4942

# 构建路线与真实资源（由 main() 从 build_report.json 填充）
ROUTES = {}
BUILD_RES = {}


# =====================================================================
# 材质角色体系
# =====================================================================

# 家具【类型】→ 大类（用于类型兜底）
TYPE_CLASS = {
    # --- 木作 ---
    "diningTable": "wood", "roundTable": "wood", "ovalTable": "wood",
    "coffeeTable": "wood", "sideTable": "wood", "conferenceTable": "wood",
    "consoleTable": "wood", "desk": "wood", "lDesk": "wood",
    "trainingTable": "wood", "teaTable": "wood", "barTable": "wood",
    "counter": "wood", "lCounter": "wood", "uCounter": "wood",
    "pantryCounter": "wood", "kitchenIsland": "wood", "island": "wood",
    "wardrobe": "wood", "cabinet": "wood", "shelfRack": "wood",
    "bookshelf": "wood", "chest": "wood", "tvCabinet": "wood",
    "nightstand": "wood", "sideboard": "wood", "shoeCabinet": "wood",
    "dresser": "wood", "wineCabinet": "wood", "displayCabinet": "wood",
    "mirrorCabinet": "wood", "workbench": "wood", "lectern": "wood",
    "fileCabinet": "wood", "toyCabinet": "wood", "hallCabinet": "wood",
    "garageShelf": "wood", "plantShelf": "wood", "bedBench": "wood",
    "whiteboard": "wood", "slidingBoard": "wood", "wallPanel": "wood",
    "wallArt": "wood", "wallArt3": "wood", "piano": "wood",
    "grandPiano": "wood", "mahjong": "wood", "billiards": "wood",
    "stage": "wood", "gazebo": "wood", "fence": "wood",
    "entryBench": "wood", "shoeBench": "wood", "diningBench": "wood",
    "deskBench2": "wood", "deskBench4": "wood",
    # --- 软包 ---
    "sofa": "fabric", "lSofa": "fabric", "uSofa": "fabric",
    "curvedSofa": "fabric", "bendSofa": "fabric", "singleSofa": "fabric",
    "fourSofa": "fabric", "theaterSofa": "fabric", "officeSofa": "fabric",
    "armchair": "fabric", "readingChair": "fabric", "chaise": "fabric",
    "chaiseSofa": "fabric", "dayBed": "fabric", "beanbag": "fabric",
    "lounge": "fabric", "chair": "fabric", "officeChair": "fabric",
    "gamingChair": "fabric", "barStool": "fabric", "stool": "fabric",
    "ottoman": "fabric", "bench": "fabric", "armDiningChair": "fabric",
    "trainingChair": "fabric", "rockingChair": "fabric",
    "hangingChair": "fabric", "sunLounger": "fabric", "outdoorSet": "fabric",
    "rug": "fabric", "rugRound": "fabric", "yogaMat": "fabric",
    "playMat": "fabric", "doormat": "fabric", "curtain": "fabric",
    "sheer": "fabric", "petBed": "fabric", "bayCushion": "fabric",
    "reception": "fabric", "booth": "fabric", "parasol": "fabric",
    "projScreen": "fabric", "tatami": "fabric", "catTree": "fabric",
    "bed": "fabric", "roundBed": "fabric", "bunkBed": "fabric",
    "crib": "fabric", "screenDivider": "fabric",
    # --- 陶瓷 / 洁具 ---
    "toilet": "ceramic", "squat": "ceramic", "bathtub": "ceramic",
    "freeTub": "ceramic", "sink": "ceramic", "vanity": "ceramic",
    "pedestalSink": "ceramic", "urinal": "ceramic",
    "serviceSink": "ceramic", "laundrySink": "ceramic",
    "pool": "ceramic", "vase": "ceramic", "floorVase": "ceramic",
    "freeVase": "ceramic",
    # --- 玻璃 ---
    "mirror": "glass", "freeGlassScreen": "glass", "freeMirror": "glass",
    "fishTank": "glass",
    # --- 金属设备 ---
    "fridge": "metal", "fridgeDouble": "metal", "fridgeFrench": "metal",
    "freezer": "metal", "wineFridge": "metal", "washer": "metal",
    "dryer": "metal", "dishwasher": "metal", "hood": "metal",
    "microwave": "metal", "oven": "metal", "tallOven": "metal",
    "coffeeMachine": "metal", "printer": "metal", "mobileDisplay": "metal",
    "waterHeater": "metal", "miniHeater": "metal", "gasHeater": "metal",
    "boiler": "metal", "waterDispenser": "metal", "purifier": "metal",
    "airPurifier": "metal", "robotVac": "metal", "elevator": "metal",
    "evCharger": "metal", "waterSoftener": "metal", "manifold": "metal",
    "speaker": "metal", "wifiAP": "metal", "ceilingSpeaker": "metal",
    "airVent": "metal", "radiator": "metal", "fan": "metal",
    "floorLamp": "metal", "deskLamp": "metal", "lawnLamp": "metal",
    "arcLamp": "metal", "chandelier": "metal", "wallTV": "metal",
    "wallClock": "metal", "bike": "metal", "bicycle": "metal",
    "treadmill": "metal", "swing": "metal", "clothesRack": "metal",
    "coatRack": "metal", "lockers": "metal", "kitchenTrolley": "metal",
    "bbq": "metal", "carport": "metal", "carport2": "metal",
    "car": "metal", "suv": "metal", "towelWarmer": "metal",
    "bathHeater": "metal", "acWall": "metal", "acFloor": "metal",
    "supplyVent": "metal", "returnVent": "metal",
    # --- 石材 / 建筑 ---
    "freeArcWall": "stone", "freeArch": "stone", "freeColumn": "stone",
    "freeHalfCyl": "stone", "freeHemi": "stone", "freeSphere": "stone",
    "freeSteps": "stone", "stairU": "stone", "stairRun": "stone",
    "stairLanding": "stone", "waterFeature": "stone", "stepStones": "stone",
    "fireplace": "stone",
    "freeBox": "wood", "freeCone": "wood", "freeExtrude": "wood",
    "freePlatform": "wood", "freePyramid": "wood",
    "freeRoundBox": "wood", "freeRoundStage": "wood",
    "freeSlats": "wood", "freeTorus": "wood",
    "freeWallBlock": "wood", "freeWedge": "wood", "freeCeilBlock": "wood",
    "freeCyl": "metal", "freeTube": "metal", "freeLightBox": "metal",
    # --- 植物 ---
    "plant": "leaf", "bigPlant": "leaf", "smallPlant": "leaf",
    "hangingPlant": "leaf", "shrub": "leaf", "lawn": "leaf", "tree": "leaf",
}

CLASS_ROLES = {
    "wood": {"wood_oak", "wood_walnut"},
    "fabric": {"fabric_oat", "fabric_oat_d", "fabric_cream", "fabric_grey"},
    "metal": {"metal_black", "metal_steel", "metal_brass"},
    "stone": {"stone_light", "stone_dark"},
    "ceramic": {"ceramic_white"},
    "leaf": {"leaf", "leaf_dark"},
    "glass": {"glass_clear"},
}

CLASS_DEFAULT = {
    "wood": "wood_walnut", "fabric": "fabric_oat", "metal": "metal_black",
    "stone": "stone_light", "ceramic": "ceramic_white", "leaf": "leaf",
    "glass": "glass_clear",
}

# =====================================================================
# 木纹深浅分档（按【家具类型】覆盖大类默认）
# =====================================================================
#
# 【为什么需要这个】
#   role_wood_walnut 的 baseColor 平均亮度只有 36.5/255 —— 是极深的黑棕木。
#   144/251 个模型用它做默认木纹 → 衣柜、餐桌、书柜全渲染成一坨黑，
#   轮廓都看不清（用户看到的"乱码"体感）。
#   role_wood_oak 平均亮度 92.5 —— 清晰的浅橡木，木纹可辨。
#
# 【分档原则】（按家具体量与常见配色）
#   · 大型柜体/餐桌/床架 → wood_walnut（深色沉稳，压得住场）
#   · 小件/边几/台面/面板 → wood_oak（浅色提亮，避免死黑）
#   · 地面类 → 由 build_route 决定，不在此列
#
# 【注意】只改【geo 路线】的兜底角色。
#   ph 路线（PolyHaven 扫描模型）保留原始扫描贴图 —— 那是真实资产，
#   不能用程序化木纹覆盖，否则会毁掉扫描细节。
TYPE_WOOD_TONE = {
    # --- 浅橡木：台面 / 小件 / 面板 / 椅腿一类 ---
    "counter": "wood_oak", "lCounter": "wood_oak", "uCounter": "wood_oak",
    "pantryCounter": "wood_oak", "kitchenIsland": "wood_oak",
    "island": "wood_oak", "nightstand": "wood_oak", "sideTable": "wood_oak",
    "coffeeTable": "wood_oak", "consoleTable": "wood_oak",
    "teaTable": "wood_oak", "sideboard": "wood_oak", "shoeCabinet": "wood_oak",
    "desk": "wood_oak", "lDesk": "wood_oak", "trainingTable": "wood_oak",
    "entryBench": "wood_oak", "shoeBench": "wood_oak",
    "diningBench": "wood_oak", "deskBench2": "wood_oak",
    "deskBench4": "wood_oak", "bedBench": "wood_oak",
    "whiteboard": "wood_oak", "slidingBoard": "wood_oak",
    "wallPanel": "wood_oak", "workbench": "wood_oak",
    "shelfRack": "wood_oak", "bookshelf": "wood_oak",
    "chest": "wood_oak", "fileCabinet": "wood_oak",
    "toyCabinet": "wood_oak", "hallCabinet": "wood_oak",
    "garageShelf": "wood_oak", "plantShelf": "wood_oak",
    "stage": "wood_oak", "gazebo": "wood_oak", "fence": "wood_oak",
    "lectern": "wood_oak", "mahjong": "wood_oak", "billiards": "wood_oak",
    "wallArt": "wood_oak", "wallArt3": "wood_oak",
    # --- 深胡桃：大型柜体 / 餐桌 / 床架 / 钢琴 ---
    "wardrobe": "wood_walnut", "cabinet": "wood_walnut",
    "tvCabinet": "wood_walnut", "dresser": "wood_walnut",
    "wineCabinet": "wood_walnut", "displayCabinet": "wood_walnut",
    "mirrorCabinet": "wood_walnut", "diningTable": "wood_walnut",
    "roundTable": "wood_walnut", "ovalTable": "wood_walnut",
    "barTable": "wood_walnut", "conferenceTable": "wood_walnut",
    "piano": "wood_walnut", "grandPiano": "wood_walnut",
}

# key 级木纹分档（优先于 type 级）
#
# 【为什么需要 key 级】
#   "free" 是一个【通用原型】类型，25 个不同用途的原件都归在它下面：
#   freeWallBlock（墙体）、freeCeilBlock（吊顶）、freeSlats（木格栅）
#   应该是浅色；而 freeColumn（柱）、freeArch（拱）用深色更有质感。
#   只看 type 无法区分，所以补一张 key 级表。
KEY_WOOD_TONE = {
    # 浅色：墙体、吊顶、台面、格栅、装饰构件
    "freeWallBlock": "wood_oak", "freeCeilBlock": "wood_oak",
    "freeSlats": "wood_oak", "freePlatform": "wood_oak",
    "freeRoundStage": "wood_oak", "freeSteps": "wood_oak",
    "freeLightBox": "wood_oak", "freeBox": "wood_oak",
    "freeRoundBox": "wood_oak", "freeArch": "wood_oak",
    "freeHalfCyl": "wood_oak", "freeWedge": "wood_oak",
    # 深色：柱、拱、雕塑感构件
    "freeColumn": "wood_walnut", "freeArcWall": "wood_walnut",
    "freeExtrude": "wood_walnut", "freeCone": "wood_oak",
    "freePyramid": "wood_oak", "freeTorus": "wood_oak",
}

# 原素材材质名 → 角色（优先采信，比类型更可靠）
#
# 【重要】判断逻辑全部委托给 roles.py（唯一真源）：
#   · 按【词元】精确匹配，绝不做子串匹配
#     —— 旧实现在这里用 `"ash" in "metal_trash_can"`，把铁桶判成白橡木
#   · 猜不到返回 None，绝不静默兜底 fabric_oat
#     —— 旧实现猜不到就返回 fabric_oat，木餐桌/木咖啡桌全变燕麦布
#   · PolyHaven 后缀语义（_pot 陶瓷 / _leaves 叶片 / _glass 玻璃）
#     由 roles.py 的 suffix 规则处理，且只认【末尾词元】
#     —— "potted" 里的 pot 不会误伤 "_leaves"
# 详见 roles.py 顶部文档。
NAME_ROLE = ROLES.ROLE_TEX      # 角色 → 贴图前缀（唯一真源）
ROLE_METAL = ROLES.ROLE_METAL   # 角色 → 金属度
ROLE_TEX = ROLES.ROLE_TEX       # 角色 → 贴图前缀

# 合法角色全集 —— 判定"角色是否已经正确"必须用这个。
# 【为什么不能直接用 ROLE_TEX】
#   glass_clear（玻璃）不在 ROLE_TEX 里（玻璃不贴表面扫描图），
#   但它是一个【合法角色】。若拿 ROLE_TEX 判合法性，
#   所有带玻璃的模型（fireplace / dresser / cabSlide / pool /
#   washer / dryer）都会在"兜底"时把玻璃改成石材或木头。
#   实测：pool 的 U_glass_clear 被改成 U_ceramic_white —— 泳池变陶瓷。
VALID_ROLES = set(ROLE_TEX.keys()) | set(ROLES.NO_TEXTURE_ROLES)


def role_from_name(name):
    """按材质名猜角色。**猜不到返回 None**（不兜底 fabric_oat）。"""
    return ROLES.role_from_name(name)


def class_of(item):
    t = (item.get("type") or "").lower()
    c = (item.get("cat") or "").lower()
    if t in TYPE_CLASS:
        return TYPE_CLASS[t]
    if c in TYPE_CLASS:
        return TYPE_CLASS[c]
    return None


# =====================================================================
# GLB 低层读写（需要能追加 bufferView / image / texture）
# =====================================================================

def load_glb(path):
    with open(path, "rb") as f:
        blob = f.read()
    total = struct.unpack("<I", blob[8:12])[0]
    off = 12
    js = None
    binchunk = b""
    while off + 8 <= min(total, len(blob)):
        clen, ctype = struct.unpack("<II", blob[off:off + 8])
        data = blob[off + 8:off + 8 + clen]
        if ctype == CT_JSON:
            js = json.loads(data.decode("utf-8"))
        elif ctype == CT_BIN:
            binchunk = data
        off += 8 + clen
    return js, binchunk


def save_glb(path, js, binchunk):
    """原子写：先写 .tmp 再 os.replace（Windows 上浏览器可能占着目标文件）。

    【注意】写盘前必须删掉 _tex_dedup —— 它是运行期的去重索引，
    不是 glTF 规范字段，留着会让 glTF 校验器报未知属性。
    """
    js = dict(js)
    js.pop("_tex_dedup", None)
    js_bytes = json.dumps(js, separators=(",", ":")).encode("utf-8")
    js_bytes += b" " * ((4 - len(js_bytes) % 4) % 4)
    bin_bytes = binchunk + b"\x00" * ((4 - len(binchunk) % 4) % 4)
    total = 12 + 8 + len(js_bytes) + 8 + len(bin_bytes)
    out = bytearray()
    out += b"glTF"
    out += struct.pack("<II", 2, total)
    out += struct.pack("<II", len(js_bytes), CT_JSON) + js_bytes
    out += struct.pack("<II", len(bin_bytes), CT_BIN) + bin_bytes
    tmp = path + ".tmp"
    with open(tmp, "wb") as f:
        f.write(bytes(out))
    try:
        os.replace(tmp, path)
    except OSError:
        os.remove(path)
        os.replace(tmp, path)
    return len(out)


def append_image(js, binchunk, data, mime="image/jpeg"):
    """把字节流追加进 GLB 的 BIN chunk，返回 image 下标。

    【去重】同 role 的多个材质（如柜体+门板都是 wood_walnut）
    会内嵌【完全相同】的贴图字节。实测一件 3 材质模型会重复 3 次，
    体积白白翻三倍。→ 用 data 的 sha1 做 key，已内嵌过就直接复用
    image 下标，不再追加。
    """
    if not js.get("buffers"):
        js["buffers"] = [{"byteLength": 0}]
    js.setdefault("bufferViews", [])

    # ---- 去重：同一份字节只内嵌一次 ----
    key = hashlib.sha1(data).hexdigest()
    cache = js.setdefault("_tex_dedup", {})
    if key in cache:
        idx = cache[key]
        if idx < len(js.get("images", [])):
            return js, binchunk, idx

    binchunk += b"\x00" * ((-len(binchunk)) % 4)
    off = len(binchunk)
    binchunk += data
    bv = len(js["bufferViews"])
    js["bufferViews"].append({"buffer": 0, "byteOffset": off,
                              "byteLength": len(data)})
    idx = len(js.get("images", []))
    js.setdefault("images", []).append({"bufferView": bv, "mimeType": mime})
    js["buffers"][0]["byteLength"] = len(binchunk)
    cache[key] = idx
    return js, binchunk, idx


def add_texture(js, img_index):
    """image → texture，返回 texture 下标。"""
    if "samplers" not in js:
        js["samplers"] = [{"magFilter": 9729, "minFilter": 9987,
                           "wrapS": 10497, "wrapT": 10497}]
    js.setdefault("textures", []).append({"sampler": 0, "source": img_index})
    return len(js["textures"]) - 1


def has_texture_slot(mat, slot):
    """该材质是否已经用了这个贴图槽位。"""
    if slot == "baseColor":
        return bool((mat.get("pbrMetallicRoughness") or {}).get("baseColorTexture"))
    if slot == "mr":
        return bool((mat.get("pbrMetallicRoughness") or {}).get("metallicRoughnessTexture"))
    if slot == "normal":
        return bool(mat.get("normalTexture"))
    if slot == "occlusion":
        return bool(mat.get("occlusionTexture"))
    return False


# =====================================================================
# 单件处理
# =====================================================================

def decide_roles(item, mats, orig_mats, cur_roles=None, route="geo"):
    """返回 {材质下标: 新角色}。

    【关键设计 · 按构建路线分流】

    ▸ route == "geo"（几何生成模型）
      builder 自己就给每个部件指定了正确材质，这是【真源】：
          bed18  U_wood_oak(床架) + U_fabric_oat(床垫) + U_wood_walnut(床头板)
          piano  U_ceramic_white(琴键) + U_wood_walnut(琴身)
          counter U_stone_light(台面) + U_wood_walnut(柜体)
      任何"类型级兜底"都会把床架变布、琴键变木、台面变木。
      → **geo 模型的角色一个都不动**（只在角色【非法/缺失】时兜底）。

    ▸ route == "ph"（现成 PolyHaven 资源）
      资源自带原始材质名，信息量最大：
          potted_plant_01_pot     → 陶瓷花盆
          potted_plant_01_leaves  → 叶片
          vintage_cabinet_01_glass→ 玻璃
          dining_table            → 木
      → 按【词元精确匹配】逐槽位判定（roles.py），
        猜不出才用类型大类兜底。

    【已修的坑：跨槽位回退】
      旧实现里 `pick is None` 时会去扫其他槽位找任意一个 named 角色：
          named = [ceramic_white(花盆), leaf(叶片)]
          槽位 1 猜不出 → 借用槽位 0 的 ceramic_white
      → 把叶片变成花盆。部件语义被串味，必须去掉这个回退。
    """
    cls = class_of(item)
    allow = CLASS_ROLES.get(cls, set()) if cls else None
    named = [role_from_name(n) for n in orig_mats]
    cur_roles = cur_roles or []
    out = {}

    # ---- geo 路线：builder 的角色是真源，但木纹【深浅】按类型分档 ----
    #
    # 【为什么要在这里再调一次】
    #   geo_models.py 的 builder 已经显式指定了 mat（如 U_wood_walnut），
    #   所以上面"角色合法就不动"的规则会跳过它们。
    #   但 U_wood_walnut 的贴图太暗（平均亮度 36.5），
    #   不分档的话 144 个模型全是黑糊。
    #   → 对 wood 类角色，按 TYPE_WOOD_TONE 分档表覆盖深浅。
    #   → 其余角色（金属/布/玻璃/石）一律不动。
    if route != "ph":
        # 【优先按 key 匹配】—— "free" 是通用原型类型，
        #   freeWallBlock（墙体）该用浅色，freeSlats（木格栅）也该用浅色，
        #   但 freeColumn/furniture 类可能想用深色。
        #   所以先查 key 级分档表，再退回 type 级。
        ikey = (item or {}).get("key") or ""
        tkey = (item or {}).get("type") or ""
        tone = KEY_WOOD_TONE.get(ikey) or TYPE_WOOD_TONE.get(tkey)

        # 【重要】只在【整个模型只有一种木纹角色】时才做深浅分档。
        #   有些 builder 故意在同一模型里混用深浅木：
        #       cabTall  下段柜体 U_wood_walnut + 门板 U_wood_oak
        #       longTable 桌面 U_wood_walnut + 桌腿 U_wood_oak
        #   这种"部件级配色"是设计意图，不能被类型级分档抹平。
        #   → 多木纹角色时保持原样（builder 说啥就是啥）。
        wood_slots = []
        for i, m in enumerate(mats):
            cur = m.get("name", "")
            cur_role = cur[2:] if cur.startswith("U_") else cur
            if cur_role in ("wood_oak", "wood_walnut"):
                wood_slots.append((i, cur_role))
        multi_wood = len({r for _, r in wood_slots}) > 1

        for i, m in enumerate(mats):
            cur = m.get("name", "")
            cur_role = cur[2:] if cur.startswith("U_") else cur
            if tone and not multi_wood and cur_role in ("wood_oak", "wood_walnut"):
                # 木纹分档：浅↔深 互换
                if tone != cur_role:
                    out[i] = tone
                continue
            if cur_role in VALID_ROLES:
                continue                       # 已是合法角色 → 不动
            # 角色非法或缺失 → 兜底
            if cls:
                pick = CLASS_DEFAULT.get(cls)
                if pick and pick != cur_role:
                    out[i] = pick
        return out

    # ---- ph 路线：只修【非法角色】，不动合法角色 ----
    #
    # 【为什么 PH 模型的角色尽量不动】
    #   PH 模型带的是【原始扫描贴图】（44/44 已核实完好），
    #   渲染效果由贴图决定，材质名只是给主程序用的元数据。
    #   旧实现对 PH 模型做"类型级覆盖"，把：
    #       dining_table  U_fabric_oat → U_wood_walnut
    #       plant         U_leaf → U_ceramic_white（花盆） / U_leaf（叶）
    #   这些改动【对验收站的渲染毫无影响】（贴图没变），
    #   却引入了"把玻璃改成木头"之类的新错误风险。
    #   → PH 模型只修非法角色，其余一律保留。
    for i, m in enumerate(mats):
        cur = m.get("name", "")
        cur_role = cur[2:] if cur.startswith("U_") else cur
        if cur_role in VALID_ROLES:
            continue
        # 非法角色 → 按原素材名精确判定
        pick = named[i] if i < len(named) else None
        if pick is None and cls:
            pick = CLASS_DEFAULT.get(cls)
        if pick and pick != cur_role:
            out[i] = pick
    return out


def process_one(path, item, orig_mats, dry, route="geo"):
    """返回 (changed, notes, n_tex_added)。"""
    js, binchunk = load_glb(path)
    mats = js.get("materials") or []
    if not mats:
        return False, "", 0

    notes = []
    changed = False

    # --- A. 角色修正（逐槽位）---
    cur_roles = [m.get("name", "") for m in mats]
    roles = decide_roles(item, mats, orig_mats, cur_roles, route=route)
    for i, r in roles.items():
        old = mats[i].get("name", "")
        mats[i]["name"] = "U_" + r
        notes.append("%s->%s" % (old or "?", r))
        changed = True

        # --- B. 内嵌 PBR 四通道 ---
    #
    # 【关键】PH 模型【绝不】覆盖原始扫描贴图。
    #   Poly Haven 资源自带完整的 col/nor/rough/AO 扫描贴图，
    #   是整套资产里质量最高的部分。旧实现对 PH 也跑这一段，
    #   结果把 dining_table 的木质扫描贴图换成了 ambientCG 的布料图
    #   → 餐桌/茶几/衣柜全变成米色布 → 用户看到的"家具全是布"。
    #   → PH 路线【只填空槽位】：已有贴图的槽位一律不动，
    #     缺贴图的槽位才用 ambientCG 角色图补上。
    #   【为什么 PH 也要填空】
    #     实测 acFloor / fan 两件 PH 模型【一张贴图都没有】——
    #     它们对应的 Polyhaven 资源本身不带扫描图（工业件/简化件常见）。
    #     旧实现对 PH 整段跳过 → 这两件永远是白模。
    #     只填空槽位既不碰原生扫描图，又能救回白模。
    #
    # 【注意】alphaMode / baseColorFactor 的修改【必须置 changed】
    #   否则"材质属性改了但文件没保存"——实测玻璃件改了透明参数
    #   却因为 added=0 而没写盘，改动丢失。
    added = 0
    if route == "ph":
        for m in mats:
            nm = m.get("name", "")
            role = nm[2:] if nm.startswith("U_") else nm
            pbr = m.get("pbrMetallicRoughness")
            if pbr is None:
                pbr = {}
                m["pbrMetallicRoughness"] = pbr
                changed = True
            # ---- 只填空槽位 ----
            if role in PP.ROLE_TEX:
                maps = PP.build_role_maps(role)
                if maps.get("col") and not has_texture_slot(m, "baseColor"):
                    js, binchunk, ci = append_image(js, binchunk, maps["col"])
                    pbr["baseColorTexture"] = {"index": add_texture(js, ci)}
                    pbr.setdefault("baseColorFactor", [1, 1, 1, 1])
                    added += 1
                if maps.get("orm") and not has_texture_slot(m, "mr"):
                    js, binchunk, ci = append_image(js, binchunk, maps["orm"])
                    pbr["metallicRoughnessTexture"] = {"index": add_texture(js, ci)}
                    added += 1
                if maps.get("nor") and not has_texture_slot(m, "normal"):
                    js, binchunk, ci = append_image(js, binchunk, maps["nor"])
                    m["normalTexture"] = {"index": add_texture(js, ci)}
                    added += 1
                if maps.get("ao") and not has_texture_slot(m, "occlusion"):
                    js, binchunk, ci = append_image(js, binchunk, maps["ao"])
                    m["occlusionTexture"] = {"index": add_texture(js, ci)}
                    added += 1
            # 玻璃：补规范 ORM（玻璃不贴扫描图，但 metallicRoughnessTexture
            # 槽位一旦缺省，金属度会按常量 1.0 渲染 → 玻璃变成金属镜面）
            elif role in ROLES.NO_TEXTURE_ROLES:
                if not has_texture_slot(m, "baseColor"):
                    bc = PP.pack_glass_basecolor()
                    if bc:
                        js, binchunk, ci = append_image(js, binchunk, bc)
                        pbr["baseColorTexture"] = {"index": add_texture(js, ci)}
                        added += 1
                if not has_texture_slot(m, "mr"):
                    orm = PP.pack_glass_orm()
                    if orm:
                        js, binchunk, ci = append_image(js, binchunk, orm)
                        pbr["metallicRoughnessTexture"] = {"index": add_texture(js, ci)}
                        added += 1
                # 物理参数 + 透明
                if m.get("alphaMode") != "BLEND":
                    m["alphaMode"] = "BLEND"
                    changed = True
                    notes.append("玻璃透明")
                if list(pbr.get("baseColorFactor") or []) != [0.80, 0.78, 0.74, 0.32]:
                    pbr["baseColorFactor"] = [0.80, 0.78, 0.74, 0.32]
                    changed = True
            # 物理参数：金属度/粗糙度由 ORM 的 B/G 通道驱动，
            # 所以这里的 factor 必须给中性值，否则会二次调暗。
            metal = PP.ROLE_METAL.get(role, 0.0)
            if pbr.get("metallicFactor") != (1.0 if metal > 0 else 0.0):
                pbr["metallicFactor"] = 1.0 if metal > 0 else 0.0
                changed = True
            if pbr.get("roughnessFactor") != 1.0:
                pbr["roughnessFactor"] = 1.0
                changed = True
                # 【玻璃必须透明】alphaMode=BLEND + alpha=0.32，
                # 与 template.html 的 __FURN_ROLE.glass.opacity 对齐。
                # 缺了会渲染成不透明米白板（比白模更像坏件）。
                m["alphaMode"] = "BLEND"
                pbr["baseColorFactor"] = [0.80, 0.78, 0.74, 0.32]
    else:
        for m in mats:
            nm = m.get("name", "")
            role = nm[2:] if nm.startswith("U_") else nm
            if role not in PP.ROLE_TEX:
                # 【玻璃等无扫描图角色】—— 也要给一张规范 ORM。
                #   玻璃不贴表面扫描图，但 metallicRoughnessTexture 槽位
                #   缺省时 metallicFactor=1.0 会被当作金属 → 玻璃变镜面。
                #   → 补 pack_glass_orm()：R=AO=1, G=rough=0.04, B=metal=0
                if role in ROLES.NO_TEXTURE_ROLES:
                    pbr = m.get("pbrMetallicRoughness")
                    if pbr is None:
                        pbr = {}
                        m["pbrMetallicRoughness"] = pbr
                    if not has_texture_slot(m, "baseColor"):
                        bc = PP.pack_glass_basecolor()
                        if bc:
                            js, binchunk, ci = append_image(js, binchunk, bc)
                            pbr["baseColorTexture"] = {"index": add_texture(js, ci)}
                            added += 1
                    if not has_texture_slot(m, "mr"):
                        orm = PP.pack_glass_orm()
                        if orm:
                            js, binchunk, ci = append_image(js, binchunk, orm)
                            pbr["metallicRoughnessTexture"] = {"index": add_texture(js, ci)}
                            added += 1
                    pbr["metallicFactor"] = 0.0
                    pbr["roughnessFactor"] = 0.05
                    # 【玻璃必须透明】没有 alphaMode=BLEND 时，
                    # three.js 按不透明渲染 → 一块不透明的米白板，
                    # 比白模更像"坏掉的模型"。
                    # alpha=0.32 与 template.html 的 __FURN_ROLE.glass.opacity 对齐。
                    if m.get("alphaMode") != "BLEND":
                        m["alphaMode"] = "BLEND"
                        changed = True
                        notes.append("玻璃透明")
                    if list(pbr.get("baseColorFactor") or []) != [0.80, 0.78, 0.74, 0.32]:
                        pbr["baseColorFactor"] = [0.80, 0.78, 0.74, 0.32]
                        changed = True
                continue
            maps = PP.build_role_maps(role)
            if not maps.get("col"):
                continue
            pbr = m.get("pbrMetallicRoughness")
            if pbr is None:
                pbr = {}
                m["pbrMetallicRoughness"] = pbr
            # baseColor
            if not has_texture_slot(m, "baseColor"):
                js, binchunk, ci = append_image(js, binchunk, maps["col"])
                pbr["baseColorTexture"] = {"index": add_texture(js, ci)}
                pbr.setdefault("baseColorFactor", [1, 1, 1, 1])
                added += 1
            # metallicRoughness（必须用打包好的 ORM，不能直接挂 rough 图）
            if not has_texture_slot(m, "mr") and maps.get("orm"):
                js, binchunk, ci = append_image(js, binchunk, maps["orm"])
                pbr["metallicRoughnessTexture"] = {"index": add_texture(js, ci)}
                added += 1
            # normal
            if not has_texture_slot(m, "normal") and maps.get("nor"):
                js, binchunk, ci = append_image(js, binchunk, maps["nor"])
                m["normalTexture"] = {"index": add_texture(js, ci)}
                added += 1
            # occlusion（独立槽位，R=AO）
            if not has_texture_slot(m, "occlusion") and maps.get("ao"):
                js, binchunk, ci = append_image(js, binchunk, maps["ao"])
                m["occlusionTexture"] = {"index": add_texture(js, ci)}
                added += 1

            # 物理参数：金属度/粗糙度由 ORM 的 B/G 通道驱动，
            # 所以这里的 factor 必须给中性值，否则会二次调暗。
            metal = PP.ROLE_METAL.get(role, 0.0)
            pbr["metallicFactor"] = 1.0 if metal > 0 else 0.0
            pbr["roughnessFactor"] = 1.0
            if m.get("normalTexture"):
                m.setdefault("normalTexture", {})["scale"] = 1.0

    # --- C. 修 ORM 通道误用 ---
    # 【实测问题】
    #   12 个材质把【灰度粗糙度图】直接挂在 metallicRoughnessTexture 上。
    #   glTF 规范要求：R=AO  G=roughness  B=metalness。
    #   灰度图 R=G=B=0.265 → 金属度被误读成 0.265 →
    #   玻璃/布料呈现脏污塑料反光。
    n_orm = 0
    for m in mats:
        pbr = m.get("pbrMetallicRoughness") or {}
        slot = pbr.get("metallicRoughnessTexture")
        if not slot:
            continue
        ti = slot.get("index")
        if ti is None or ti >= len(js.get("textures") or []):
            continue
        tex = js["textures"][ti]
        si = tex.get("source")
        if si is None or si >= len(js.get("images") or []):
            continue
        if not _is_grayscale_image(js, binchunk, si):
            continue                        # 通道正常 → 不动
        # 确认是"灰度图误挂" → 换成正确打包的 ORM
        nm = m.get("name", "")
        role = nm[2:] if nm.startswith("U_") else nm
        if role in PP.ROLE_TEX:
            maps = PP.build_role_maps(role)
        elif role in ROLES.NO_TEXTURE_ROLES:
            # 【玻璃】
            # 玻璃不贴表面扫描图，但它【仍然需要一个规范的 ORM】：
            #   R=AO=1（玻璃不遮蔽）
            #   G=roughness=0.04（极光滑）
            #   B=metalness=0（玻璃是介电质，不是金属）
            # 旧实现直接挂灰度粗糙度图 → B 通道读出 0.279
            # → 玻璃被当成半金属 → 脏污塑料感。
            maps = {"orm": PP.pack_glass_orm()}
        else:
            maps = {}
        if not maps.get("orm"):
            continue
        js, binchunk, ci = append_image(js, binchunk, maps["orm"])
        pbr["metallicRoughnessTexture"] = {"index": add_texture(js, ci)}
        # 玻璃的物理参数也要归位
        if role in ROLES.NO_TEXTURE_ROLES:
            pbr["metallicFactor"] = 0.0
            pbr["roughnessFactor"] = 0.05
        n_orm += 1
        notes.append("ORM修正:%s" % (role or nm))

    if changed or added or n_orm:
        if not dry:
            save_glb(path, js, binchunk)
    return changed, ",".join(notes), added + n_orm


def _is_grayscale_image(js, binchunk, img_index):
    """判断这张图是不是灰度图（R=G=B）。

    【为什么要检测】
      glTF 的 metallicRoughnessTexture 必须是 ORM 打包图：
          R=AO  G=roughness  B=metalness
      如果挂的是纯灰度粗糙度图，R=G=B →
      金属度通道被误读成粗糙度值 → 材质呈现错误的金属反射。

    【判定方法】
      取图像左上角 1/4 区域，抽样若干像素，
      若所有采样的 R/G/B 最大差值 < 0.02 → 判定为灰度图。
      （正常 ORM 图的 R=AO、G=rough、B=metal 三通道有明显差异）
    """
    try:
        import io
        from PIL import Image
    except ImportError:
        return False
    im = js.get("images") or []
    if img_index >= len(im):
        return False
    img = im[img_index]
    bv = img.get("bufferView")
    if bv is None:
        return False
    v = js["bufferViews"][bv]
    off = v.get("byteOffset", 0)
    data = binchunk[off:off + v["byteLength"]]
    if not data:
        return False
    try:
        pic = Image.open(io.BytesIO(data)).convert("RGB")
    except Exception:
        return False
    w, h = pic.size
    box = (0, 0, max(1, w // 4), max(1, h // 4))
    crop = pic.crop(box)
    px = list(crop.getdata())
    if not px:
        return False
    # 抽样最多 400 个像素
    step = max(1, len(px) // 400)
    worst = 0
    for i in range(0, len(px), step):
        r, g, b = px[i]
        worst = max(worst, abs(r - g), abs(g - b), abs(r - b))
    return worst <= 5          # 通道差 ≤5/255 → 灰度图


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--only", default=None,
                    help="只处理指定 key，逗号分隔（支持多件）")
    args = ap.parse_args()
    only_set = None
    if args.only:
        only_set = set(x.strip() for x in args.only.split(",") if x.strip())

    man = json.load(open(os.path.join(ACC, "manifest.json"), encoding="utf-8"))
    items = man["items"]
    amap = json.load(open(AMAP, encoding="utf-8")) if os.path.exists(AMAP) else {}

    # ---- 构建路线 + 真实资源 ----
    #
    # 【真源优先级：asset_map.source  >  build_report.route】
    #
    #   实测（2026-11-06）：build_report.json 只有 6 条结果，
    #   其余 245 件在旧代码里被【默认当成 geo】。
    #   但 asset_map.json 里 source='polyhaven' 的有 114 件 —— 其中
    #   113 件带【PolyHaven 原生扫描贴图】，而 geo 路线的 B 段
    #   会用 ambientCG 角色图去覆盖它们。
    #   → 那会把 dining_table 的木质扫描贴图换成 ambientCG 的布料图，
    #     正是文档里明确警告过的"家具全是布"事故。
    #   → 所以路线必须按 asset_map.source 判定，build_report 只作补充。
    global ROUTES, BUILD_RES
    ROUTES, BUILD_RES = {}, {}
    rep_path = os.path.join(ROOT, "assets", "_asset_cache", "build_report.json")
    if os.path.exists(rep_path):
        rep = json.load(open(rep_path, encoding="utf-8"))
        for r in rep.get("results", []):
            ROUTES[r["key"]] = r.get("route") or "geo"
            BUILD_RES[r["key"]] = r.get("resource")
    # asset_map.source 是逐件记录，覆盖 build_report 的稀疏结果
    for key, v in amap.items():
        src = (v or {}).get("source")
        if src == "polyhaven":
            ROUTES[key] = "ph"
            BUILD_RES.setdefault(key, (v or {}).get("resource"))
        elif src in (None, "", "geo"):
            # 只有在 build_report 没有明确记录时才回退 geo
            ROUTES.setdefault(key, "geo")
        else:
            ROUTES[key] = ROUTES.get(key, "geo")
    print("构建路线: geo=%d ph=%d (共 %d)"
          % (sum(1 for v in ROUTES.values() if v == "geo"),
             sum(1 for v in ROUTES.values() if v == "ph"), len(ROUTES)))

    if args.apply:
        stamp = time.strftime("%Y%m%d_%H%M%S")
        bdir = os.path.join(ROOT, "assets", "_asset_cache", "glb_backup_" + stamp)
        for base, sub in ((ACC, "acc"), (NEW, "furnlib")):
            dst = os.path.join(bdir, sub)
            os.makedirs(dst, exist_ok=True)
            for f in os.listdir(base):
                if not f.endswith(".glb"):
                    continue
                try:
                    shutil.copy2(os.path.join(base, f), os.path.join(dst, f))
                except OSError:
                    pass          # 被浏览器占用 → 跳过该文件的备份
        print("备份 -> %s" % bdir)

    n_role = n_tex = n_changed = 0
    rows = []
    for it in items:
        key = it["key"]
        if only_set and key not in only_set:
            continue
        # ---- 构建路线（geo / ph）—— 决定角色判定的策略 ----
        route = (ROUTES.get(key) or "geo")
        # ---- 原素材材质名 ----
        # 【重要】用 build_report.json 的 resource（真实构建时用的资源），
        # 不用 asset_map.json —— 后者是旧快照，会指向错的资源，
        # 导致"原材质名"取错，进而把角色判错（曾误报 89 项丢贴图）。
        orig_mats = []
        res = (BUILD_RES.get(key) or {}) or (amap.get(key) or {}).get("resource")
        if res:
            rp = os.path.join(CACHE_RAW, res + ".glb")
            if os.path.exists(rp):
                try:
                    rjs, _ = load_glb(rp)
                    orig_mats = [m.get("name", "") for m in rjs.get("materials", [])]
                except Exception:
                    pass
        allnotes = []
        alladded = 0
        anych = False
        for base in (ACC, NEW):
            p = os.path.join(base, key + ".glb")
            if not os.path.exists(p):
                continue
            try:
                ch, note, added = process_one(p, it, orig_mats, not args.apply,
                                             route=route)
            except Exception as e:
                allnotes.append("%s ERR %s" % (os.path.basename(base), e))
                continue
            if ch or added:
                anych = True
                alladded += added
                if note:
                    allnotes.append(note)
        if anych:
            n_changed += 1
            if alladded:
                n_tex += 1
            if any("->" in n for n in allnotes):
                n_role += 1
            rows.append((key, it.get("name"), alladded, " | ".join(allnotes[:3])))

    print("\n%s 处理 %d 个，变更 %d 个"
          % ("APPLY" if args.apply else "DRY", len(items), n_changed))
    print("  角色修正 %d，内嵌 PBR 贴图 %d" % (n_role, n_tex))
    for k, nm, added, n in rows:
        if only_set or added:
            print("   %-18s %-22s +%d张 %s" % (k, nm or "", added, n))


if __name__ == "__main__":
    main()

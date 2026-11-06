"""修复 251 个 GLB 的材质角色错配 + 给没贴图的模型接上真实扫描 PBR。

【问题根因（实测证据）】
1. normalize_glb.guess_role() 只按材质名里的关键字猜角色，猜不到就
   【默认返回 "fabric_oat"】。
   → diningTable / wardrobe / coffeeTable / officeDesk / lawn / tree / wallArt
     这些明显不是布的模型，全被打成 U_fabric_oat。
   → 主程序用 __furnMat("fabric_oat") 套燕麦布 PBR（粗糙度 .95 + 米色染色）
     → 木纹衣柜渲染成"米色布柜子"。
2. 只有 44/251 个模型内嵌了贴图，其余 207 个是纯色白模。
   验收站 app.js 又完全没有 U_* → 扫描贴图的映射逻辑
   → 验收站里 207 件家具全是"一坨纯色"，用户看到的就是"乱码"。

【本脚本做什么】
A. 角色修正：【逐材质】判定。对每个材质，按
   ① 原素材材质名关键字 → ② 家具类型 → ③ 保留原角色 的顺序取角色。
   混合材质模型（衣柜=柜体木+镜面玻璃）不会被整体改写。
B. 贴图补齐：模型缺 baseColorTexture 且材质角色有对应 ambientCG 扫描贴图时，
   把 col/nor/rough/ao 四通道打包进 GLB 的 images/textures，
   让任何查看器（验收站 / 主程序 / Blender / 第三方）都直接看到真实 PBR。

【安全】
- 默认只报告；--apply 才写盘。
- 写盘前自动备份到 assets/_asset_cache/glb_backup_<时间戳>/。
- 不改几何、不改尺寸、不改顶点，只改材质名 + 贴图。

用法：
  python fix_roles_pbr.py
  python fix_roles_pbr.py --apply
  python fix_roles_pbr.py --apply --only diningTable
"""
import argparse
import json
import os
import shutil
import struct
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
ACC = os.path.join(ROOT, "assets", "furnlib")
NEW = os.path.join(ROOT, "assets", "furnlib")
TEX = os.path.join(ROOT, "assets", "furnlib", "tex")
CACHE_RAW = os.path.join(ROOT, "assets", "_asset_cache", "raw")
AMAP = os.path.join(ROOT, "assets", "_asset_cache", "asset_map.json")

CT_JSON = 0x4E4F534A
CT_BIN = 0x004E4942


# =====================================================================
# 角色体系
# =====================================================================

# 角色 → ambientCG 扫描贴图前缀（None = 该角色不贴图，如玻璃）
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
    "glass_clear": None,
}

# 家具【类型】→ 期望的大类
TYPE_CLASS = {
    # --- 木作（桌/柜/架） ---
    "diningTable": "wood", "roundTable": "wood", "ovalTable": "wood",
    "coffeeTable": "wood", "sideTable": "wood", "conferenceTable": "wood",
    "consoleTable": "wood", "desk": "wood", "lDesk": "wood",
    "trainingTable": "wood", "teaTable": "wood",
    "wardrobe": "wood", "cabinet": "wood", "shelfRack": "wood",
    "bookshelf": "wood", "chest": "wood", "tvCabinet": "wood",
    "nightstand": "wood", "sideboard": "wood", "shoeCabinet": "wood",
    "dresser": "wood", "wineCabinet": "wood", "displayCabinet": "wood",
    "mirrorCabinet": "wood", "island": "wood", "kitchenIsland": "wood",
    "counter": "wood", "lCounter": "wood", "uCounter": "wood",
    "pantryCounter": "wood", "workbench": "wood", "lectern": "wood",
    "fileCabinet": "wood", "toyCabinet": "wood", "hallCabinet": "wood",
    "garageShelf": "wood", "plantShelf": "wood",
    # --- 软包 ---
    "sofa": "fabric", "lSofa": "fabric", "uSofa": "fabric",
    "armchair": "fabric", "chaise": "fabric", "beanbag": "fabric",
    "chair": "fabric", "officeChair": "fabric", "barStool": "fabric",
    "stool": "fabric", "ottoman": "fabric", "bench": "fabric",
    "bed": "fabric", "roundBed": "fabric", "bunkBed": "fabric",
    "crib": "fabric", "bedBench": "fabric", "dayBed": "fabric",
    "hangingChair": "fabric", "rockingChair": "fabric",
    "sunLounger": "fabric", "outdoorSet": "fabric",
    "rug": "fabric", "rugRound": "fabric", "yogaMat": "fabric",
    "playMat": "fabric", "doormat": "fabric",
    "curtain": "fabric", "sheer": "fabric",
    "petBed": "fabric", "bayCushion": "fabric", "reception": "fabric",
    "booth": "fabric",
    # --- 陶瓷/洁具 ---
    "toilet": "ceramic", "squat": "ceramic", "bathtub": "ceramic",
    "freeTub": "ceramic", "sink": "ceramic", "vanity": "ceramic",
    "pedestalSink": "ceramic", "urinal": "ceramic",
    "serviceSink": "ceramic", "laundrySink": "ceramic",
    "mirror": "glass", "wallArt": "wood", "wallArt3": "wood",
    "wallPanel": "wood", "wallTV": "metal", "wallClock": "metal",
    "whiteboard": "wood", "slidingBoard": "wood", "projScreen": "fabric",
    # --- 金属设备 ---
    "fridge": "metal", "freezer": "metal", "washer": "metal",
    "dryer": "metal", "dishwasher": "metal", "hood": "metal",
    "microwave": "metal", "oven": "metal", "tallOven": "metal",
    "coffeeMachine": "metal", "printer": "metal", "mobileDisplay": "metal",
    "waterHeater": "metal", "gasHeater": "metal", "boiler": "metal",
    "waterDispenser": "metal", "purifier": "metal", "robotVac": "metal",
    "elevator": "metal", "evCharger": "metal", "waterSoftener": "metal",
    "speaker": "metal", "wifiAP": "metal", "ceilingSpeaker": "metal",
    "airVent": "metal", "radiator": "metal", "fan": "metal",
    "floorLamp": "metal", "deskLamp": "metal", "lawnLamp": "metal",
    "chandelier": "metal", "swing": "metal", "slide": "metal",
    "treadmill": "bike", "bike": "metal", "bicycle": "metal",
    # --- 石材 ---
    "freeArcWall": "stone", "freeArch": "stone", "freeColumn": "stone",
    "freeHalfCyl": "stone", "freeHemi": "stone", "freeSphere": "stone",
    "freeBox": "wood", "freeCone": "wood", "freeCyl": "metal",
    "freeExtrude": "wood", "freeLightBox": "metal",
    "freeGlassScreen": "glass", "freeMirror": "glass",
    "freePlatform": "wood", "freePyramid": "wood",
    "freeRoundBox": "wood", "freeRoundStage": "wood",
    "freeSlats": "wood", "freeTorus": "wood", "freeTube": "metal",
    "freeVase": "ceramic", "freeWallBlock": "wood", "freeWedge": "wood",
    "freeCeilBlock": "wood",
    # --- 植物 ---
    "plant": "leaf", "hangingPlant": "leaf", "shrub": "leaf",
    "lawn": "leaf", "tree": "leaf",
    # --- 户外/其他 ---
    "fence": "wood", "gazebo": "wood", "gate": "wood",
    "carport": "metal", "car": "metal", "suv": "metal",
    "bbq": "metal", "parasol": "fabric", "pool": "ceramic",
    "waterFeature": "stone", "stepStones": "stone",
    "fishTank": "glass", "vase": "ceramic", "floorVase": "ceramic",
    "piano": "wood", "grandPiano": "wood", "mahjong": "wood",
    "billiards": "wood", "fireplace": "stone", "catTree": "fabric",
    "clothesRack": "metal", "coatRack": "metal", "lockers": "metal",
    "screenDivider": "fabric", "stage": "wood", "stairs": "stone",
    "stairRun": "stone", "stairU": "stone", "stairLanding": "stone",
    "tatami": "fabric", "kitchenTrolley": "metal", "mall": "metal",
    "mall2": "metal", "mall3": "metal", "mall4": "metal",
}

# 大类 → 该类允许的角色
CLASS_ROLES = {
    "wood": {"wood_oak", "wood_walnut"},
    "fabric": {"fabric_oat", "fabric_oat_d", "fabric_cream", "fabric_grey"},
    "metal": {"metal_black", "metal_steel", "metal_brass"},
    "stone": {"stone_light", "stone_dark"},
    "ceramic": {"ceramic_white"},
    "leaf": {"leaf"},
    "glass": {"glass_clear"},
}

# 大类 → 默认角色
CLASS_DEFAULT = {
    "wood": "wood_walnut",
    "fabric": "fabric_oat",
    "metal": "metal_black",
    "stone": "stone_light",
    "ceramic": "ceramic_white",
    "leaf": "leaf",
    "glass": "glass_clear",
}

# 原素材材质名关键字 → 角色（优先采信，比类型更可靠）
NAME_ROLE = [
    ("walnut", "wood_walnut"), ("oak", "wood_oak"), ("wood", "wood_walnut"),
    ("timber", "wood_oak"), ("plywood", "wood_oak"), ("veneer", "wood_oak"),
    ("teak", "wood_walnut"), ("birch", "wood_oak"), ("mahogany", "wood_walnut"),
    ("bamboo", "wood_oak"), ("rattan", "wood_walnut"), ("cane", "wood_oak"),
    ("wenge", "wood_walnut"), ("ash", "wood_oak"), ("pine", "wood_oak"),
    ("marble", "stone_light"), ("granite", "stone_dark"), ("slate", "stone_dark"),
    ("travertine", "stone_light"), ("terrazzo", "stone_light"),
    ("linen", "fabric_cream"), ("cotton", "fabric_cream"),
    ("wool", "fabric_oat"), ("felt", "fabric_grey"),
    ("velvet", "fabric_grey"), ("leather", "fabric_grey"),
    ("suede", "fabric_grey"), ("canvas", "fabric_cream"),
    ("cloth", "fabric_oat"), ("uphol", "fabric_oat"),
    ("fabric", "fabric_oat"), ("textile", "fabric_oat"),
    ("cushion", "fabric_oat"), ("fiber", "fabric_grey"),
    ("brass", "metal_brass"), ("gold", "metal_brass"),
    ("copper", "metal_brass"), ("bronze", "metal_brass"),
    ("chrome", "metal_steel"), ("aluminium", "metal_steel"),
    ("aluminum", "metal_steel"), ("steel", "metal_steel"),
    ("iron", "metal_black"), ("metal", "metal_black"),
    ("powder", "metal_black"), ("painted", "metal_black"),
    ("ceramic", "ceramic_white"), ("porcelain", "ceramic_white"),
    ("concrete", "stone_light"), ("stone", "stone_light"),
    ("glass", "glass_clear"), ("mirror", "glass_clear"),
    ("leaf", "leaf"), ("foliage", "leaf"), ("plant", "leaf"),
    ("grass", "leaf"), ("moss", "leaf"),
]


def role_from_name(name):
    low = (name or "").lower()
    for hint, role in NAME_ROLE:
        if hint in low:
            return role
    return None


def class_of(item):
    t = (item.get("type") or "").lower()
    c = (item.get("cat") or "").lower()
    if t in TYPE_CLASS:
        return TYPE_CLASS[t]
    if c in TYPE_CLASS:
        return TYPE_CLASS[c]
    return None


# =====================================================================
# GLB 读写
# =====================================================================

def load_glb(path):
    blob = open(path, "rb").read()
    total = struct.unpack("<I", blob[8:12])[0]
    off = 12
    js = None
    binchunk = None
    while off + 8 <= min(total, len(blob)):
        clen, ctype = struct.unpack("<II", blob[off:off + 8])
        data = blob[off + 8:off + 8 + clen]
        if ctype == CT_JSON:
            js = json.loads(data.decode("utf-8"))
        elif ctype == CT_BIN:
            binchunk = data
        off += 8 + clen
    return js, binchunk, blob


def write_glb(path, js, binchunk):
    js_bytes = json.dumps(js, separators=(",", ":")).encode("utf-8")
    js_bytes += b" " * ((4 - len(js_bytes) % 4) % 4)
    bin_bytes = binchunk + b"\x00" * ((4 - len(binchunk) % 4) % 4)
    total = 12 + 8 + len(js_bytes) + 8 + len(bin_bytes)
    out = bytearray()
    out += b"glTF"
    out += struct.pack("<II", 2, total)
    out += struct.pack("<II", len(js_bytes), CT_JSON) + js_bytes
    out += struct.pack("<II", len(bin_bytes), CT_BIN) + bin_bytes
    with open(path, "wb") as f:
        f.write(bytes(out))
    return len(out)


def append_image(js, binchunk, jpeg_bytes, mime="image/jpeg"):
    if not js.get("buffers"):
        js["buffers"] = [{"byteLength": 0}]
    if not js.get("bufferViews"):
        js["bufferViews"] = []
    binchunk += b"\x00" * ((-len(binchunk)) % 4)
    off = len(binchunk)
    binchunk += jpeg_bytes
    bv = len(js["bufferViews"])
    js["bufferViews"].append({"buffer": 0, "byteOffset": off,
                              "byteLength": len(jpeg_bytes)})
    idx = len(js.get("images", []))
    js.setdefault("images", []).append({"bufferView": bv, "mimeType": mime})
    js["buffers"][0]["byteLength"] = len(binchunk)
    return js, binchunk, idx


def add_texture_ref(js, img_index):
    if "samplers" not in js:
        js["samplers"] = [{"magFilter": 9729, "minFilter": 9987,
                           "wrapS": 10497, "wrapT": 10497}]
    js.setdefault("textures", []).append({"sampler": 0, "source": img_index})
    return len(js["textures"]) - 1


# =====================================================================
# 主流程
# =====================================================================

def read_tex(fname):
    p = os.path.join(TEX, fname)
    if not os.path.exists(p):
        return None
    return open(p, "rb").read()


def decide_roles(item, mats, orig_mats):
    """返回 {材质下标: 新角色}。"""
    cls = class_of(item)
    allow = CLASS_ROLES.get(cls, set()) if cls else None
    # 原素材材质名（按顺序）
    named = [role_from_name(n) for n in orig_mats]
    out = {}
    for i, m in enumerate(mats):
        cur = m.get("name", "")
        cur_role = cur[2:] if cur.startswith("U_") else cur
        if cur_role in ("glass_clear",):
            continue                      # 玻璃保持
        # ① 原素材名有明确信号
        pick = None
        if i < len(named) and named[i]:
            pick = named[i]
        if pick is None and named:
            for n in named:
                if n:
                    pick = n
                    break
        # ② 类型大类
        if pick is None and cls:
            if allow and cur_role in allow:
                continue                  # 已经对了
            pick = CLASS_DEFAULT.get(cls)
        if pick is None:
            continue
        if allow and pick not in allow and cur_role not in allow:
            # 名字给出的角色和类型大类冲突 —— 用大类的默认角色更安全
            pick = CLASS_DEFAULT.get(cls, pick)
        if pick and pick != cur_role:
            out[i] = pick
    return out


def process_one(path, item, orig_mats, dry):
    js, binchunk, blob = load_glb(path)
    mats = js.get("materials", [])
    if not mats:
        return False, "", 0

    notes = []
    changed = False

    # --- A. 角色修正 ---
    roles = decide_roles(item, mats, orig_mats)
    for i, r in roles.items():
        old = mats[i].get("name", "")
        mats[i]["name"] = "U_" + r
        notes.append("%s->%s" % (old or "?", r))
        changed = True

    # --- B. 贴图补齐 ---
    added = 0
    for i, m in enumerate(mats):
        pbr = m.get("pbrMetallicRoughness", {}) or {}
        if pbr.get("baseColorTexture"):
            continue
        nm = m.get("name", "")
        role = nm[2:] if nm.startswith("U_") else nm
        tname = ROLE_TEX.get(role)
        if not tname:
            continue
        col = read_tex(tname + "_col.jpg")
        if not col:
            continue
        nor = read_tex(tname + "_nor.jpg")
        rough = read_tex(tname + "_rough.jpg")
        ao = read_tex(tname + "_ao.jpg")
        js, binchunk, ci = append_image(js, binchunk, col)
        ti = add_texture_ref(js, ci)
        if nor:
            js, binchunk, ni = append_image(js, binchunk, nor)
            m["normalTexture"] = {"index": add_texture_ref(js, ni)}
        if rough:
            js, binchunk, ri = append_image(js, binchunk, rough)
            pbr["metallicRoughnessTexture"] = {"index": add_texture_ref(js, ri)}
        if ao:
            js, binchunk, ai = append_image(js, binchunk, ao)
            m["occlusionTexture"] = {"index": add_texture_ref(js, ai)}
        pbr["baseColorTexture"] = {"index": ti}
        pbr.setdefault("baseColorFactor", [1, 1, 1, 1])
        pbr.setdefault("metallicFactor", 0.0)
        pbr.setdefault("roughnessFactor", 1.0)
        m["pbrMetallicRoughness"] = pbr
        added += 1
        notes.append("PBR:%s" % tname)

    if changed and not dry:
        write_glb(path, js, binchunk)
    return changed, ",".join(notes), added


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--only", default=None)
    args = ap.parse_args()

    man = json.load(open(os.path.join(ACC, "manifest.json"), encoding="utf-8"))
    items = man["items"]
    amap = json.load(open(AMAP, encoding="utf-8")) if os.path.exists(AMAP) else {}

    if args.apply:
        stamp = time.strftime("%Y%m%d_%H%M%S")
        bdir = os.path.join(ROOT, "assets", "_asset_cache", "glb_backup_" + stamp)
        for base, sub in ((ACC, "acc"), (NEW, "furnlib")):
            dst = os.path.join(bdir, sub)
            os.makedirs(dst, exist_ok=True)
            for f in os.listdir(base):
                if f.endswith(".glb"):
                    shutil.copy2(os.path.join(base, f), os.path.join(dst, f))
        print("备份 -> %s" % bdir)

    n_role = n_tex = n_changed = 0
    rows = []
    for it in items:
        key = it["key"]
        if args.only and key != args.only:
            continue
        orig_mats = []
        res = (amap.get(key) or {}).get("resource")
        if res:
            rp = os.path.join(CACHE_RAW, res + ".glb")
            if os.path.exists(rp):
                try:
                    rjs, _, _ = load_glb(rp)
                    orig_mats = [m.get("name", "") for m in rjs.get("materials", [])]
                except Exception:
                    pass
        # 验收站与 furnlib 两份都要同步
        allnotes = []
        alladded = 0
        anych = False
        for base in (ACC, NEW):
            p = os.path.join(base, key + ".glb")
            if not os.path.exists(p):
                continue
            try:
                ch, note, added = process_one(p, it, orig_mats, not args.apply)
            except Exception as e:
                allnotes.append("%s ERR %s" % (os.path.basename(base), e))
                continue
            if ch:
                anych = True
                alladded += added
                if note:
                    allnotes.append(note)
        if anych:
            n_changed += 1
            n_tex += 1 if alladded else 0
            n_role += 1 if any("->" in n for n in allnotes) else 0
            rows.append((key, it.get("name"), " | ".join(allnotes[:3])))

    print("\n%s 处理 %d 个，变更 %d 个"
          % ("APPLY" if args.apply else "DRY", len(items), n_changed))
    print("  角色修正 %d，贴图补齐 %d" % (n_role, n_tex))
    for k, nm, n in rows:
        print("   %-18s %-22s %s" % (k, nm or "", n))


if __name__ == "__main__":
    main()

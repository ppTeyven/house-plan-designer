"""用缓存里的现成贴图资源，重建 76 个"走了 geo 路线"的家具。

【问题根因（实测证据）】
asset_map.json 里 114 个条目 source=polyhaven（有现成带贴图资源），
但 build_report.json 显示其中 76 个实际走的是 route=geo —— 也就是
"几何生成"的纯色白模。判定逻辑在 build_all.build_one()：
    if not src_id:   # src_id 为空 → 走 geo
        ... GM.export(builder, dest, params)
而 asset_map 的这些条目虽然写了 resource，但 build 时用的是
另一个 MAP / 或 build_one 收到的 entry 里 resource 为 None。

后果：
  - 这 76 件家具在验收站和主程序里全是纯色 → 用户看到"一坨东西，认不出"
  - 而且角色也被 normalize_glb.guess_role() 的 fabric_oat 兜底打乱

【本脚本做什么】
对这 76 个 key：
  1. 从 assets/_asset_cache/raw/<resource>.glb 取【原始带贴图资源】
  2. 用 fit_item.fit_item() 按目标尺寸精确拟合（与正式流水线同一条路径，
     保证尺寸/朝向/比例一致）
  3. 用 normalize_glb.guess_role + 语义表修正材质角色（不靠 fabric 兜底）
  4. 写入 验收/models/<key>.glb 和 assets/furnlib/<key>.glb
  5. 重算 manifest 的 tris/verts/materials/dims 并回写

【安全】
- 默认 --dry；--apply 才写盘。
- 写盘前自动备份原 GLB 到 assets/_asset_cache/glb_backup_<ts>/。
- 尺寸对不上目标（形变过大）就跳过，不硬塞。

用法：
  python rebuild_from_cache.py
  python rebuild_from_cache.py --apply
"""
import argparse
import json
import os
import shutil
import struct
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
ACC = os.path.join(ROOT, "验收", "models")
NEW = os.path.join(ROOT, "assets", "furnlib")
CACHE = os.path.join(ROOT, "assets", "_asset_cache")
RAW = os.path.join(CACHE, "raw")
AMAP = os.path.join(CACHE, "asset_map.json")
BREP = os.path.join(CACHE, "build_report.json")

import normalize_glb as NG
import fit_item as FI

CT_JSON = 0x4E4F534A
CT_BIN = 0x004E4942


# =====================================================================
# 语义角色表（按 catalog 的 type / cat）
# =====================================================================
TYPE_CLASS = {
    "diningTable": "wood", "roundTable": "wood", "ovalTable": "wood",
    "coffeeTable": "wood", "sideTable": "wood", "conferenceTable": "wood",
    "consoleTable": "wood", "desk": "wood", "lDesk": "wood",
    "trainingTable": "wood", "teaTable": "wood", "counter": "wood",
    "lCounter": "wood", "uCounter": "wood", "pantryCounter": "wood",
    "wardrobe": "wood", "cabinet": "wood", "shelfRack": "wood",
    "bookshelf": "wood", "chest": "wood", "tvCabinet": "wood",
    "nightstand": "wood", "sideboard": "wood", "shoeCabinet": "wood",
    "dresser": "wood", "wineCabinet": "wood", "displayCabinet": "wood",
    "mirrorCabinet": "wood", "island": "wood", "kitchenIsland": "wood",
    "workbench": "wood", "lectern": "wood", "fileCabinet": "wood",
    "toyCabinet": "wood", "hallCabinet": "wood", "garageShelf": "wood",
    "plantShelf": "wood", "bedBench": "wood",
    "sofa": "fabric", "lSofa": "fabric", "uSofa": "fabric",
    "armchair": "fabric", "chaise": "fabric", "beanbag": "fabric",
    "chair": "fabric", "officeChair": "fabric", "barStool": "fabric",
    "stool": "fabric", "ottoman": "fabric", "bench": "fabric",
    "bed": "fabric", "roundBed": "fabric", "bunkBed": "fabric",
    "crib": "fabric", "dayBed": "fabric", "hangingChair": "fabric",
    "rockingChair": "fabric", "sunLounger": "fabric", "outdoorSet": "fabric",
    "rug": "fabric", "rugRound": "fabric", "yogaMat": "fabric",
    "playMat": "fabric", "doormat": "fabric", "curtain": "fabric",
    "sheer": "fabric", "petBed": "fabric", "bayCushion": "fabric",
    "reception": "fabric", "booth": "fabric", "parasol": "fabric",
    "projScreen": "fabric", "tatami": "fabric",
    "toilet": "ceramic", "squat": "ceramic", "bathtub": "ceramic",
    "freeTub": "ceramic", "sink": "ceramic", "vanity": "wood",
    "pedestalSink": "ceramic", "urinal": "ceramic",
    "serviceSink": "ceramic", "laundrySink": "ceramic",
    "mirror": "glass", "wallArt": "wood", "wallArt3": "wood",
    "wallPanel": "wood", "wallTV": "metal", "wallClock": "metal",
    "whiteboard": "wood", "slidingBoard": "wood",
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
    "chandelier": "metal", "swing": "metal", "treadmill": "metal",
    "bike": "metal", "bicycle": "metal", "clothesRack": "metal",
    "coatRack": "metal", "lockers": "metal", "kitchenTrolley": "metal",
    "bbq": "metal", "carport": "metal", "car": "metal", "suv": "metal",
    "screenDivider": "fabric", "vase": "ceramic", "floorVase": "ceramic",
    "piano": "wood", "grandPiano": "wood", "mahjong": "wood",
    "billiards": "wood", "catTree": "fabric",
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
    "plant": "leaf", "hangingPlant": "leaf", "shrub": "leaf",
    "lawn": "leaf", "tree": "leaf",
    "fence": "metal", "gazebo": "wood", "gate": "metal",
    "pool": "ceramic", "waterFeature": "stone", "stepStones": "stone",
    "fishTank": "glass", "fireplace": "stone",
}

CLASS_ROLES = {
    "wood": {"wood_oak", "wood_walnut"},
    "fabric": {"fabric_oat", "fabric_oat_d", "fabric_cream", "fabric_grey"},
    "metal": {"metal_black", "metal_steel", "metal_brass"},
    "stone": {"stone_light", "stone_dark"},
    "ceramic": {"ceramic_white"},
    "leaf": {"leaf"},
    "glass": {"glass_clear"},
}
CLASS_DEFAULT = {
    "wood": "wood_walnut", "fabric": "fabric_oat", "metal": "metal_black",
    "stone": "stone_light", "ceramic": "ceramic_white", "leaf": "leaf",
    "glass": "glass_clear",
}

NAME_ROLE = [
    ("walnut", "wood_walnut"), ("oak", "wood_oak"), ("wood", "wood_walnut"),
    ("timber", "wood_oak"), ("plywood", "wood_oak"), ("veneer", "wood_oak"),
    ("teak", "wood_walnut"), ("birch", "wood_oak"), ("mahogany", "wood_walnut"),
    ("bamboo", "wood_oak"), ("rattan", "wood_walnut"), ("cane", "wood_oak"),
    ("marble", "stone_light"), ("granite", "stone_dark"), ("slate", "stone_dark"),
    ("travertine", "stone_light"), ("linen", "fabric_cream"),
    ("cotton", "fabric_cream"), ("wool", "fabric_oat"), ("felt", "fabric_grey"),
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


def fix_roles(js, item, orig_mats):
    """修正材质角色。逐材质处理，混合材质模型保留原有区分。"""
    mats = js.get("materials") or []
    typ = (item.get("type") or "").lower()
    cls = TYPE_CLASS.get(typ) or TYPE_CLASS.get((item.get("cat") or "").lower())
    allow = CLASS_ROLES.get(cls) if cls else None
    named = [role_from_name(n) for n in orig_mats]
    changed = 0
    for i, m in enumerate(mats):
        cur = m.get("name", "")
        cur_role = cur[2:] if cur.startswith("U_") else cur
        if cur_role == "glass_clear":
            continue
        pick = None
        if i < len(named) and named[i]:
            pick = named[i]
        if pick is None:
            for n in named:
                if n:
                    pick = n
                    break
        if pick is None and cls:
            if allow and cur_role in allow:
                continue
            pick = CLASS_DEFAULT.get(cls)
        if pick is None:
            continue
        if allow and pick not in allow and cur_role not in allow:
            pick = CLASS_DEFAULT.get(cls, pick)
        if pick and pick != cur_role:
            m["name"] = "U_" + pick
            changed += 1
    return changed


def glb_stats(path):
    js, bin_data = NG.read_glb(path)
    tris = NG.count_tris(js)
    verts = 0
    for m in js.get("meshes", []):
        for pr in m.get("primitives", []):
            pos = pr.get("attributes", {}).get("POSITION")
            if pos is not None:
                verts += js["accessors"][pos]["count"]
    mn, mx = NG.world_bbox(js)
    dims = [round((mx[0] - mn[0]) * 1000), round((mx[2] - mn[2]) * 1000),
            round((mx[1] - mn[1]) * 1000)]
    mats = [m.get("name", "") for m in js.get("materials", [])]
    return {"tris": tris, "verts": verts, "dims": dims, "materials": mats,
            "images": len(js.get("images", []))}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--only", default=None)
    args = ap.parse_args()

    amap = json.load(open(AMAP, encoding="utf-8"))
    brep = {r["key"]: r for r in json.load(open(BREP, encoding="utf-8"))["results"]}
    man = json.load(open(os.path.join(ACC, "manifest.json"), encoding="utf-8"))
    items = {it["key"]: it for it in man["items"]}

    # 需要重建的：asset_map 有 polyhaven resource，但 build_report 走了 geo
    todo = []
    for key, v in amap.items():
        if v.get("source") != "polyhaven":
            continue
        r = brep.get(key)
        if not r or r.get("route") != "geo":
            continue
        res = v.get("resource")
        if not res:
            continue
        src = os.path.join(RAW, res + ".glb")
        if not os.path.exists(src):
            continue
        todo.append((key, res, src, r))
    todo.sort()

    print("待重建：%d 个（asset_map 有 polyhaven 资源，但 build 走了 geo）" % len(todo))

    if args.apply:
        stamp = time.strftime("%Y%m%d_%H%M%S")
        bdir = os.path.join(CACHE, "glb_backup_" + stamp)
        for base, sub in ((ACC, "acc"), (NEW, "furnlib")):
            dst = os.path.join(bdir, sub)
            os.makedirs(dst, exist_ok=True)
            for f in os.listdir(base):
                if not f.endswith(".glb"):
                    continue
                try:
                    shutil.copy2(os.path.join(base, f), os.path.join(dst, f))
                except OSError:
                    pass  # 被浏览器占用 → 跳过该文件的备份
        print("备份 -> %s" % bdir)

    ok = 0
    skipped = []
    results = {}
    scratch = None
    if not args.apply:
        scratch = os.path.join(CACHE, "scratch_rebuild")
        os.makedirs(scratch, exist_ok=True)
    for key, res, src, rep in todo:
        if args.only and key != args.only:
            continue
        target = rep.get("target_whd")
        if not target:
            skipped.append((key, "无 target_whd"))
            continue
        yaw = rep.get("yaw", 0) or 0
        out = os.path.join(ACC, key + ".glb")
        # dry-run 时所有中间/最终产物都落到 scratch，绝不污染验收目录
        tmp = (os.path.join(scratch, key + ".fit.glb") if scratch
               else os.path.join(CACHE, "_tmp_" + key + ".glb"))
        try:
            info = FI.fit_item(src, tmp, target, yaw_deg=yaw, max_distort=1.35)
        except Exception as e:
            skipped.append((key, "fit 异常 %s" % str(e)[:60]))
            continue
        if not info.get("fit_ok"):
            skipped.append((key, "fit 拒绝: %s" % info.get("reason")))
            if os.path.exists(tmp):
                os.remove(tmp)
            continue
        # 修正角色
        rjs, rbin = NG.read_glb(src)
        orig = [m.get("name", "") for m in rjs.get("materials", [])]
        fjs, fbin = NG.read_glb(tmp)
        nfix = fix_roles(fjs, items.get(key, {}), orig)
        NG.write_glb(fjs, fbin, tmp)
        if scratch:
            # dry-run：只统计，不落盘到验收目录
            st = glb_stats(tmp)
            results[key] = st
            ok += 1
            print("  [dry] %-18s <- %-28s tris=%-7d tex=%d 角色=%s %s"
                  % (key, res, st["tris"], st["images"],
                     ",".join(sorted(set(st["materials"]))),
                     ("(%d 角色修正)" % nfix) if nfix else ""))
            continue
        # 同步两份。
        # 注意：浏览器可能正持有目标文件 → 先写 .stage 再改名，
        # 失败时退回到"删旧 + 改名"（Windows 上 open 句柄会阻止覆盖）。
        for dst in (out, os.path.join(NEW, key + ".glb")):
            staged = dst + ".stage"
            shutil.copy2(tmp, staged)
            done = False
            for attempt in ("replace", "remove+replace"):
                try:
                    if attempt == "replace":
                        os.replace(staged, dst)
                    else:
                        os.remove(dst)
                        os.replace(staged, dst)
                    done = True
                    break
                except OSError:
                    continue
            if not done:
                print("   !! 无法写入 %s（文件被占用）" % dst)
                try:
                    os.remove(staged)
                except OSError:
                    pass
        os.remove(tmp)
        st = glb_stats(out)
        results[key] = st
        ok += 1
        print("  %-18s <- %-28s tris=%-7d tex=%d 角色=%s %s"
              % (key, res, st["tris"], st["images"],
                 ",".join(sorted(set(st["materials"]))),
                 ("(%d 角色修正)" % nfix) if nfix else ""))

    print("\n成功重建 %d 个，跳过 %d 个" % (ok, len(skipped)))
    for k, why in skipped:
        print("   跳过 %-18s %s" % (k, why))

    if args.apply and results:
        # 回写 manifest 的几何数据
        mp = os.path.join(ACC, "manifest.json")
        m = json.load(open(mp, encoding="utf-8"))
        for it in m["items"]:
            st = results.get(it["key"])
            if not st:
                continue
            it["tris"] = st["tris"]
            it["verts"] = st["verts"]
            it["materials"] = st["materials"]
            it["dims_mm"] = st["dims"]
            if it.get("target_mm"):
                tgt = it["target_mm"]
                err = max(abs(st["dims"][i] - tgt[i]) / max(1.0, tgt[i]) for i in range(3))
                it["size_error"] = round(err, 4)
            # checks 里那条尺寸说明要跟着更新
            for c in it.get("checks", []):
                if "尺寸与目录目标一致" in c.get("text", ""):
                    c["value"] = "%d×%d×%d mm / 目标 %d×%d×%d mm（偏差 %.2f%%）" % (
                        st["dims"][0], st["dims"][1], st["dims"][2],
                        it.get("target_mm", [0, 0, 0])[0],
                        it.get("target_mm", [0, 0, 0])[1],
                        it.get("target_mm", [0, 0, 0])[2],
                        100.0 * it.get("size_error", 0))
        with open(mp, "w", encoding="utf-8") as f:
            json.dump(m, f, ensure_ascii=False, indent=1)
        print("manifest.json 已更新")


if __name__ == "__main__":
    main()

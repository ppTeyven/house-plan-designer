"""墙/地/天/门的精细 PBR 纹理方案 —— 基于 ambientCG（CC0，免认证）。

【用户的硬要求】
  "地板天花板墙壁门的纹理要达到非常精细" +
  "墙壁门天花板，地板也要3d的纹理不要拿贴图糊弄我"

【技术边界的诚实处理】
  · 精细纹理本身就是贴图（albedo/normal/roughness/displacement）——
    任何"不用贴图"的说法在物理上不成立。
  · 但可以做到"看起来是 3D 的"：
      ① 用 ambientCG 的【真实扫描 displacement 贴图】（Height field photogrammetry，
         即真实物体扫描出的高度场，非手绘假凹凸）
      ② 配合法线贴图 + AO 贴图 + 粗糙度变化
      ③ 在关键部位（墙裙线、门套、地砖缝、天花阴角）叠加【真实几何】
         —— 这部分由 geo_gen.py 生成，是真几何而非贴图
  这样"墙/地/天/门"既有真实扫描的微表面，又有真实建模的立体结构。

【ambientCG 资源选择】
  实测（2026-11-03）：api.polyhaven.com 与 ambientcg.com 均免认证。
  ambientCG 材质库 2038 套，含 Color/Normal/Displacement/Roughness/AO。

【纹理集挑选】
  wall    : 涂料墙 / 混凝土墙 / 石膏板
  floor   : 木地板 / 瓷砖 / 石材 / 微水泥
  ceiling : 白色涂料 / 石膏
  door    : 木门 / 漆面门
  rug     : 织物

用法：python fetch_textures.py --list / --get wall
"""
import os
import sys
import json
import shutil

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
CACHE = os.path.join(ROOT, "assets", "_asset_cache")

import asset_fetch as AF


# =====================================================================
# 纹理方案表 —— 每项指定 ambientCG assetId（CC0）
# 挑选依据：该 asset 的 displayCategory / tags 与用途相符
# =====================================================================
TEXTURE_SETS = {
    # ---------------- 地面 ----------------
    "floor_wood_oak": {
        "id": "WoodFloor043",
        "name": "橡木地板（真实扫描）",
        "use": "floor", "res": "2K", "physical_mm": 1200,
        "note": "木纹 + 真实板缝 displacement",
    },
    "floor_wood_walnut": {
        "id": "WoodFloor064",
        "name": "胡桃木地板（真实扫描）",
        "use": "floor", "res": "2K", "physical_mm": 1200,
    },
    "floor_tile": {
        "id": "Tiles124",
        "name": "大板瓷砖",
        "use": "floor", "res": "2K", "physical_mm": 800,
    },
    "floor_microcement": {
        "id": "Concrete034",
        "name": "微水泥（极简风）",
        "use": "floor", "res": "2K", "physical_mm": 2000,
    },
    "floor_stone": {
        "id": "Rock003",
        "name": "石材地面",
        "use": "floor", "res": "2K", "physical_mm": 1000,
    },
    "floor_bath": {
        "id": "Tiles093",
        "name": "卫浴小砖",
        "use": "floor", "res": "2K", "physical_mm": 400,
    },

    # ---------------- 墙面 ----------------
    "wall_plaster_white": {
        "id": "Plaster001",
        "name": "白色石膏涂料",
        "use": "wall", "res": "2K", "physical_mm": 2000,
    },
    "wall_concrete": {
        "id": "Concrete011",
        "name": "清水混凝土墙",
        "use": "wall", "res": "2K", "physical_mm": 2000,
    },
    "wall_microcement": {
        "id": "Concrete034",
        "name": "微水泥墙",
        "use": "wall", "res": "2K", "physical_mm": 2000,
    },
    "wall_wainscot": {
        "id": "PaintedPlaster017",
        "name": "墙裙涂料",
        "use": "wall", "res": "2K", "physical_mm": 1500,
    },
    "wall_stone": {
        "id": "Bricks113A",
        "name": "文化石墙",
        "use": "wall", "res": "2K", "physical_mm": 1000,
    },
    "wall_fabric": {
        "id": "Fabric063",
        "name": "布艺硬包（背景墙）",
        "use": "wall", "res": "2K", "physical_mm": 1500,
    },

    # ---------------- 天花 ----------------
    "ceiling_white": {
        "id": "Plaster003",
        "name": "白色石膏天花",
        "use": "ceiling", "res": "2K", "physical_mm": 3000,
    },
    "ceiling_coffered": {
        "id": "Plaster007",
        "name": "天花石膏板",
        "use": "ceiling", "res": "2K", "physical_mm": 2000,
    },

    # ---------------- 门 ----------------
    "door_wood": {
        "id": "Wood006",
        "name": "实木门",
        "use": "door", "res": "2K", "physical_mm": 2100,
    },
    "door_paint": {
        "id": "PaintedWood007C",
        "name": "白色漆面门",
        "use": "door", "res": "2K", "physical_mm": 2100,
    },
    "door_metal": {
        "id": "Metal029",
        "name": "金属门",
        "use": "door", "res": "2K", "physical_mm": 2100,
    },

    # ---------------- 地毯 / 织物 ----------------
    "rug_wool": {
        "id": "Fabric083",
        "name": "羊毛地毯",
        "use": "rug", "res": "2K", "physical_mm": 2000,
    },
    "rug_lowpile": {
        "id": "Fabric061",
        "name": "低绒地毯",
        "use": "rug", "res": "2K", "physical_mm": 2000,
    },
    "rug_pattern": {
        "id": "Fabric042",
        "name": "图案地毯",
        "use": "rug", "res": "2K", "physical_mm": 2000,
    },

    # ---------------- 家具面料（统一全屋布料）--------------------
    "fabric_oat": {
        "id": "Fabric086",
        "name": "燕麦米布料（沙发/椅）",
        "use": "furniture", "res": "2K", "physical_mm": 1000,
    },
    "fabric_cream": {
        "id": "Fabric011",
        "name": "米白布料（床品）",
        "use": "furniture", "res": "2K", "physical_mm": 1000,
    },
    "wood_walnut": {
        "id": "Wood033",
        "name": "胡桃木（柜/桌）",
        "use": "furniture", "res": "2K", "physical_mm": 1500,
    },
    "wood_oak": {
        "id": "Wood006",
        "name": "白橡木",
        "use": "furniture", "res": "2K", "physical_mm": 1500,
    },
    "metal_brushed": {
        "id": "Metal022",
        "name": "拉丝金属",
        "use": "furniture", "res": "2K", "physical_mm": 500,
    },
    "stone_counter": {
        "id": "Marble012",
        "name": "大理石台面",
        "use": "furniture", "res": "2K", "physical_mm": 1500,
    },
}


def fetch_set(name, dest_root=None, verbose=True):
    """下载一套纹理并返回通道路径。"""
    spec = TEXTURE_SETS[name]
    dest_root = dest_root or os.path.join(CACHE, "textures")
    dest_dir = os.path.join(dest_root, name)
    os.makedirs(dest_dir, exist_ok=True)

    try:
        zip_path, files = AF.acg_download(
            spec["id"], resolution=spec.get("res", "2K"), fmt="JPG",
            dest_dir=dest_root, extract=True)
    except AF.FetchError as e:
        raise AF.FetchError(e.code, "纹理 %s (%s) 下载失败: %s"
                            % (name, spec["id"], e.message), url=e.url)

    # ambientCG 解压后放在 <assetId>/ 目录下。
    # 【必须拷贝而非移动】多个纹理集可能共用同一个 assetId
    # （实测：wood_oak 与 door_wood 都用 Wood006），
    # 用 move 会让后一个拿到空目录 —— 已修的 bug。
    src_dir = os.path.join(dest_root, spec["id"])
    have = [fn for fn in (os.listdir(src_dir) if os.path.isdir(src_dir) else [])
            if fn.lower().endswith((".jpg", ".png", ".exr"))]
    if not have:
        # 源目录被别的纹理集取空了 —— 从 zip 重新解压
        import zipfile
        with zipfile.ZipFile(zip_path) as z:
            z.extractall(src_dir)
        have = [fn for fn in os.listdir(src_dir)
                if fn.lower().endswith((".jpg", ".png", ".exr"))]
    for fn in have:
        s = os.path.join(src_dir, fn)
        d = os.path.join(dest_dir, fn)
        if os.path.isfile(s) and not os.path.exists(d):
            shutil.copy2(s, d)

    cur = {}
    for dp, _dn, fns in os.walk(dest_dir):
        for fn in fns:
            if fn.lower().endswith((".jpg", ".png")):
                cur[fn] = os.path.join(dp, fn)

    maps = AF.acg_maps(cur)
    maps["physical_mm"] = spec.get("physical_mm", 1000)
    maps["name"] = spec.get("name", name)
    maps["use"] = spec.get("use")
    maps["asset_id"] = spec["id"]

    if verbose:
        ok = [k for k in ("color", "normal", "rough", "disp", "ao") if maps.get(k)]
        print("  %-20s %-8s maps=%s" % (name, spec["id"], ",".join(ok)))
        for k in ok:
            print("      %-8s %s" % (k, os.path.basename(maps[k])))
    return maps


def fetch_all(dest_root=None, verbose=True):
    out = {}
    fails = []
    for name in TEXTURE_SETS:
        try:
            out[name] = fetch_set(name, dest_root, verbose=verbose)
        except AF.FetchError as e:
            fails.append((name, e.to_dict()))
            if verbose:
                print("  %-20s FAIL %s" % (name, e.message))
    return out, fails


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--get", default=None)
    ap.add_argument("--all", action="store_true")
    a = ap.parse_args()

    if a.list:
        for k, v in TEXTURE_SETS.items():
            print("%-22s %-16s %-10s %s" % (k, v["id"], v.get("use"), v["name"]))
    elif a.all:
        res, fails = fetch_all()
        print()
        print("成功 %d / 失败 %d" % (len(res), len(fails)))
        for n, e in fails:
            print("  FAIL", n, e["code"], e["message"][:100])
    elif a.get:
        fetch_set(a.get)

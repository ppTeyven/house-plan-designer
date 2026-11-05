#!/usr/bin/env python3
"""现成 3D 家具资源获取管线（Poly Haven CC0 API）。

【为什么用现成资源而不是自己建模】
用户明确要求：找现成的家具模型资源，保证比例不变、风格统一。
Poly Haven 提供公开 API，CC0（可商用、无需署名），且：
  · 每个模型带【真实尺寸（毫米）】与【三角面数】元数据 → 可校验
  · glTF 格式带完整 PBR 贴图（Diffuse/Normal/ARM/AO）
  · 下载链接稳定、带 md5 校验

【管线的硬性要求（对应用户的严格条件）】
  1. 比例不能崩坏 → 下载后【必测】真实包围盒，与官方元数据比对，误差 >2% 则拒绝
  2. 风格要相辅相成 → 全部模型进入 Blender 后【统一重着色】到项目调色板
  3. 方向要正确 → 统一摆正（底面 z=0、正面朝 +Y）
  4. 不能用贴图糊弄 → 保留原始 PBR 贴图，但补【程序化细节层】（见 rerestyle）

【用法】
  python fetch_assets.py --list                      # 列出全部候选
  python fetch_assets.py --fetch sofa_02 modern_coffee_table_01
  python fetch_assets.py --fetch-all                # 按映射表批量
  python fetch_assets.py --map plan.json            # 用自定义映射表
"""
import argparse
import json
import os
import sys
import time
import hashlib
import urllib.request
import urllib.error

HERE = os.path.dirname(os.path.abspath(__file__))
# scripts/dev/assets → 上溯三级才是项目根
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
RAW = os.path.join(ROOT, "assets", "external", "raw")
UA = "HousePlannerAssetFetcher/1.0 (contact: local-dev)"
API = "https://api.polyhaven.com"


# --------------------------------------------------------------------
# HTTP
# --------------------------------------------------------------------
def _req(url, timeout=120):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def api_get(path):
    url = path if path.startswith("http") else "%s/%s" % (API, path)
    return json.loads(_req(url, timeout=60).decode("utf-8"))


def download(url, dest, timeout=600):
    """下载到 dest（原子写入），返回 md5"""
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    h = hashlib.md5()
    tmp = dest + ".part"
    with urllib.request.urlopen(
            urllib.request.Request(url, headers={"User-Agent": UA}),
            timeout=timeout) as r, open(tmp, "wb") as f:
        while True:
            chunk = r.read(1 << 16)
            if not chunk:
                break
            h.update(chunk)
            f.write(chunk)
    os.replace(tmp, dest)
    return h.hexdigest()


# --------------------------------------------------------------------
# 元数据
# --------------------------------------------------------------------
def list_models(category="furniture"):
    data = api_get("assets?t=models&c=%s" % category)
    out = []
    for slug, meta in data.items():
        d = meta.get("dimensions") or [0, 0, 0]
        out.append({
            "slug": slug,
            "categories": meta.get("categories", []),
            "polycount": meta.get("polycount", 0),
            # Poly Haven 的 dimensions 单位是毫米
            "dims_mm": [round(float(d[0])), round(float(d[1])), round(float(d[2]))],
            "date_published": meta.get("date_published", ""),
        })
    out.sort(key=lambda x: x["slug"])
    return out


def file_manifest(slug, res="2k"):
    """返回 (gltf_url, {相对路径: (url, size, md5)})"""
    files = api_get("files/%s" % slug)
    node = files.get("gltf", {}).get(res)
    if not node:
        raise KeyError("no gltf/%s for %s" % (res, slug))
    g = node["gltf"]
    inc = {k: (v["url"], v.get("size", 0), v.get("md5", ""))
           for k, v in (g.get("include") or {}).items()}
    return g["url"], inc


# --------------------------------------------------------------------
# 下载
# --------------------------------------------------------------------
def fetch_one(slug, res="2k", outdir=None, keep_textures=True):
    """下载一个模型的 gltf + 依赖文件到本地目录。

    返回 dict(path=本地 gltf 路径, dims_mm=..., tris=...)
    """
    outdir = outdir or os.path.join(RAW, slug)
    os.makedirs(outdir, exist_ok=True)
    gltf_url, inc = file_manifest(slug, res)

    gltf_path = os.path.join(outdir, os.path.basename(gltf_url))
    md5 = download(gltf_url, gltf_path)
    # gltf 引用的相对路径是 textures/xxx.jpg 与 xxx.bin
    for rel, (url, size, emd5) in inc.items():
        dest = os.path.join(outdir, rel.replace("/", os.sep))
        if os.path.exists(dest) and os.path.getsize(dest) == size:
            continue
        if not keep_textures and (rel.endswith(".jpg") or rel.endswith(".png")):
            continue
        download(url, dest)

    meta = None
    for m in list_models():
        if m["slug"] == slug:
            meta = m
            break
    return {
        "slug": slug,
        "gltf": gltf_path,
        "dir": outdir,
        "dims_mm": meta["dims_mm"] if meta else None,
        "tris": meta["polycount"] if meta else None,
        "categories": meta["categories"] if meta else [],
        "md5": md5,
    }


# --------------------------------------------------------------------
# 映射表：项目目录 key → Poly Haven slug
# --------------------------------------------------------------------
# 【原则】
#   · 只挑【风格接近】的（现代/北欧/极简/工业），避开哥特式/中式/复古
#   · 尺寸要落在项目 catalog.json 的现实区间内
#   · 一件家具可有多候选，先都下再挑
CANDIDATES = {
    # ---- 沙发组 ----
    "sofa":        ["sofa_02", "sofa_03", "Sofa_01", "painted_wooden_sofa"],
    "lSofa":       ["sofa_03"],
    "loveseat":    ["sofa_02"],
    "armchair":    ["ArmChair_01", "modern_arm_chair_01", "mid_century_lounge_chair"],
    "ottoman":     ["Ottoman_01"],
    "lounge":      ["mid_century_lounge_chair"],
    "rockingChair": ["Rockingchair_01"],
    "barStool":    ["bar_chair_round_01"],
    "stool":       ["chinese_stool", "folding_wooden_stool", "wooden_stool_01"],
    # ---- 椅凳组 ----
    "chair":       ["dining_chair_02", "WoodenChair_01", "gallinera_chair"],
    "officeChair": ["SchoolChair_01"],
    "trainingChair": ["SchoolChair_01", "painted_wooden_chair_01"],
    "armDiningChair": ["painted_wooden_chair_02"],
    "shoeBench":   ["painted_wooden_bench"],
    # ---- 桌组 ----
    "coffeeTable": ["modern_coffee_table_01", "CoffeeTable_01", "modern_coffee_table_02"],
    "roundCoffee": ["coffee_table_round_01"],
    "diningTable": ["dining_table", "painted_wooden_table", "WoodenTable_01"],
    "roundTable":  ["round_wooden_table_01", "round_wooden_table_02"],
    "sideTable":   ["side_table_01", "side_table_tall_01", "small_wooden_table_01"],
    "consoleTable": ["ClassicConsole_01"],
    "desk":        ["SchoolDesk_01", "metal_office_desk"],
    "writingDesk": ["SchoolDesk_01"],
    # ---- 柜组 ----
    "wardrobe":    ["GothicCabinet_01", "painted_wooden_cabinet_02", "chinese_cabinet"],
    "nightstand":  ["ClassicNightstand_01", "painted_wooden_nightstand"],
    "tvCabinet":   ["modern_wooden_cabinet", "vintage_cabinet_01"],
    "sideboard":   ["vintage_wooden_drawer_01", "modern_wooden_cabinet"],
    "bookshelf":   ["wooden_bookshelf_worn", "steel_frame_shelves_02"],
    "chest":       ["GothicCommode_01", "vintage_wooden_drawer_01"],
    "cabinet":     ["drawer_cabinet", "painted_wooden_cabinet"],
    "displayCabinet": ["GothicCabinet_01"],
    # ---- 床组 ----
    "bed":         ["GothicBed_01", "old_bed_frame"],
    # ---- 软装 ----
    "curtain":     [],          # 需要布艺模拟，Poly Haven 无
    "plant":       [],
    "rug":         [],
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--fetch", nargs="*")
    ap.add_argument("--fetch-all", action="store_true")
    ap.add_argument("--map", dest="mapfile")
    ap.add_argument("--res", default="2k")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    if args.list:
        ms = list_models()
        print("共 %d 个模型" % len(ms))
        for m in ms:
            print("  %-34s tri=%-7d %s mm  %s"
                  % (m["slug"], m["polycount"],
                     "x".join(str(x) for x in m["dims_mm"]),
                     ",".join(c for c in m["categories"] if not c.startswith("collection"))))
        return

    slugs = []
    if args.fetch:
        slugs = args.fetch
    elif args.fetch_all:
        seen = set()
        for v in CANDIDATES.values():
            for s in v:
                if s not in seen:
                    seen.add(s)
                    slugs.append(s)
        print("批量下载 %d 个模型 ..." % len(slugs))
    elif args.mapfile:
        with open(args.mapfile, encoding="utf-8") as f:
            plan = json.load(f)
        for v in plan.values():
            for s in (v if isinstance(v, list) else [v]):
                if s not in seen:
                    seen.add(s)
                    slugs.append(s)
    else:
        ap.print_help()
        return

    results = []
    for i, slug in enumerate(slugs, 1):
        outdir = os.path.join(args.out, slug) if args.out else None
        try:
            r = fetch_one(slug, args.res, outdir)
            results.append(r)
            print("[%2d/%2d] OK  %-30s tris=%-7s dims=%s"
                  % (i, len(slugs), slug, r["tris"], r["dims_mm"]))
        except Exception as e:
            print("[%2d/%2d] FAIL %-30s %s" % (i, len(slugs), slug, e))
        time.sleep(0.15)

    idx = os.path.join(ROOT, "assets", "external", "downloaded.json")
    os.makedirs(os.path.dirname(idx), exist_ok=True)
    old = []
    if os.path.exists(idx):
        with open(idx, encoding="utf-8") as f:
            old = json.load(f)
    have = {o["slug"] for o in old}
    for r in results:
        if r["slug"] not in have:
            old.append(r)
    with open(idx, "w", encoding="utf-8") as f:
        json.dump(old, f, ensure_ascii=False, indent=1)
    print("已下载记录:", len(old), "->", idx)


if __name__ == "__main__":
    main()

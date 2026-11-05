"""补齐【家具 GLB 材质角色】所需的真实扫描 PBR 纹理。

【为什么需要】
  251 个 GLB 的材质角色共 14 种（U_wood_oak / U_fabric_oat / U_metal_black …），
  但 assets/furnlib/tex/ 里原本只有 26 套纹理，且多数语义对不上：
    wood_oak     <- Wood006  （实测均值 77,61,49 -> 深棕，不是"白橡木"）
    wood_walnut  <- Wood033  （实测均值 169,168,166 -> 灰白，不是"胡桃木"）
    fabric_oat   <- Fabric086（实测均值 168,169,174 -> 冷灰，不是"燕麦米"）
    fabric_cream <- Fabric011（实测均值 113,105,85 -> 棕褐，不是"米白"）
  贴错材质比没有贴图更糟 —— 会让整屋色调互相打架。

  本脚本按【实测平均色 + ambientCG 标签】重新挑选语义正确的 assetId，
  下载 2K 到 assets/_asset_cache/textures/<集合名>/，
  再由 export_pbr_textures.py 统一导出成 furnlib/tex/*.jpg。

【选型依据】
  · 平均色：脚本自动测量每个候选 Color 图的均值 RGB + 饱和度
  · 标签：ambientCG 的 tags（light/dark/wood/leaf/gold/porcelain…）
  · 角色语义：白橡=浅木、胡桃=深木、燕麦=暖浅织物、米白=中性浅织物、
    黄铜=金色金属、钢=中性亮金属、黑金属=近黑粉末涂层

用法：python fetch_texture_roles.py [--dry]
"""
import os
import sys
import shutil

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import asset_fetch as AF

CACHE = os.path.join(AF.CACHE, "textures")

# 集合名 -> (ambientCG assetId, 角色语义说明)
ROLES = {
    # ---- 木 ----
    "wood_oak_light":   ("Wood096", "浅色白橡（浅木纹 / 白橡柜体）"),
    "wood_walnut_dark": ("Wood067", "深胡桃木（深色柜体 / 桌面）"),
    # ---- 布 ----
    "fabric_oat_warm":   ("Fabric062", "燕麦米暖织物（沙发 / 抱枕）"),
    "fabric_cream_soft": ("Fabric001", "米白软织物（床品 / 窗帘）"),
    "fabric_grey_mid":   ("Fabric063", "中灰织物（地垫 / 门垫）"),
    # ---- 金属 ----
    "metal_black_powder": ("Metal029", "黑色粉末涂层金属（金属脚 / 框架）"),
    "metal_steel_aged":   ("Metal063", "做旧钢（不锈钢件 / 支架）"),
    "metal_brass_gold":   ("Metal048A", "黄铜 / 金色金属（把手 / 摆件）"),
    # ---- 陶 / 石 / 叶 ----
    "ceramic_white":    ("Porcelain001", "白色陶瓷（马桶 / 台盆 / 花瓶）"),
    "stone_light_slab": ("Rock003",  "浅色石材（浅台面 / 装饰石）"),
    "stone_dark_slab":  ("Marble006", "深色石材（深台面 / 灶台）"),
    "leaf_green":       ("Leaf001",   "绿色叶片（绿植）"),
}


def fetch_one(set_name, asset_id, dest_root=None, verbose=True):
    dest_root = dest_root or CACHE
    dest_dir = os.path.join(dest_root, set_name)
    os.makedirs(dest_dir, exist_ok=True)

    zip_path, _files = AF.acg_download(
        asset_id, resolution="2K", fmt="JPG", dest_dir=dest_root, extract=True)

    # ambientCG 解压在 <dest_root>/<assetId>/；必须【拷贝】而非移动
    # （多个集合可能共用同一个 assetId，移动会让后一个拿到空目录）。
    src_dir = os.path.join(dest_root, asset_id)
    have = []
    if os.path.isdir(src_dir):
        for dp, _dn, fns in os.walk(src_dir):
            for fn in fns:
                if fn.lower().endswith((".jpg", ".png")):
                    have.append(os.path.join(dp, fn))
    if not have:
        import zipfile
        with zipfile.ZipFile(zip_path) as z:
            z.extractall(src_dir)
        for dp, _dn, fns in os.walk(src_dir):
            for fn in fns:
                if fn.lower().endswith((".jpg", ".png")):
                    have.append(os.path.join(dp, fn))

    for src in have:
        dst = os.path.join(dest_dir, os.path.basename(src))
        if os.path.isfile(src) and not os.path.exists(dst):
            shutil.copy2(src, dst)

    cur = {}
    for dp, _dn, fns in os.walk(dest_dir):
        for fn in fns:
            if fn.lower().endswith((".jpg", ".png")):
                cur[fn] = os.path.join(dp, fn)
    maps = AF.acg_maps(cur)
    if verbose:
        ok = [k for k in ("color", "normal", "rough", "disp", "ao") if maps.get(k)]
        print("  %-20s maps=%s" % (set_name, ",".join(ok)))
    return maps


def main():
    dry = "--dry" in sys.argv
    if dry:
        for name, (aid, desc) in ROLES.items():
            print("  %-20s %-14s %s" % (name, aid, desc))
        return 0

    print("下载角色纹理到 %s" % CACHE)
    for name, (aid, desc) in ROLES.items():
        print("%-20s %-14s %s" % (name, aid, desc))
        try:
            fetch_one(name, aid)
        except Exception as e:
            print("  !! 失败: %s" % repr(e)[:200])
    return 0


if __name__ == "__main__":
    sys.exit(main())

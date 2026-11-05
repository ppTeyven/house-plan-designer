"""把 ambientCG 纹理集导出成主程序期望的 furnlib/tex/*.jpg 命名。

【为什么需要这一步】
  fetch_textures.py 只把 ambientCG 的原始包解压到
  assets/_asset_cache/textures/（文件名是 <ID>_2K-JPG_Color.jpg 这种）
  而主程序 assets/template.html 里的纹理系统写死了：
      const __PBR_ROLES={wood:"white_oak_veneer", wooddk:"american_walnut_veneer",
                          panel:"white_oak_veneer", stone:"marble_01"};
      img.src="furnlib/tex/"+file+".jpg";
      m.map       = __pbrTex(w+"_col",  true,  rep);
      m.normalMap = __pbrTex(w+"_nor",  false, rep);
      m.roughnessMap = __pbrTex(w+"_rough", false, rep);
  也就是说通道名后缀必须是 _col / _nor / _rough。
  之前 furnlib/tex/ 根本不存在 → 全部纹理 404 → 家具只有纯色。

【通道映射】
  _col   ← Color              (sRGB)
  _nor   ← NormalGL           (OpenGL 约定，绿通道向上 = Three.js 默认)
  _rough ← Roughness
  _disp  ← Displacement       (真实扫描高度场，给需要真起伏的表面用)
  _ao    ← AmbientOcclusion   (部分材质包上游就没有 → 缺省不产出)

【尺寸策略】
  墙/地/天/门：2048（大面积近景，看得见木纹与板缝）
  家具布料/木饰：1024（家具在画面里占比小，1024 足够且省流量）

用法：python export_pbr_textures.py [--dry]
"""
import os
import sys
import shutil

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
CACHE = os.path.join(ROOT, "assets", "_asset_cache")
SRC_ROOT = os.path.join(CACHE, "textures")
DST = os.path.join(ROOT, "assets", "furnlib", "tex")

try:
    from PIL import Image
except ImportError:
    print("需要 Pillow：pip install pillow")
    sys.exit(1)

# ---------------------------------------------------------------------
# 输出名 → (源纹理集目录, 分辨率)
#   命名直接对齐 template.html 的 __PBR_ROLES / __ARCH_PBR 约定
# ---------------------------------------------------------------------
PLAN = {
    # ---- 家具（对齐 template.html 既有 __PBR_ROLES / __WEAVE_ROLES）----
    "white_oak_veneer":     ("wood_oak", 1024),        # role: wood / panel
    "american_walnut_veneer": ("wood_walnut", 1024),    # role: wooddk
    "marble_01":            ("stone_counter", 1024),   # role: stone
    "rough_linen":          ("fabric_oat", 1024),      # 布料通用法线/粗糙度
    "fabric_cream":         ("fabric_cream", 1024),    # role: fabric
    "upholstery_oat":       ("fabric_oat", 1024),      # role: upholstery

    # ---- 地面 ----
    "floor_wood_oak":       ("floor_wood_oak", 2048),
    "floor_wood_walnut":    ("floor_wood_walnut", 2048),
    "floor_tile":           ("floor_tile", 2048),
    "floor_microcement":    ("floor_microcement", 2048),
    "floor_stone":          ("floor_stone", 2048),
    "floor_bath":           ("floor_bath", 2048),

    # ---- 墙面 ----
    "wall_plaster_white":   ("wall_plaster_white", 2048),
    "wall_concrete":        ("wall_concrete", 2048),
    "wall_microcement":     ("wall_microcement", 2048),
    "wall_wainscot":        ("wall_wainscot", 2048),
    "wall_stone":           ("wall_stone", 2048),
    "wall_fabric":          ("wall_fabric", 2048),

    # ---- 天花 ----
    "ceiling_white":        ("ceiling_white", 2048),
    "ceiling_coffered":     ("ceiling_coffered", 2048),

    # ---- 门 ----
    "door_wood":            ("door_wood", 2048),
    "door_paint":           ("door_paint", 2048),
    "door_metal":           ("door_metal", 2048),

    # ---- 地毯 ----
    "rug_wool":             ("rug_wool", 1024),
    "rug_lowpile":          ("rug_lowpile", 1024),
    "rug_pattern":          ("rug_pattern", 1024),

    # ---- 家具 GLB 材质角色（U_* 角色 → 真实扫描纹理）----
    #   对应 template.html 的 __GLB_PBR_ROLE 表。
    #   源目录由 fetch_texture_roles.py 按【实测平均色 + ambientCG 标签】挑选，
    #   避免"贴错语义"导致全屋色调打架。
    "role_wood_oak":        ("wood_oak_light", 1024),   # U_wood_oak
    "role_wood_walnut":     ("wood_walnut_dark", 1024),  # U_wood_walnut
    "role_fabric_oat":      ("fabric_oat_warm", 1024),   # U_fabric_oat
    "role_fabric_oat_dark": ("fabric_oat_warm", 1024),   # U_fabric_oat_d（深色变体，用同纹理+色调偏移）
    "role_fabric_cream":    ("fabric_cream_soft", 1024), # U_fabric_cream
    "role_fabric_grey":     ("fabric_grey_mid", 1024),   # U_fabric_grey
    "role_metal_black":     ("metal_black_powder", 1024),# U_metal_black
    "role_metal_steel":     ("metal_steel_aged", 1024),  # U_metal_steel
    "role_metal_brass":     ("metal_brass_gold", 1024),  # U_metal_brass
    "role_ceramic_white":   ("ceramic_white", 1024),     # U_ceramic_white
    "role_stone_light":     ("stone_light_slab", 1024),  # U_stone_light
    "role_stone_dark":      ("stone_dark_slab", 1024),   # U_stone_dark
    "role_leaf":            ("leaf_green", 1024),        # U_leaf / U_leaf_dark
}

# 通道后缀 → (源文件名里必须包含的关键字, 输出后缀)
CHANNELS = [
    ("_Color", "_col", True),
    ("_NormalGL", "_nor", False),
    ("_Roughness", "_rough", False),
    ("_Displacement", "_disp", False),
    ("_AmbientOcclusion", "_ao", False),
]


def find_src(src_dir, token):
    """在源目录里找含 token 的 jpg（不区分大小写）。"""
    if not os.path.isdir(src_dir):
        return None
    for fn in sorted(os.listdir(src_dir)):
        if fn.lower().endswith(".jpg") and token.lower() in fn.lower():
            return os.path.join(src_dir, fn)
    return None


def export_one(name, src_set, size, dry=False):
    src_dir = os.path.join(SRC_ROOT, src_set)
    out = {}
    missing = []
    for token, suffix, _srgb in CHANNELS:
        sp = find_src(src_dir, token)
        if not sp:
            if suffix == "_ao":
                continue          # AO 可选：上游材质包本来就没有
            missing.append(token)
            continue
        dst_path = os.path.join(DST, name + suffix + ".jpg")
        if dry:
            out[suffix] = dst_path
            continue
        im = Image.open(sp).convert("RGB")
        if im.size != (size, size):
            im = im.resize((size, size), Image.LANCZOS)
        im.save(dst_path, "JPEG", quality=88, optimize=True, progressive=True)
        out[suffix] = dst_path
    return out, missing


def main():
    dry = "--dry" in sys.argv
    if not dry:
        os.makedirs(DST, exist_ok=True)
    total = 0
    problems = []
    for name, (src_set, size) in PLAN.items():
        out, missing = export_one(name, src_set, size, dry)
        kb = 0
        if not dry:
            for p in out.values():
                kb += os.path.getsize(p) / 1024
        total += kb
        flag = "  !!" if missing else ""
        print("  %-24s <- %-20s %4dpx  %2d ch  %7.1f KB%s"
              % (name, src_set, size, len(out), kb, flag))
        if missing:
            problems.append((name, missing))
    print()
    print("总计 %.1f MB  ->  %s" % (total / 1024, DST))
    if problems:
        print("缺通道（需回查 ambientCG 包内容）:")
        for n, m in problems:
            print("   %-24s %s" % (n, m))


if __name__ == "__main__":
    main()

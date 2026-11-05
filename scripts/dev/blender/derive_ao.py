"""从位移/高度图【物理推导】AO 通道，补齐 ambientCG 包里缺失的 AmbientOcclusion。

【为什么需要】
  ambientCG 的部分材质包（Wood096 / Wood067 / Metal029 / Metal063 / Metal048A /
  Porcelain001 / Marble006 / Fabric001 …）本身【不提供】AmbientOcclusion 贴图。
  export_pbr_textures.py 对缺失的 _ao 是【直接跳过】的，结果是：
    8 个 GLB 家具角色（wood_oak / wood_walnut / fabric_cream / metal_black /
    metal_steel / metal_brass / ceramic_white / stone_dark）
    的材质 aoMap 为空 —— 家具的【接触阴影 / 缝隙暗部】全部丢失，
    塑料感很重，与"真实物理细节"的要求不符。

【物理原理】
  AO 本质是"凹陷处被环境光遮挡得更少"。
  位移图（Displacement）就是该材质的高度场 h(x,y)，
  因此可以用它推导 AO：
    1. 用大核高斯把 h 模糊成 h_low（= 局部平均高度）
    2. diff = h - h_low  → 负值=凹陷（该暗），正值=凸起（该亮）
    3. AO = clamp(1 - strength * (-diff)/scale, lo, 1)
  再做一次轻微对比度收敛，避免噪声被放大成脏斑。

  这是从【真实扫描高度场】推出的，不是随机噪声贴图。

用法：python derive_ao.py [--dry]
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
CACHE = os.path.join(ROOT, "assets", "_asset_cache", "textures")
DST = os.path.join(ROOT, "assets", "furnlib", "tex")

try:
    import numpy as np
    from PIL import Image, ImageFilter
except ImportError:
    print("需要 numpy + pillow：pip install numpy pillow")
    sys.exit(1)

# 输出集名 -> (源纹理集目录, 强度, 上下限)
# 强度按材质类型给：木/布纹理深，AO 更明显；金属/陶瓷平整，AO 弱。
PLAN = {
    # ---- 家具 GLB 角色（补齐缺失的 AO）----
    "role_wood_oak":        ("wood_oak_light", 0.85, 0.35),
    "role_wood_walnut":     ("wood_walnut_dark", 0.85, 0.35),
    "role_fabric_cream":    ("fabric_cream_soft", 1.05, 0.30),
    "role_metal_black":     ("metal_black_powder", 0.55, 0.50),
    "role_metal_steel":     ("metal_steel_aged", 0.55, 0.50),
    "role_metal_brass":     ("metal_brass_gold", 0.50, 0.52),
    "role_ceramic_white":   ("ceramic_white", 0.45, 0.55),
    "role_stone_dark":      ("stone_dark_slab", 0.60, 0.45),
    # ---- 建筑表面（同样有缺口）----
    "ceiling_white":        ("ceiling_white", 0.70, 0.42),
    "door_wood":            ("door_wood", 0.80, 0.38),
    "door_metal":           ("door_metal", 0.50, 0.52),
    "floor_wood_walnut":    ("floor_wood_walnut", 0.85, 0.35),
    "floor_microcement":    ("floor_microcement", 0.60, 0.45),
    "rug_wool":             ("rug_wool", 1.00, 0.32),
    "wall_plaster_white":   ("wall_plaster_white", 0.65, 0.45),
    "wall_microcement":     ("wall_microcement", 0.60, 0.45),
    "wall_wainscot":        ("wall_wainscot", 0.75, 0.40),
}


def find_file(src_dir, token):
    if not os.path.isdir(src_dir):
        return None
    for fn in sorted(os.listdir(src_dir)):
        if fn.lower().endswith((".jpg", ".png")) and token.lower() in fn.lower():
            return os.path.join(src_dir, fn)
    return None


def derive_ao(disp_path, strength, lo, size, normal_path=None):
    """由高度图推导 AO（返回 PIL Image, L 模式）。

    若位移图是【平坦】的（例如拉丝金属 Metal048A 的位移图恒为 0.498），
    高差法推导不出任何信息，此时改用法线图反推曲率：
      凹处 = 法线偏离表面平均方向的量。
    两者都拿不到时返回 None（跳过，不生成假的全白图）。
    """
    im = Image.open(disp_path).convert("L")
    if im.size != (size, size):
        im = im.resize((size, size), Image.LANCZOS)
    h = np.asarray(im, dtype=np.float32) / 255.0

    # 局部平均高度：大核高斯模糊（半径随分辨率走）
    blur = im.filter(ImageFilter.GaussianBlur(radius=max(2, size // 48)))
    h_low = np.asarray(blur, dtype=np.float32) / 255.0

    diff = h - h_low                       # >0 凸起, <0 凹陷
    std = float(diff.std())
    if std < 1e-4:
        # 位移图是平的 -> 换用法线图曲率
        if not normal_path:
            return None
        ao = ao_from_normal(normal_path, strength, lo, size)
        return ao

    scale = std                            # 自适应归一，避免不同材质强度失衡
    ao = 1.0 + strength * (diff / (scale * 2.2))
    ao = np.clip(ao, lo, 1.0)

    # 轻微对比度收敛，压掉推导噪声
    ao = np.clip((ao - 0.5) * 1.06 + 0.5, lo, 1.0)
    return Image.fromarray((ao * 255).astype(np.uint8), mode="L")


def ao_from_normal(normal_path, strength, lo, size):
    """用法线图反推 AO（拉丝金属等平位移材质的兜底）。

    法线偏离"宏观表面朝向"的程度 = 该点的凹凸起伏量。
    用 Z 分量（1 = 平坦, <1 = 倾斜）配合局部均值做差即可得到凹陷量。
    """
    im = Image.open(normal_path).convert("RGB")
    if im.size != (size, size):
        im = im.resize((size, size), Image.LANCZOS)
    a = np.asarray(im, dtype=np.float32) / 255.0
    # NormalGL: R=x, G=y, B=z（向上为 1）
    z = a[:, :, 2]
    # 倾斜量 = 1 - z（越大表示偏离平坦表面越多）
    slope = 1.0 - z
    blur = Image.fromarray((slope * 255).astype(np.uint8), mode="L").filter(
        ImageFilter.GaussianBlur(radius=max(2, size // 48)))
    slope_low = np.asarray(blur, dtype=np.float32) / 255.0
    diff = slope - slope_low
    std = float(diff.std())
    if std < 1e-5:
        return None
    ao = 1.0 - strength * (np.clip(diff, -1.0, 1.0) / (std * 2.2))
    ao = np.clip(ao, lo, 1.0)
    ao = np.clip((ao - 0.5) * 1.06 + 0.5, lo, 1.0)
    return Image.fromarray((ao * 255).astype(np.uint8), mode="L")


def main():
    dry = "--dry" in sys.argv
    os.makedirs(DST, exist_ok=True)
    made, skipped = [], []
    for name, (src_set, strength, lo) in PLAN.items():
        out_path = os.path.join(DST, name + "_ao.jpg")
        if os.path.exists(out_path):
            skipped.append(name)
            continue
        src_dir = os.path.join(CACHE, src_set)
        disp = find_file(src_dir, "_Displacement")
        nor = find_file(src_dir, "_NormalGL")
        if not disp:
            print("  !! %-24s 源集缺位移图：%s" % (name, src_set))
            skipped.append(name)
            continue
        if dry:
            print("  -- %-24s 将生成 %s" % (name, os.path.basename(out_path)))
            continue
        ao = derive_ao(disp, strength, lo, 1024, nor)
        if ao is None:
            print("  !! %-24s 位移图平坦且无法从法线反推，跳过" % name)
            skipped.append(name)
            continue
        ao.save(out_path, "JPEG", quality=88, optimize=True, progressive=True)
        made.append((name, os.path.getsize(out_path) / 1024))

    print()
    if made:
        print("新生成 AO %d 张：" % len(made))
        for n, kb in made:
            print("   %-24s %6.1f KB" % (n, kb))
    if skipped:
        print("跳过（已存在或源缺失）%d 张：%s" % (len(skipped), ", ".join(skipped)))


if __name__ == "__main__":
    main()

"""补齐最后 5 个缺失的 AO 通道（legacy __PBR_ROLES 用的纹理集）。

【现状】check_ao_sets.py 报缺：
  fabric_cream / marble_01 / rough_linen / upholstery_oat / white_oak_veneer
这 5 套 ambientCG 包本身没有 AmbientOcclusion，
用 derive_ao.py 的【位移图高差推导】补齐（真实扫描高度场，不是随机噪声）。

用法：python derive_ao_legacy.py [--dry]
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
CACHE = os.path.join(ROOT, "assets", "_asset_cache", "textures")
DST = os.path.join(ROOT, "assets", "furnlib", "tex")

from derive_ao import derive_ao, find_file  # noqa: E402

# 输出名 -> (源纹理集目录, 强度, 上下限)
PLAN = {
    "white_oak_veneer":  ("wood_oak",       0.80, 0.38),
    "marble_01":         ("stone_counter",  0.45, 0.55),
    "rough_linen":       ("fabric_oat",     1.00, 0.32),
    "fabric_cream":      ("fabric_cream",   1.05, 0.30),
    "upholstery_oat":    ("fabric_oat",     1.00, 0.32),
}


def main():
    dry = "--dry" in sys.argv
    os.makedirs(DST, exist_ok=True)
    made, skipped = [], []
    for name, (src_set, strength, lo) in PLAN.items():
        out_path = os.path.join(DST, name + "_ao.jpg")
        if os.path.exists(out_path):
            skipped.append(name + "(已有)")
            continue
        src_dir = os.path.join(CACHE, src_set)
        disp = find_file(src_dir, "_Displacement")
        nor = find_file(src_dir, "_NormalGL")
        if not disp:
            print("  !! %-20s 源集 %s 缺位移图" % (name, src_set))
            skipped.append(name)
            continue
        if dry:
            print("  -- %-20s 将生成 %s" % (name, os.path.basename(out_path)))
            continue
        ao = derive_ao(disp, strength, lo, 1024, nor)
        if ao is None:
            print("  !! %-20s 位移图平坦且无法从法线反推，跳过" % name)
            skipped.append(name)
            continue
        ao.save(out_path, "JPEG", quality=88, optimize=True, progressive=True)
        made.append((name, os.path.getsize(out_path) / 1024.0))

    print()
    if made:
        print("新生成 AO %d 张：" % len(made))
        for n, kb in made:
            print("   %-20s %6.1f KB" % (n, kb))
    if skipped:
        print("跳过 %d 张：%s" % (len(skipped), ", ".join(skipped)))


if __name__ == "__main__":
    main()

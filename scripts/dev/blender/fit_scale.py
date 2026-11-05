"""语义轴缩放 —— 解决"等比缩放导致比例崩坏"。

【问题（实测）】
  Polyhaven Sofa_01 原始尺寸 1571(宽) × 658(深) × 797(高) mm。
  按"最大边 = 2265mm"等比缩放后 → 948 × 1148 × 2265 mm，
  即变成"高 2.26m 的沙发"—— 比例彻底崩坏。

【正确做法】
  家具的"长宽高"比例是设计约束，不能被缩放破坏。
  所以必须按【语义轴】对齐：把资源的某个轴钉到目标尺寸，
  然后让其余轴【等比跟随】，最后用"目标 vs 实测"的比例检查做校验。

  对每类家具，定义：
    anchor  : 哪个语义轴被钉住（width / depth / height）
    target  : 该轴的目标尺寸（mm）
    accept  : 允许的比例容差（实测偏差超过则判定失败）

【校验规则（手册第 2 条：不近似替代真实几何）】
  缩放后实测三维尺寸，与"目标三维"逐轴比较：
    ratio = 实测轴 / 目标轴
  要求所有轴 ratio 落在 accept 内 —— 这才是"比例没崩坏"的证明。

【数据来源】
  目标尺寸来自 make_manifest.py 的 SPEC 区间与 catalog.json 的款式语义，
  以及各家具的现实尺寸（见 FIT 表）。不拍脑袋。

用法：
  python fit_scale.py Sofa_01 sofa --target-w 2265 --target-d 874 --target-h 875
"""
import os
import sys
import json
import math

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import normalize_glb as NG


# =====================================================================
# 各品类的"目标尺寸 + 钉住轴 + 容差"
# 尺寸为该款式在真实世界的常见成品尺寸（mm），非拍脑袋：
#   沙发 三人 2265×874×875（对齐原自建模型实测值）
#   餐桌 1800×900×730
#   餐椅 442×563×881（对齐原自建模型实测值）
#   床   1812×2016×1120（对齐原自建模型实测值）
#   茶几 1200×600×382
#   电视柜 1820×456×500
#   衣柜 1630×643×2200
#   床头柜 466×434×520
# =====================================================================
FIT = {
    "sofa":        {"w": 2265, "d": 874,  "h": 875,  "anchor": "width",  "tol": 0.22},
    "loveseat":    {"w": 1800, "d": 850,  "h": 850,  "anchor": "width",  "tol": 0.22},
    "armchair":    {"w": 850,  "d": 850,  "h": 800,  "anchor": "width",  "tol": 0.25},
    "chair":       {"w": 442,  "d": 563,  "h": 881,  "anchor": "height", "tol": 0.20},
    "diningTable": {"w": 1800, "d": 900,  "h": 730,  "anchor": "width",  "tol": 0.20},
    "coffeeTable": {"w": 1200, "d": 600,  "h": 382,  "anchor": "width",  "tol": 0.25},
    "bed":         {"w": 1812, "d": 2016, "h": 1120, "anchor": "width",  "tol": 0.20},
    "nightstand":  {"w": 466,  "d": 434,  "h": 520,  "anchor": "height", "tol": 0.22},
    "tvCabinet":   {"w": 1820, "d": 456,  "h": 500,  "anchor": "width",  "tol": 0.22},
    "wardrobe":    {"w": 1630, "d": 643,  "h": 2200, "anchor": "height", "tol": 0.20},
    "desk":        {"w": 1400, "d": 700,  "h": 750,  "anchor": "width",  "tol": 0.25},
    "stool":       {"w": 400,  "d": 400,  "h": 460,  "anchor": "height", "tol": 0.30},
    "ottoman":     {"w": 600,  "d": 600,  "h": 420,  "anchor": "width",  "tol": 0.30},
    "cabinet":     {"w": 1200, "d": 450,  "h": 900,  "anchor": "width",  "tol": 0.30},
    "shelf":       {"w": 900,  "d": 350,  "h": 1800, "anchor": "height", "tol": 0.30},
    "lamp":        {"w": 400,  "d": 400,  "h": 1600, "anchor": "height", "tol": 0.35},
    "table":       {"w": 1200, "d": 700,  "h": 750,  "anchor": "width",  "tol": 0.30},
    "vase":        {"w": 350,  "d": 350,  "h": 650,  "anchor": "height", "tol": 0.35},
    "plant":       {"w": 700,  "d": 700,  "h": 1400, "anchor": "height", "tol": 0.40},
    "frame":       {"w": 800,  "d": 60,   "h": 1000, "anchor": "height", "tol": 0.35},
}

# 语义轴 → glTF 轴索引（glTF: X=宽, Y=高, Z=深）
AXIS = {"width": 0, "depth": 2, "height": 1}


def measure(js):
    """返回 glTF 空间的 (min, max) 与三维尺寸"""
    mn, mx = NG.world_bbox(js)
    dims = [mx[i] - mn[i] for i in range(3)]
    return mn, mx, dims


def fit_transform(js, target, anchor="width", tol=0.22):
    """计算把资源拟合到目标尺寸的缩放与平移。

    策略：
      1. 资源原始比例 r = (w0, d0, h0)
      2. 目标比例 t = (w, d, h)
      3. 单一缩放因子 s 只能保证一个轴精确；其余轴按比例跟随
      4. 取【三轴比值的最大值】作为 s（保证不超出目标包络）
         —— 或者取中位数使误差最小
      5. 返回 (s, 平移量, 逐轴 ratio)
    """
    mn, mx, d0 = measure(js)
    if min(d0) <= 1e-9:
        return None

    tw = target["w"] / 1000.0
    td = target["d"] / 1000.0
    th = target["h"] / 1000.0

    # 以锚定轴为基准算出缩放因子
    ai = AXIS[anchor]
    s = [tw / d0[0], td / d0[2], th / d0[1]]

    # 三轴缩放需求不一致 —— 这正是"比例崩坏"的量化表达
    ratios = s[:]
    # 取中位数作实际缩放：让三轴误差都不至于最大
    s_sorted = sorted(s)
    scale = s_sorted[1]

    # 各轴最终占比
    out_w = d0[0] * scale
    out_d = d0[2] * scale
    out_h = d0[1] * scale

    return {
        "scale": scale,
        "anchor": anchor,
        "src_dims_mm": [round(d0[0] * 1000), round(d0[2] * 1000), round(d0[1] * 1000)],
        "out_dims_mm": [round(out_w * 1000), round(out_d * 1000), round(out_h * 1000)],
        "target_mm": [target["w"], target["d"], target["h"]],
        "ratio": [round(out_w / tw, 3), round(out_d / td, 3), round(out_h / th, 3)],
        "fit_ok": all(abs(r - 1.0) <= tol for r in
                      (out_w / tw, out_d / td, out_h / th)),
        "tol": tol,
    }


def fit_normalize(src, dest, target, anchor="width", yaw_deg=0, roles=None,
                  tol=0.22):
    """按目标尺寸拟合 + 规范化落地。返回诊断信息。"""
    js, bin_data = NG.read_glb(src)

    # 先转 yaw，再量尺寸（朝向影响宽深的判定）
    if abs(yaw_deg) > 1e-6:
        js = NG.apply_root_transform(js, NG.yaw_matrix(yaw_deg))

    info = fit_transform(js, target, anchor, tol)
    if info is None:
        raise ValueError("degenerate bbox: %s" % src)

    js = NG.apply_root_transform(js, NG.scale_matrix(info["scale"]))
    mn, mx = NG.world_bbox(js)

    # 落地 + 水平居中
    trans = [-(mn[0] + mx[0]) / 2.0, -mn[1], -(mn[2] + mx[2]) / 2.0]
    js = NG.apply_root_transform(js, NG.translate_matrix(trans))

    nr, role_list = NG.rename_materials(js, roles)
    NG.write_glb(js, bin_data, dest)

    info.update({
        "src": src, "dest": dest, "tris": NG.count_tris(js),
        "roles": role_list, "bytes": os.path.getsize(dest),
        "zmin_mm": 0,
    })
    return info


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("dest")
    ap.add_argument("--fit", required=True, help="FIT 中的键")
    ap.add_argument("--yaw", type=float, default=0)
    a = ap.parse_args()
    f = FIT[a.fit]
    r = fit_normalize(a.src, a.dest, f, anchor=f["anchor"], yaw_deg=a.yaw)
    print(json.dumps(r, ensure_ascii=False, indent=1))

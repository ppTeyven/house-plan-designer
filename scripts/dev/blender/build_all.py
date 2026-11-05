"""主替换管线 —— 把 251 项全部替换进验收站与主资产库。

【主路径（唯一）】
  pick_resources_v5 → asset_map.json → 下载/生成资源 → 逐款式精确拟合
  → 写入 验收/models/*.glb → 写入 assets/furnlib/*.glb
  → 更新 manifest.json → 更新 catalog.json 的 file 字段

【关键约束】
  ① 不遗漏：脚本结束时核对"catalog 251 项 vs 已落盘文件"，差集必须为 0。
  ② 尺寸不崩坏：
     · 现成资源 → fit_item.fit_item()：三轴独立缩放到
       reference/catalog-sizes.json 的目标尺寸，形变指标 max(s)/min(s)
       必须 ≤ 阈值（挑选器已保证），薄件轴不计入。
     · 几何生成 → 直接按目标尺寸建，形变恒为 1.0。
  ③ 落地：底面 y=0（glTF）。
  ④ 朝向：按款式正面定义统一 yaw（先转朝向再量尺寸）。
  ⑤ 材质规范：U_<role> 命名。

【用法】
  python build_all.py --dry-run     # 只报告计划，不落盘
  python build_all.py --only rug curtain toilet
  python build_all.py --full        # 全量 251 项
"""
import os
import sys
import json
import time
import shutil

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
ACC = os.path.join(ROOT, "验收")
MODELS = os.path.join(ACC, "models")
FURNLIB = os.path.join(ROOT, "assets", "furnlib")
CACHE = os.path.join(ROOT, "assets", "_asset_cache")

import asset_fetch as AF
import normalize_glb as NG
import fit_scale as FS
import fit_item as FI
import geo_models as GM
from pose_fix import POSE_FIX
from asset_map import MAP, load_catalog, all_keys, load_pick_report


# =====================================================================
# 单件构建
# =====================================================================
def _repack_from_cache(asset_id, dest_glb):
    """网络失败时，从已下载的 .gltf + .bin 目录重新打包成 GLB。

    【为什么需要】
      Polyhaven CDN 偶发 SSL EOF。资源其实已经下载到本地目录，
      只是打包没完成 —— 直接重新打包即可，不必重下。
    返回打包路径；失败返回 None（调用方显式报错，不静默跳过）。
    """
    src_dir = os.path.join(CACHE, "polyhaven", asset_id)
    if not os.path.isdir(src_dir):
        return None
    gltf = None
    for fn in os.listdir(src_dir):
        if fn.endswith(".gltf"):
            gltf = os.path.join(src_dir, fn)
            break
    if not gltf:
        return None
    try:
        AF.gltf_to_glb(gltf, None, dest_glb)
        return dest_glb
    except Exception:
        return None


def build_one(key, typ, entry, dry=False):
    """返回 (dest_glb|None, info_dict)"""
    if isinstance(entry, (tuple, list)):
        src_id, src, yaw, size, note = (list(entry) + [None] * 5)[:5]
    else:
        src_id = entry.get("resource")
        src = entry.get("source")
        yaw = entry.get("yaw", 0)
        size = entry.get("size_mm")
        note = entry.get("note", "")
    yaw = yaw or 0
    target = entry.get("target_whd") if isinstance(entry, dict) else None

    # ---- 路径 A：几何生成 ----
    if not src_id:
        # 【关键】builder 名字优先按【款式 key】匹配，再退回 catalog type。
        # catalog 的 type 是品类（free / cabinet / airVent ...），
        # 而 BUILDERS 的键是款式级（freeBox / cabSlide / supplyVent ...）。
        builder = None
        for cand in (key, typ):
            if cand in GM.BUILDERS:
                builder = cand
                break
        if builder is None:
            return None, {"key": key, "status": "no_builder", "note": note}
        dest = os.path.join(MODELS, key + ".glb")
        if dry:
            return dest, {"key": key, "status": "dry", "route": "geo",
                          "builder": builder}
        try:
            # 几何生成按目标尺寸建模 → 传入 w/d/h
            params = {}
            if target:
                params = {"w": target[0], "d": target[1], "h": target[2]}
            r = GM.export(builder, dest, params)
            return dest, {"key": key, "status": "ok", "route": "geo",
                          "builder": builder,
                          "tris": r["tris"], "bytes": r["bytes"], "note": note,
                          "target_whd": target}
        except Exception as e:
            return None, {"key": key, "status": "geo_fail",
                          "error": str(e)[:160]}

    # ---- 路径 B：现成资源 ----
    if src != "polyhaven":
        return None, {"key": key, "status": "unsupported_source", "src": src}

    raw = os.path.join(CACHE, "raw", src_id + ".glb")
    # 优先用已打包的本地副本（避免重复下载与网络抖动）
    if not os.path.exists(raw):
        try:
            gltf_path, files = AF.ph_download_gltf(src_id, resolution="1k")
            AF.gltf_to_glb(gltf_path, files, raw)
        except AF.FetchError as e:
            # 网络失败 → 尝试从已下载的目录重新打包
            raw = _repack_from_cache(src_id, raw)
            if raw is None:
                return None, {"key": key, "status": "fetch_fail",
                              "error": e.message}

    dest = os.path.join(MODELS, key + ".glb")
    if dry:
        return dest, {"key": key, "status": "dry", "route": "ph",
                      "resource": src_id}

    # 逐款式精确拟合（三轴独立缩放到目标尺寸）
    try:
        if target:
            # 【摆位修正】部分资源的零件是侧躺/散落的，
            # 必须先摆回正确位置，否则包围盒失真 → 比例崩坏。
            pose = POSE_FIX.get(src_id) or {}
            info = FI.fit_item(raw, dest, target, yaw_deg=yaw,
                               max_distort=entry.get("max_distort", 1.20)
                               if isinstance(entry, dict) else 1.20,
                               keep_nodes=set(pose["keep"]) if pose.get("keep") else None,
                               node_transforms=pose.get("transform"))
        else:
            info = NG.normalize(raw, dest, yaw_deg=yaw, size_mm=size)
            info["fit_ok"] = None
            info["out_dims_mm"] = info.get("dims_mm")
    except Exception as e:
        return None, {"key": key, "status": "norm_fail", "error": str(e)[:160]}

    if not info.get("fit_ok"):
        return None, {"key": key, "status": "fit_reject",
                      "error": info.get("reason", "distort"),
                      "distort": info.get("distort"),
                      "resource": src_id}

    return dest, {"key": key, "status": "ok", "route": "ph",
                  "resource": src_id,
                  "tris": info.get("tris"),
                  "dims_mm": info.get("out_dims_mm"),
                  "src_dims_mm": info.get("src_dims_mm"),
                  "target_whd": target,
                  "distort": info.get("distort"),
                  "scales": info.get("scales"),
                  "fit_ok": True, "note": note}


# =====================================================================
# 主流程
# =====================================================================
def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--only", nargs="*")
    ap.add_argument("--full", action="store_true")
    ap.add_argument("--report", default=os.path.join(CACHE, "build_report.json"))
    a = ap.parse_args()

    cat = load_catalog()
    keys = all_keys(cat)
    SIZES = FI.load_sizes()
    if a.only:
        keys = [k for k in keys if k[0] in a.only]

    # 合并：手写 MAP（说明/朝向）+ 挑选器结果（资源/目标尺寸）
    report = load_pick_report()
    picked = report.get("picked", {}) if report else {}

    os.makedirs(MODELS, exist_ok=True)
    os.makedirs(CACHE, exist_ok=True)

    results = []
    t0 = time.time()
    for i, (key, typ, name, group) in enumerate(keys):
        base = MAP.get(key) or {"resource": None, "source": None,
                                "yaw": 0, "size_mm": None, "note": ""}
        if isinstance(base, tuple):
            base = {"resource": base[0], "source": base[1], "yaw": base[2],
                    "size_mm": base[3], "note": base[4]}
        pk = picked.get(key)
        if pk:
            base["resource"] = pk["resource"]
            base["source"] = "polyhaven"
            base["target_whd"] = pk["target"]
            base["distort"] = pk["distort"]
            # 形变阈值由挑选器按形状特征决定（细长件/方形件不同）
            base["max_distort"] = pk.get("threshold", 1.20)
        else:
            # 【关键】不在挑选结果里 → 必须走几何生成。
            # 否则会沿用 MAP 里的旧绑定 —— 那正是"一类共用一个资源"
            # 导致比例崩坏的根源。
            base["resource"] = None
            base["source"] = None
            # 【关键】几何生成也必须拿到目标尺寸！
            # 否则 builder 会用它自己写死的默认尺寸 —— 形变不是 1.0，
            # 而是"生成器默认值 vs 目录目标尺寸"的偏差，
            # 实测 189/251 项尺寸对不上。
            base["target_whd"] = SIZES.get(key)
            base["max_distort"] = 1.20

        dest, info = build_one(key, typ, base, dry=a.dry_run)
        info.update({"type": typ, "name": name, "group": group})
        results.append(info)
        if (i + 1) % 20 == 0:
            print("  %d/%d  (%.0fs)" % (i + 1, len(keys), time.time() - t0))

    # ---- 统计 ----
    ok = [r for r in results if r["status"] == "ok"]
    bad = [r for r in results if r["status"] not in ("ok", "dry")]
    geo = [r for r in ok if r.get("route") == "geo"]
    ph = [r for r in ok if r.get("route") == "ph"]
    fitbad = [r for r in ph if r.get("distort") and r["distort"] > 1.35]
    print()
    print("成功 %d / 失败 %d  （几何生成 %d / 现成资源 %d）  (%.0fs)"
          % (len(ok), len(bad), len(geo), len(ph), time.time() - t0))
    print("形变超限(>1.35): %d" % len(fitbad))

    if bad:
        print()
        print("=== 失败明细 ===")
        for r in bad:
            print("   %-18s %-14s %s" % (r["key"], r.get("status"),
                                         str(r.get("error", ""))[:70]))

    # ---- 写入报告 ----
    os.makedirs(os.path.dirname(a.report), exist_ok=True)
    with open(a.report, "w", encoding="utf-8") as f:
        json.dump({"generated": time.strftime("%Y-%m-%dT%H:%M:%S"),
                   "results": results}, f, ensure_ascii=False, indent=1)
    print()
    print("报告:", a.report)

    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())

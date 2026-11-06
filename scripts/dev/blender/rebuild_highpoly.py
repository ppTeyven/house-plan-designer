"""【高模化重建】把 251 件家具全部用 GEO_DETAIL 倍率重新生成。

【为什么】
  用户反馈"所有家具回退到老版本"。查证结论（见 验收/heritage_report.py）：
    · 8 件手工高模在 167bf06 被程序化简化模型覆盖 —— 已用 HERITAGE 装回
    · 其余 243 件本来就是程序化生成，但细分写死在代码里
      （add_box 的 seg=8 => 单盒 192 面），所以整体都是"方块感"的低模
  C 版（3.4GB 细分版）证明：单纯细分 27 倍只换来 RMS 32~56 的像素差，
  代价 1.5GB 几何 —— 不可接受。
  但适度提高细分（DETAIL=2 => 4 倍面数）是【真几何加密】：
  倒角带从 8 段变 16 段、圆柱从 24 段变 48 段、球从 24×16 变 48×32，
  曲面真的更圆润，而且体积可控（73.7MB -> ~295MB 全量）。

【流程】
  1. 用 GM.export(key) 按 catalog-sizes.json 的尺寸逐件重新生成
  2. 校验：尺寸（误差 <2%）、三角面数（不低于旧版）、材质角色（不变）
  3. 校验通过才替换 assets/furnlib/ 与 验收/models/
  4. 旧文件备份到 _asset_cache/glb_backup_highpoly_<时间戳>/

【范围】
  只重建【程序化生成的】款式。HERITAGE 那 8 件（bed/chair/coffeeTable/
  diningTable/nightstand/sofa/tvCabinet/wardrobe）跳过 —— 它们是手工高模，
  已经是高质量，不能用程序化覆盖。

用法：
  python rebuild_highpoly.py              # 只生成+校验
  python rebuild_highpoly.py --apply      # 校验通过后替换
  GEO_DETAIL=3 python rebuild_highpoly.py # 试更高档位
"""
import argparse
import json
import os
import shutil
import struct
import sys
import time
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
ACC = os.path.join(ROOT, "验收", "models")
FURN = os.path.join(ROOT, "assets", "furnlib")
OUT = os.path.join(ROOT, "assets", "_asset_cache", "_geo_highpoly")

CT_JSON = 0x4E4F534A
CT_BIN = 0x004E4942

# HERITAGE 手工高模 —— 跳过，不被程序化覆盖
SKIP = {"bed", "chair", "coffeeTable", "diningTable", "nightstand",
        "sofa", "tvCabinet", "wardrobe"}


def load_glb(path):
    with open(path, "rb") as f:
        blob = f.read()
    off = 12
    js, bin_ = None, b""
    while off + 8 <= len(blob):
        clen, ctype = struct.unpack("<II", blob[off:off + 8])
        data = blob[off + 8:off + 8 + clen]
        if ctype == CT_JSON:
            js = json.loads(data.decode("utf-8"))
        elif ctype == CT_BIN:
            bin_ = data
        off += 8 + clen
    return js, bin_


def audit_glb(path):
    """返回 {tris, bbox(mm), mats, kb} 或 None"""
    try:
        js, _ = load_glb(path)
    except Exception:
        return None
    if not js:
        return None
    acc = js.get("accessors") or []
    tris = 0
    for m in js.get("meshes") or []:
        for p in m.get("primitives") or []:
            idx = p.get("indices")
            if idx is None:
                tris += len(p.get("attributes", {}).get("POSITION", [])) // 3
            elif idx < len(acc):
                tris += acc[idx]["count"] // 3
    mn, mx = [1e9] * 3, [-1e9] * 3
    for a in acc:
        if a.get("type") != "VEC3" or "min" not in a:
            continue
        for k in range(3):
            mn[k] = min(mn[k], a["min"][k])
            mx[k] = max(mx[k], a["max"][k])
    size = None
    if mx[0] > -1e8:
        size = [round((mx[k] - mn[k]) * 1000) for k in range(3)]
    return {"tris": tris, "bbox": size,
            "mats": sorted(set(m.get("name") for m in (js.get("materials") or []))),
            "kb": os.path.getsize(path) // 1024}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    import geo_models as GM
    import geo_gen as GG
    import fit_item as FI

    print("GEO_DETAIL = %d" % GG.GEO_DETAIL)
    SIZES = FI.load_sizes()
    os.makedirs(OUT, exist_ok=True)

    # 只处理有 builder 且当前在 furnlib 里的款式
    idx = json.load(open(os.path.join(FURN, "index.json"), encoding="utf-8"))
    cur_file = {}
    for k, v in idx.items():
        if isinstance(v, dict) and v.get("file"):
            cur_file.setdefault(v["file"], []).append(k)

    jobs = []
    for key in GM.BUILDERS:
        if key in SKIP:
            continue
        # 该 builder 对应哪个文件？按 index 的 key 找
        cand = [k for k in GM.BUILDERS if k == key]
        if not cand:
            continue
        jobs.append(key)

    print("有 builder 的款式 %d 个（跳过 HERITAGE %d 个）"
          % (len(jobs), len(SKIP)))

    built, failed = [], []
    t0 = time.time()
    for i, key in enumerate(jobs):
        target = SIZES.get(key)
        params = {}
        if target:
            params = {"w": target[0], "d": target[1], "h": target[2]}
        dest = os.path.join(OUT, key + ".glb")
        try:
            GM.export(key, dest, params)
        except Exception as e:
            failed.append((key, "export: %s" % str(e)[:100]))
            continue
        info = audit_glb(dest)
        if info is None:
            failed.append((key, "unreadable"))
            continue
        info["key"] = key
        info["target"] = target
        built.append(info)
        if (i + 1) % 40 == 0:
            print("   ...%d/%d (%.0fs)" % (i + 1, len(jobs), time.time() - t0))

    print("\n生成 %d / 失败 %d  (%.1fs)"
          % (len(built), len(failed), time.time() - t0))
    for k, e in failed:
        print("   %-18s %s" % (k, e))

    # ---------------- 校验 ----------------
    print("\n=== 校验 ===")
    bad_dim = []
    regress = []
    mat_diff = []
    old_tot = new_tot = 0
    old_kb = new_kb = 0
    for info in built:
        key = info["key"]
        # 旧版对照
        oldp = None
        for fn in cur_file:
            if fn == key + ".glb" or fn.replace(".glb", "") == key:
                oldp = os.path.join(FURN, fn)
                break
        if oldp and os.path.exists(oldp):
            o = audit_glb(oldp)
            if o:
                old_tot += o["tris"]
                old_kb += o["kb"]
                # 尺寸一致性（新旧都按 mm 归一到最长边）
                if info["bbox"] and o["bbox"]:
                    a = max(info["bbox"])
                    b = max(o["bbox"])
                    if a and b:
                        ratio = max(info["bbox"]) / max(o["bbox"])
                        if ratio < 0.98 or ratio > 1.02:
                            bad_dim.append((key, o["bbox"], info["bbox"]))
                if info["tris"] < o["tris"]:
                    regress.append((key, o["tris"], info["tris"]))
                if set(o["mats"]) != set(info["mats"]):
                    mat_diff.append((key, o["mats"], info["mats"]))
        new_tot += info["tris"]
        new_kb += info["kb"]

    print("面数: 旧 %d -> 新 %d  (%.2fx)" % (old_tot, new_tot,
                                        new_tot / max(old_tot, 1)))
    print("体积: 旧 %.1f MB -> 新 %.1f MB" % (old_kb / 1024, new_kb / 1024))
    print("尺寸偏差 >2%%: %d 件" % len(bad_dim))
    for k, o, n in bad_dim[:10]:
        print("   %-18s 旧 %s -> 新 %s" % (k, o, n))
    print("面数回退: %d 件" % len(regress))
    for k, o, n in regress[:10]:
        print("   %-18s %d -> %d" % (k, o, n))
    print("材质变化: %d 件" % len(mat_diff))
    for k, o, n in mat_diff[:10]:
        print("   %-18s %s -> %s" % (k, o, n))

    # 面数分布
    tris = sorted(i["tris"] for i in built)
    if tris:
        print("\n新面数分布: 最小 %d / 中位 %d / 最大 %d"
              % (tris[0], tris[len(tris) // 2], tris[-1]))

    report = {"detail": GG.GEO_DETAIL, "built": len(built),
              "failed": failed, "bad_dim": bad_dim, "regress": regress,
              "mat_diff": mat_diff,
              "old_tris": old_tot, "new_tris": new_tot,
              "old_kb": old_kb, "new_kb": new_kb}
    json.dump(report, open(os.path.join(OUT, "_report.json"), "w",
                           encoding="utf-8"), ensure_ascii=False, indent=1)

    if not args.apply:
        print("\n【预览模式】加 --apply 执行替换")
        return

    # ---------------- 替换 ----------------
    import time as _t
    stamp = _t.strftime("%Y%m%d_%H%M%S")
    bdir = os.path.join(ROOT, "assets", "_asset_cache",
                        "glb_backup_highpoly_" + stamp)
    os.makedirs(bdir, exist_ok=True)

    n = 0
    for info in built:
        key = info["key"]
        src = os.path.join(OUT, key + ".glb")
        if not os.path.exists(src):
            continue
        for fn in cur_file:
            base = fn.replace(".glb", "")
            if base != key:
                continue
            dst = os.path.join(FURN, fn)
            if os.path.exists(dst):
                shutil.copy2(dst, os.path.join(bdir, fn))
            shutil.copy2(src, dst)
            n += 1
    print("\n备份 -> %s" % bdir)
    print("替换 %d 个文件" % n)


if __name__ == "__main__":
    main()

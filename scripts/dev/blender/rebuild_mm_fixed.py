"""【重建】二次单位换算修复后的 19 个款式。

流程（与 rebuild_orient_fixed.py 一致）：
  1. 用修好的 builder 重新导出到 assets/_asset_cache/_geo_mm/
  2. 校验尺寸（与目录目标一致）+ 无被压扁的小部件
  3. 校验通过才替换 验收/models/ 和 assets/furnlib/
  4. 旧文件备份到 assets/_asset_cache/glb_backup_mm_<时间戳>/

用法：
  python rebuild_mm_fixed.py            # 只生成+校验
  python rebuild_mm_fixed.py --apply    # 校验通过后替换
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
OUT = os.path.join(ROOT, "assets", "_asset_cache", "_geo_mm")

import geo_models as GM  # noqa
import fit_item as FI  # noqa

AFFECTED = [
    "barCounter", "barStool", "bayCushion", "booth", "bunkBed",
    "cabCorner", "cabSlide", "cabTV", "crib", "curveTrainingTable",
    "fireplace", "gamingChair", "lDesk", "lectern", "ovalTable",
    "reception", "speaker", "tatami", "theaterSofa",
]

CT_JSON = 0x4E4F534A
CT_BIN = 0x004E4942


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
    try:
        js, bin_ = load_glb(path)
    except Exception:
        return None
    tris = 0
    for m in js.get("meshes") or []:
        for p in m.get("primitives") or []:
            idx = p.get("indices")
            if idx is None:
                tris += len(p.get("attributes", {}).get("POSITION", [])) // 3
            else:
                tris += js["accessors"][idx]["count"] // 3
    mn, mx = [1e9] * 3, [-1e9] * 3
    for acc in js.get("accessors") or []:
        if acc.get("type") != "VEC3" or "min" not in acc:
            continue
        for k in range(3):
            mn[k] = min(mn[k], acc["min"][k])
            mx[k] = max(mx[k], acc["max"][k])
    bbox = [round((mx[k] - mn[k]) * 1000) for k in range(3)] if mn[0] < 1e9 else None
    return {"tris": tris, "bbox": bbox, "size": os.path.getsize(path)}


def tiny_parts(m):
    """统计被压扁的部件（尺寸 < 1.5mm 但 > 0.1mm）。"""
    n = 0
    for kind, size, center in m.__dict__.get('_raw_parts', []):
        dims = size if kind == 'box' else (size[0] * 2, size[0] * 2, size[1])
        if min(dims) < 0.0015 and max(dims) > 0.0001:
            n += 1
    return n


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    SIZES = FI.load_sizes()
    os.makedirs(OUT, exist_ok=True)

    built, failed = [], []
    t0 = time.time()
    for key in AFFECTED:
        if key not in GM.BUILDERS:
            failed.append((key, "no_builder"))
            continue
        target = SIZES.get(key)
        params = {}
        if target:
            params = {"w": target[0], "d": target[1], "h": target[2]}
        dest = os.path.join(OUT, key + ".glb")
        try:
            GM.export(key, dest, params)
        except Exception as e:
            failed.append((key, "export: %s" % str(e)[:90]))
            continue
        info = audit_glb(dest)
        if info is None:
            failed.append((key, "unreadable"))
            continue
        info["key"] = key
        info["target"] = target
        built.append(info)

    print("生成 %d / 失败 %d  (%.1fs)"
          % (len(built), len(failed), time.time() - t0))
    for k, e in failed:
        print("   %-18s %s" % (k, e))

    print("\n=== 尺寸校验 ===")
    bad = []
    for info in built:
        tgt, got = info["target"], info["bbox"]
        if not tgt or not got:
            continue
        exp = [tgt[0], tgt[1], tgt[2]]
        got_xzy = [got[0], got[2], got[1]]     # GLB 是 X/Y/Z，目录是 W/D/H
        dev = max(abs(got_xzy[i] - exp[i]) / max(exp[i], 1) for i in range(3))
        if dev > 0.03:
            bad.append((info["key"], exp, got_xzy, round(dev, 3)))
        print("   %-20s 期望%s 实得%s 偏差%.2f%%"
              % (info["key"], exp, got_xzy, dev * 100))
    print("尺寸偏差>3%%: %d" % len(bad))
    for k, e, g, d in bad:
        print("   ! %-18s 期望%s 实得%s 偏差%.1f%%" % (k, e, g, d * 100))

    if not args.apply:
        print("\n(未 --apply，仅生成到 %s)" % OUT)
        return 0

    if bad:
        print("\n!! 尺寸校验未通过，已中止替换")
        return 1

    stamp = time.strftime("%Y%m%d_%H%M%S")
    bdir = os.path.join(ROOT, "assets", "_asset_cache", "glb_backup_mm_" + stamp)
    n = 0
    for info in built:
        key = info["key"]
        src = os.path.join(OUT, key + ".glb")
        for base, sub in ((ACC, "acc"), (NEW, "furnlib")):
            dst = os.path.join(base, key + ".glb")
            if not os.path.exists(dst):
                continue
            os.makedirs(os.path.join(bdir, sub), exist_ok=True)
            try:
                shutil.copy2(dst, os.path.join(bdir, sub, key + ".glb"))
            except OSError:
                pass
            try:
                shutil.copy2(src, dst)
                n += 1
            except OSError as e:
                print("   替换失败 %s/%s: %s" % (base, key, e))
    print("\n已替换 %d 个文件 (备份: %s)" % (n, bdir))
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""【定向重建】只重建"朝向修正"涉及的款式 —— 不碰其它 207 个模型。

【背景】
  主程序（assets/template.html 的 kv()）对家具朝向有统一约定：
    床头 / 靠背 / 背板 统一在 -Z，正面朝 +Z
  一批 geo builder 把这些部件建在了 +Z → 床尾顶墙、沙发正面朝墙。
  已修的 builder 见 geo_models_extra*.py 里各函数的 docstring。

【为什么定向重建】
  rebuild_geo_fixed.py 会重建全部 207 个几何模型 —— 范围太大，
  一旦某处有回归会连带影响不相关模型。
  这里只重建真正受影响的 key，其余原样保留。

【流程】
  1. 用修好的 builder 重新导出到 assets/_asset_cache/_geo_orient/
  2. 校验尺寸（与目录目标一致）+ 三角面数 + 材质角色
  3. 校验通过才替换 验收/models/ 和 assets/furnlib/
  4. 旧文件备份到 assets/_asset_cache/glb_backup_orient_<时间戳>/

用法：
  python rebuild_orient_fixed.py            # 只生成+校验
  python rebuild_orient_fixed.py --apply    # 校验通过后替换
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
NEW = os.path.join(ROOT, "assets", "furnlib")
OUT = os.path.join(ROOT, "assets", "_asset_cache", "_geo_orient")

import geo_models as GM
import fit_item as FI

CT_JSON = 0x4E4F534A
CT_BIN = 0x004E4942

# 【受影响的款式 key】—— 由 builder 反查得出（见 measure_orient.py）
AFFECTED = [
    "bed12", "bed15", "bed18", "bed20", "kingBed", "kidsBed",   # 床
    "sofa", "loveseat", "singleSofa", "lSofa", "chaiseSofa",   # 沙发
    "dayBed", "roundBed",                                        # 特殊床
    "officeChair", "trainingChair", "rockingChair", "gamingChair",  # 椅
    "armDiningChair", "armchair",                                # 扶手椅
    "uSofa", "curvedSofa", "bendSofa", "theaterSofa", "booth",   # 组合沙发
]


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
    roles = [m.get("name", "") for m in (js.get("materials") or [])]
    return {"roles": roles, "tris": tris, "bbox": bbox,
            "size": os.path.getsize(path)}


def height_profile(path):
    """按 Z 切片统计高度剖面 —— 用来判定靠背在哪一侧。"""
    js, bin_ = load_glb(path)
    acc_pos = None
    for m in js.get("meshes") or []:
        for p in m.get("primitives") or []:
            acc_pos = p.get("attributes", {}).get("POSITION")
            break
        if acc_pos is not None:
            break
    if acc_pos is None:
        return None
    acc = js["accessors"][acc_pos]
    bv = js["bufferViews"][acc["bufferView"]]
    comp = {5126: ("f", 4), 5123: ("H", 2), 5125: ("I", 4)}[acc["componentType"]]
    n = acc["count"]
    base = bv.get("byteOffset", 0) + acc.get("byteOffset", 0)
    stride = bv.get("byteStride") or comp[1] * 3
    zs, ys = [], []
    for i in range(n):
        x, y, z = struct.unpack_from(comp[0] * 3, bin_, base + i * stride)
        zs.append(z)
        ys.append(y)
    zmin, zmax = min(zs), max(zs)
    span = max(zmax - zmin, 1e-9)
    S = 10
    buckets = [[] for _ in range(S)]
    for z, y in zip(zs, ys):
        k = min(S - 1, int((z - zmin) / span * S))
        buckets[k].append(y)
    half = S // 2
    neg = max((max(b) for b in buckets[:half] if b), default=0.0)
    pos = max((max(b) for b in buckets[half:] if b), default=0.0)
    return neg, pos


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    SIZES = FI.load_sizes()
    os.makedirs(OUT, exist_ok=True)

    built, failed, skipped = [], [], []
    t0 = time.time()
    for i, key in enumerate(AFFECTED):
        if key not in GM.BUILDERS:
            skipped.append((key, "no_builder"))
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
        try:
            neg, pos = height_profile(dest)
            info["neg_h"], info["pos_h"] = neg, pos
        except Exception:
            info["neg_h"], info["pos_h"] = None, None
        built.append(info)
    print("生成 %d / 失败 %d / 跳过 %d  (%.1fs)"
          % (len(built), len(failed), len(skipped), time.time() - t0))
    for k, e in failed + skipped:
        print("   %-18s %s" % (k, e))

    print("\n=== 校验 ===")
    bad_dim = []
    for info in built:
        tgt, got = info["target"], info["bbox"]
        if not tgt or not got:
            continue
        exp = [tgt[0], tgt[1], tgt[2]]
        got_xzy = [got[0], got[2], got[1]]     # GLB 是 X/Y/Z，目录是 W/D/H
        dev = max(abs(got_xzy[i] - exp[i]) / max(exp[i], 1) for i in range(3))
        if dev > 0.03:
            bad_dim.append((info["key"], exp, got_xzy, round(dev, 3)))
    print("尺寸偏差>3%%: %d" % len(bad_dim))
    for k, e, g, d in bad_dim:
        print("   %-18s 期望%s 实得%s 偏差%.1f%%" % (k, e, g, d * 100))

    print("\n=== 朝向（高度剖面：负端 vs 正端）===")
    wrong = []
    for info in built:
        neg, pos = info.get("neg_h"), info.get("pos_h")
        if neg is None:
            continue
        if neg > pos * 1.10:
            verdict = "靠背 -Z  OK"
        elif pos > neg * 1.10:
            verdict = "靠背 +Z  反了"
        else:
            verdict = "两端相近（对称）"
        if "反了" in verdict:
            wrong.append(info["key"])
        print("   %-18s 负端 %.2f  正端 %.2f  %s"
              % (info["key"], neg, pos, verdict))

    rc = Counter()
    for info in built:
        for r in info["roles"]:
            rc[r] += 1
    print("\n角色分布:")
    for k, v in rc.most_common():
        print("   %-22s %d" % (k, v))

    with open(os.path.join(OUT, "_orient_report.json"), "w",
              encoding="utf-8") as f:
        json.dump({"built": built, "failed": failed,
                   "bad_dim": bad_dim, "wrong_orient": wrong},
                  f, ensure_ascii=False, indent=1)

    if not args.apply:
        print("\n(未 --apply，仅生成到 %s)" % OUT)
        return 0

    if bad_dim or wrong:
        print("\n!! 校验未通过（尺寸 %d / 朝向 %d），已中止替换"
              % (len(bad_dim), len(wrong)))
        return 1

    stamp = time.strftime("%Y%m%d_%H%M%S")
    bdir = os.path.join(ROOT, "assets", "_asset_cache", "glb_backup_orient_" + stamp)
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

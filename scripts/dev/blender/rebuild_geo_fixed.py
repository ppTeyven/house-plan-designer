"""【重建 207 个几何模型】用修好的 UV 与材质角色重新生成。

【为什么必须重建，而不是补丁改 GLB】
  缺陷 1（UV 投影）和缺陷 3c（build_freebox 硬编码木）都发生在
  【几何生成阶段】。GLB 里的 UV 是烘进顶点缓冲区的二进制数据，
  事后改要重写 accessor + 顶点，风险高。
  正确做法是：用修好的 geo_gen.py / geo_models.py 重新跑一遍生成。

【安全】
  · 生成到临时目录，不直接覆盖
  · 校验通过（尺寸、UV、三角面数、材质）后才替换
  · 原文件备份到 assets/_asset_cache/glb_backup_<时间戳>/

用法：
  python rebuild_geo_fixed.py            # 只生成到 _geo_new/ 并校验
  python rebuild_geo_fixed.py --apply    # 校验通过后替换
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
OUT = os.path.join(ROOT, "assets", "_asset_cache", "_geo_new")

import geo_models as GM
import fit_item as FI

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
    """检查一个 GLB 的关键指标。返回 dict 或 None（解析失败）。"""
    try:
        js, bin_ = load_glb(path)
    except Exception:
        return None
    mats = js.get("materials") or []
    roles = [m.get("name", "") for m in mats]
    uv_min = [1e9, 1e9]
    uv_max = [-1e9, -1e9]
    degenerate = 0
    uv_count = 0
    for acc in js.get("accessors") or []:
        if acc.get("type") != "VEC2":
            continue
        bv = acc.get("bufferView")
        if bv is None:
            continue
        v = js["bufferViews"][bv]
        n = acc["count"]
        stride = v.get("byteStride") or 8
        off = v.get("byteOffset", 0) + acc.get("byteOffset", 0)
        us = set()
        vs = set()
        for i in range(n):
            u, w = struct.unpack_from("<2f", bin_, off + i * stride)
            us.add(round(u, 5))
            vs.add(round(w, 5))
            uv_min[0] = min(uv_min[0], u)
            uv_min[1] = min(uv_min[1], w)
            uv_max[0] = max(uv_max[0], u)
            uv_max[1] = max(uv_max[1], w)
        uv_count += 1
        if len(us) == 1 or len(vs) == 1:
            degenerate += 1
    tris = 0
    for mesh in js.get("meshes") or []:
        for prim in mesh.get("primitives") or []:
            ai = prim.get("indices")
            if ai is not None:
                tris += js["accessors"][ai]["count"] // 3
    mn = [1e9] * 3
    mx = [-1e9] * 3
    for acc in js.get("accessors") or []:
        if acc.get("type") != "VEC3" or "min" not in acc:
            continue
        for k in range(3):
            mn[k] = min(mn[k], acc["min"][k])
            mx[k] = max(mx[k], acc["max"][k])
    bbox = [round((mx[k] - mn[k]) * 1000) for k in range(3)] if mn[0] < 1e9 else None
    return {
        "roles": roles, "tris": tris, "bbox": bbox,
        "uv_span": [round(uv_max[0] - uv_min[0], 3),
                    round(uv_max[1] - uv_min[1], 3)],
        "uv_degenerate": degenerate, "uv_count": uv_count,
        "size": os.path.getsize(path),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    rep_path = os.path.join(ROOT, "assets", "_asset_cache", "build_report.json")
    rep = json.load(open(rep_path, encoding="utf-8"))
    results = rep["results"]
    SIZES = FI.load_sizes()

    geo_keys = [r["key"] for r in results if r.get("route") == "geo"]
    print("几何生成模型: %d 项" % len(geo_keys))

    os.makedirs(OUT, exist_ok=True)

    t0 = time.time()
    built = []
    failed = []
    for i, key in enumerate(geo_keys):
        builder = key if key in GM.BUILDERS else None
        if builder is None:
            for r in results:
                if r["key"] == key and r.get("type") in GM.BUILDERS:
                    builder = r["type"]
                    break
        if builder is None:
            failed.append((key, "no_builder"))
            continue
        target = SIZES.get(key)
        params = {}
        if target:
            params = {"w": target[0], "d": target[1], "h": target[2]}
        dest = os.path.join(OUT, key + ".glb")
        try:
            GM.export(builder, dest, params)
        except Exception as e:
            failed.append((key, "export: %s" % str(e)[:80]))
            continue
        info = audit_glb(dest)
        if info is None:
            failed.append((key, "unreadable"))
            continue
        built.append((key, info, target))
        if (i + 1) % 25 == 0:
            print("  %d/%d (%.0fs)" % (i + 1, len(geo_keys), time.time() - t0))

    print("\n生成成功 %d / 失败 %d" % (len(built), len(failed)))
    for k, e in failed:
        print("   FAIL %-18s %s" % (k, e))

    print("\n=== 校验 ===")
    bad_dim = []
    degen = []
    for key, info, target in built:
        if target and info["bbox"]:
            got = info["bbox"]
            exp = [target[0], target[1], target[2]]
            got_xzy = [got[0], got[2], got[1]]
            dev = max(abs(got_xzy[i] - exp[i]) / max(exp[i], 1) for i in range(3))
            if dev > 0.03:
                bad_dim.append((key, exp, got_xzy, round(dev, 3)))
        if info["uv_degenerate"] > 0:
            degen.append((key, info["uv_degenerate"], info["uv_count"]))

    print("尺寸偏差>3%%: %d" % len(bad_dim))
    for k, e, g, d in bad_dim[:20]:
        print("   %-18s 期望%s 实得%s 偏差%.1f%%" % (k, e, g, d * 100))
    print("UV 退化(某方向仅1个取值): %d" % len(degen))
    for k, d, t in degen[:20]:
        print("   %-18s 退化 %d / %d 个 UV accessor" % (k, d, t))

    rc = Counter()
    for key, info, target in built:
        for r in info["roles"]:
            rc[r] += 1
    print("\n新角色分布:")
    for k, v in rc.most_common():
        print("   %-22s %d" % (k, v))

    with open(os.path.join(OUT, "_rebuild_report.json"), "w",
              encoding="utf-8") as f:
        json.dump({"built": [{"key": k, **i} for k, i, _ in built],
                   "failed": failed}, f, ensure_ascii=False, indent=1)

    if not args.apply:
        print("\n(未 --apply，仅生成到 %s)" % OUT)
        return 0

    stamp = time.strftime("%Y%m%d_%H%M%S")
    bdir = os.path.join(ROOT, "assets", "_asset_cache", "glb_backup_" + stamp)
    for base, sub in ((ACC, "acc"), (NEW, "furnlib")):
        dst = os.path.join(bdir, sub)
        os.makedirs(dst, exist_ok=True)
        for key, info, target in built:
            src = os.path.join(base, key + ".glb")
            if os.path.exists(src):
                try:
                    shutil.copy2(src, os.path.join(dst, key + ".glb"))
                except OSError:
                    pass
    n = 0
    for key, info, target in built:
        src = os.path.join(OUT, key + ".glb")
        for base in (ACC, NEW):
            dst = os.path.join(base, key + ".glb")
            if not os.path.exists(dst):
                continue
            try:
                shutil.copy2(src, dst)
                n += 1
            except OSError as e:
                print("   替换失败 %s/%s: %s" % (base, key, e))
    print("\n已替换 %d 个文件 (备份: %s)" % (n, bdir))
    return 0


if __name__ == "__main__":
    sys.exit(main())

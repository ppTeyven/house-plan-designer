"""【基线审计】251 个模型当前的贴图/角色状态快照。

用于修复前后的对比 —— 手册第 3 条：不凭记忆断言事实，必须查证。

用法：
  python audit_tex_state.py                 # 报告（验收/models 优先）
  python audit_tex_state.py --dir 验收/models
  python audit_tex_state.py --json out.json
"""
import argparse
import json
import os
import struct
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))

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


def audit(path):
    js, bin_ = load_glb(path)
    mats = js.get("materials") or []
    images = js.get("images") or []
    textures = js.get("textures") or []
    n_tex = 0          # 有贴图的材质数
    n_nor = 0
    n_mr = 0
    n_ao = 0
    roles = []
    for m in mats:
        nm = m.get("name", "")
        roles.append(nm[2:] if nm.startswith("U_") else nm)
        pbr = m.get("pbrMetallicRoughness") or {}
        if pbr.get("baseColorTexture"):
            n_tex += 1
        if pbr.get("metallicRoughnessTexture"):
            n_mr += 1
        if m.get("normalTexture"):
            n_nor += 1
        if m.get("occlusionTexture"):
            n_ao += 1
    # 几何量
    n_tris = 0
    n_prim = 0
    for mesh in js.get("meshes", []):
        for prim in mesh.get("primitives", []):
            n_prim += 1
            ai = prim.get("indices")
            if ai is not None and ai < len(js.get("accessors", [])):
                n_tris += js["accessors"][ai]["count"] // 3
    return {
        "key": os.path.splitext(os.path.basename(path))[0],
        "mats": len(mats),
        "roles": roles,
        "col": n_tex, "mr": n_mr, "nor": n_nor, "ao": n_ao,
        "images": len(images), "textures": len(textures),
        "tris": n_tris, "prims": n_prim,
        "size": os.path.getsize(path),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default=os.path.join(ROOT, "验收", "models"))
    ap.add_argument("--json", default=None)
    args = ap.parse_args()

    d = args.dir
    files = sorted(f for f in os.listdir(d) if f.endswith(".glb"))
    rows = []
    errs = []
    for f in files:
        try:
            rows.append(audit(os.path.join(d, f)))
        except Exception as e:
            errs.append((f, str(e)))

    n = len(rows)
    no_col = [r for r in rows if r["col"] == 0]
    no_any = [r for r in rows if r["col"] == 0 and r["mr"] == 0
              and r["nor"] == 0 and r["ao"] == 0]
    full = [r for r in rows if r["col"] and r["mr"] and r["nor"]]
    mr_no_col = [r for r in rows if r["mr"] and not r["col"]]

    rc = Counter()
    for r in rows:
        for role in r["roles"]:
            rc[role] += 1

    print("目录: %s" % d)
    print("模型总数: %d   解析失败: %d" % (n, len(errs)))
    print("\n--- 贴图覆盖率 ---")
    print("  完全没有 baseColorTexture : %d" % len(no_col))
    print("  四槽全空（纯白模）        : %d" % len(no_any))
    print("  col+mr+nor 三件套齐全     : %d" % len(full))
    print("  有 mr 但没 col（异常）    : %d" % len(mr_no_col))
    print("\n--- 材质角色分布 ---")
    for k, v in rc.most_common():
        print("  %-22s %d" % (k or "(空名)", v))
    print("\n--- 无 baseColorTexture 的模型 (%d) ---" % len(no_col))
    for r in no_col[:300]:
        print("  %-20s mats=%d tris=%-7d roles=%s"
              % (r["key"], r["mats"], r["tris"], ",".join(r["roles"][:4])))
    if errs:
        print("\n--- 解析失败 ---")
        for f, e in errs:
            print("  %s: %s" % (f, e))

    if args.json:
        with open(args.json, "w", encoding="utf-8") as f:
            json.dump({"rows": rows, "errors": errs}, f, ensure_ascii=False, indent=1)
        print("\n-> %s" % args.json)


if __name__ == "__main__":
    main()

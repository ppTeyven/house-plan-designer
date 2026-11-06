"""【诊断】审计 251 个 GLB 的几何一致性 —— 定位"黑白三角乱刺"的根因。

【现象】
  验收站里几乎所有【几何生成】模型渲染成一堆黑白三角尖刺，
  像被撕碎的纸。PH 现成资源（44 个）正常。
  → 问题出在 geo_gen.py 的网格导出，不在贴图。

【检查项】
  ① accessor 计数一致性：POSITION / NORMAL / TEXCOORD_0 的 count 是否一致
     —— 不一致 → 法线缓冲与顶点缓冲错位 → 法线读到了别的顶点的值
  ② index 上界 < POSITION count —— 否则是索引越界 → 三角形乱飞
  ③ 法线是否单位长度
  ④ 每个 primitive 是否都指定了 material
  ⑤ 是否缺少 TANGENT（有 normalTexture 无 tangent 时靠屏幕空间导数，
     通常没问题，但要确认）
"""
import json
import math
import os
import struct
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
ACC = os.path.join(ROOT, "assets", "furnlib")
CT_JSON = 0x4E4F534A
CT_BIN = 0x004E4942


def load_glb(path):
    with open(path, "rb") as f:
        blob = f.read()
    off = 12
    js, bn = None, b""
    while off + 8 <= len(blob):
        cl, ct = struct.unpack("<II", blob[off:off + 8])
        d = blob[off + 8:off + 8 + cl]
        if ct == CT_JSON:
            js = json.loads(d.decode("utf-8"))
        elif ct == CT_BIN:
            bn = d
        off += 8 + cl
    return js, bn


def read_accessor(js, bn, idx):
    """返回 (values, comps, type) —— values 是元组列表。

    【重要】componentType 在【accessor】上，不在 bufferView 上。
      glTF 规范：accessor.componentType 决定元素类型；
      bufferView 只有 byteOffset/byteLength/byteStride。
      旧实现从 bufferView 读 componentType（不存在 → 默认 5126=float），
      对 ushort/uint 索引会读错字节 → 误报"索引越界"。
    """
    acc = js["accessors"][idx]
    t = acc["type"]
    comps = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4, "MAT4": 16}[t]
    bv = acc.get("bufferView")
    if bv is None:
        return [], comps, t
    v = js["bufferViews"][bv]
    ctype = acc.get("componentType", 5126)      # ← accessor，不是 bufferView
    # glTF componentType: 5120=byte 5121=ubyte 5122=short 5123=ushort 5125=uint 5126=float
    code, size = {5120: ("b", 1), 5121: ("B", 1), 5122: ("h", 2),
                  5123: ("H", 2), 5125: ("I", 4), 5126: ("f", 4)}[ctype]
    stride = v.get("byteStride") or comps * size
    base = v.get("byteOffset", 0) + acc.get("byteOffset", 0)
    n = acc["count"]
    out = []
    for i in range(n):
        o = base + i * stride
        out.append(struct.unpack_from("<%d%s" % (comps, code), bn, o))
    return out, comps, t


def audit(path):
    try:
        js, bn = load_glb(path)
    except Exception as e:
        return {"fatal": str(e)[:60]}
    r = {"mismatch": [], "idx_oob": [], "bad_norm": 0, "no_mat": 0,
         "prims": 0, "no_uv": 0, "no_tangent": 0}
    for mi, mesh in enumerate(js.get("meshes") or []):
        for pi, prim in enumerate(mesh.get("primitives") or []):
            r["prims"] += 1
            if prim.get("material") is None:
                r["no_mat"] += 1
            att = prim.get("attributes") or {}
            p = att.get("POSITION")
            n = att.get("NORMAL")
            t = att.get("TEXCOORD_0")
            if p is None:
                continue
            pacc = js["accessors"][p]
            pc = pacc["count"]
            if t is None:
                r["no_uv"] += 1
            if "TANGENT" not in att:
                r["no_tangent"] += 1
            # ① 计数一致性
            for label, ai in (("NORMAL", n), ("TEXCOORD_0", t)):
                if ai is None:
                    continue
                c = js["accessors"][ai]["count"]
                if c != pc:
                    r["mismatch"].append("mesh%d/prim%d %s count=%d != POS=%d"
                                         % (mi, pi, label, c, pc))
            # ② 索引上界
            ii = prim.get("indices")
            if ii is not None:
                idx, _, _ = read_accessor(js, bn, ii)
                if idx:
                    mx = max(x[0] for x in idx)
                    if mx >= pc:
                        r["idx_oob"].append("mesh%d/prim%d maxIdx=%d >= pos=%d"
                                            % (mi, pi, mx, pc))
            # ③ 法线单位长度
            if n is not None:
                nrm, _, _ = read_accessor(js, bn, n)
                for v in nrm[:400]:
                    L = math.sqrt(v[0] ** 2 + v[1] ** 2 + v[2] ** 2)
                    if not (0.5 < L < 1.5):
                        r["bad_norm"] += 1
                        break
    return r


def main():
    files = sorted(f for f in os.listdir(ACC) if f.endswith(".glb"))
    rep_path = os.path.join(ROOT, "assets", "_asset_cache", "build_report.json")
    route = {}
    if os.path.exists(rep_path):
        for r in json.load(open(rep_path, encoding="utf-8"))["results"]:
            route[r["key"]] = r.get("route")

    bad = []
    stats = Counter()
    for f in files:
        key = f[:-4]
        res = audit(os.path.join(ACC, f))
        if "fatal" in res:
            print("FATAL %s: %s" % (key, res["fatal"]))
            continue
        issues = []
        if res["mismatch"]:
            issues.append("COUNT_MISMATCH:" + res["mismatch"][0])
        if res["idx_oob"]:
            issues.append("IDX_OOB:" + res["idx_oob"][0])
        if res["bad_norm"]:
            issues.append("BAD_NORMAL")
        if res["no_mat"]:
            issues.append("NO_MATERIAL:%d" % res["no_mat"])
        if res["no_uv"]:
            issues.append("NO_UV:%d" % res["no_uv"])
        if issues:
            bad.append((key, route.get(key), issues))
        stats["n_mismatch"] += len(res["mismatch"])
        stats["n_idoob"] += len(res["idx_oob"])
        stats["n_badnorm"] += res["bad_norm"]
        stats["n_nomat"] += res["no_mat"]
        stats["n_nouv"] += res["no_uv"]
        stats["n_notan"] += res["no_tangent"]

    print("=== 几何审计: %d 个模型 ===" % len(files))
    print("  accessor 计数不一致 : %d 个模型" % len([b for b in bad if any('COUNT' in i for i in b[2])]))
    print("  索引越界            : %d 个模型" % len([b for b in bad if any('IDX' in i for i in b[2])]))
    print("  法线非单位长度      : %d 个模型" % len([b for b in bad if any('BAD_NORMAL' in i for i in b[2])]))
    print("  primitive 无材质    : %d 个模型" % len([b for b in bad if any('NO_MATERIAL' in i for i in b[2])]))
    print("  缺 UV               : %d 个模型" % len([b for b in bad if any('NO_UV' in i for i in b[2])]))
    print("  缺 TANGENT          : %d 个模型 (有 normalTexture 时需注意)" % stats["n_notan"])
    print()
    for key, rt, iss in bad[:25]:
        print("  %-16s [%s] %s" % (key, rt or "?", "; ".join(iss)))

    # 按路线统计
    byroute = Counter()
    for key, rt, iss in bad:
        byroute[rt or "?"] += 1
    print("\n问题模型按构建路线:", dict(byroute))


if __name__ == "__main__":
    main()

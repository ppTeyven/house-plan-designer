"""全量 251 个 GLB 的几何完整性体检。

【为什么查这个】用户报"几乎所有的物件都是乱码"。如果只查 UI 文字（已排除），
剩下的可能解释是几何数据坏掉：NaN / Inf 顶点、UV 爆炸、索引越界、
顶点被压扁到原点或拉到天外——渲染出来就是一团噪点/"乱码"。

检查项：
  1. 顶点/索引 accessor 里有没有 NaN / Inf
  2. 有没有索引越界
  3. UV 数值范围（0..1 还是爆炸到 1e6）
  4. 包围盒（长宽高是否有 0 或离谱值）
  5. 三角形退化（面积≈0）比例
  6. 顶点坐标是否大量重复/塌陷（去重后比例过低 = 网格塌了）

用法：python geo_audit.py
"""
import json
import math
import os
import struct
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
ACC = os.path.join(ROOT, "assets", "furnlib")

CT_JSON = 0x4E4F534A
CT_BIN = 0x004E4942

COMP = {5120: ("b", 1), 5121: ("B", 1), 5122: ("h", 2),
        5123: ("H", 2), 5125: ("I", 4), 5126: ("f", 4)}
NCOMP = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4, "MAT4": 16}


def load_glb(path):
    blob = open(path, "rb").read()
    total = struct.unpack("<I", blob[8:12])[0]
    off = 12
    js = None
    binchunk = None
    while off + 8 <= min(total, len(blob)):
        clen, ctype = struct.unpack("<II", blob[off:off + 8])
        data = blob[off + 8:off + 8 + clen]
        if ctype == CT_JSON:
            js = json.loads(data.decode("utf-8"))
        elif ctype == CT_BIN:
            binchunk = data
        off += 8 + clen
    return js, binchunk


def read_accessor(js, binchunk, idx):
    acc = js["accessors"][idx]
    bv = js["bufferViews"][acc["bufferView"]]
    n = NCOMP[acc["type"]]
    fmt, size = COMP[acc["componentType"]]
    count = acc["count"]
    base = bv.get("byteOffset", 0) + acc.get("byteOffset", 0)
    stride = bv.get("byteStride") or (n * size)
    out = []
    for i in range(count):
        s = base + i * stride
        v = struct.unpack_from("<" + fmt * n, binchunk, s)
        out.append(v[0] if n == 1 else v)
    return out, acc, bv


def audit(path):
    js, binchunk = load_glb(path)
    res = {
        "name": os.path.basename(path),
        "nan": 0, "inf": 0,
        "oob": 0,          # 索引越界
        "uv_max": 0.0,
        "degenerate": 0,
        "tris": 0,
        "bbox": None,
        "uniq_ratio": 1.0,
        "uv_missing": 0,   # 完全没有 TEXCOORD_0 的网格数
        "no_uv_meshes": 0,
        "mats": set(),
        "flat_slots": 0,
    }
    verts_all = []
    for mi, m in enumerate(js.get("meshes", [])):
        for pr in m.get("primitives", []):
            pos_idx = pr.get("attributes", {}).get("POSITION")
            if pos_idx is None:
                continue
            pos, _, _ = read_accessor(js, binchunk, pos_idx)
            verts_all.extend(pos)
            for v in pos:
                for c in v:
                    if math.isnan(c):
                        res["nan"] += 1
                    elif math.isinf(c):
                        res["inf"] += 1
            uv_idx = pr.get("attributes", {}).get("TEXCOORD_0")
            if uv_idx is None:
                res["no_uv_meshes"] += 1
            else:
                uv, _, _ = read_accessor(js, binchunk, uv_idx)
                for u in uv:
                    for c in u:
                        if not (math.isnan(c) or math.isinf(c)):
                            res["uv_max"] = max(res["uv_max"], abs(c))
            idx_idx = pr.get("indices")
            if idx_idx is not None:
                idx, _, _ = read_accessor(js, binchunk, idx_idx)
                n = len(pos)
                for i in idx:
                    if i >= n or i < 0:
                        res["oob"] += 1
                for t in range(0, len(idx) - 2, 3):
                    a, b, c = pos[idx[t]], pos[idx[t + 1]], pos[idx[t + 2]]
                    ux, uy, uz = b[0] - a[0], b[1] - a[1], b[2] - a[2]
                    vx, vy, vz = c[0] - a[0], c[1] - a[1], c[2] - a[2]
                    cx = uy * vz - uz * vy
                    cy = uz * vx - ux * vz
                    cz = ux * vy - uy * vx
                    area = 0.5 * math.sqrt(cx * cx + cy * cy + cz * cz)
                    res["tris"] += 1
                    if area < 1e-9:
                        res["degenerate"] += 1
            mat = pr.get("material")
            if mat is not None:
                mm = js["materials"][mat]
                res["mats"].add(mm.get("name", ""))
                pbr = mm.get("pbrMetallicRoughness", {}) or {}
                if not pbr.get("baseColorTexture"):
                    res["flat_slots"] += 1
    if verts_all:
        xs = [v[0] for v in verts_all]
        ys = [v[1] for v in verts_all]
        zs = [v[2] for v in verts_all]
        res["bbox"] = (min(xs), max(xs), min(ys), max(ys), min(zs), max(zs))
        uniq = len(set((round(v[0], 5), round(v[1], 5), round(v[2], 5)) for v in verts_all))
        res["uniq_ratio"] = uniq / max(1, len(verts_all))
    return res


files = sorted(f for f in os.listdir(ACC) if f.endswith(".glb"))
print("检查 %d 个 GLB ..." % len(files))
problems = []
flat_only = []
no_uv = []
for f in files:
    try:
        r = audit(os.path.join(ACC, f))
    except Exception as e:
        problems.append((f, "解析异常: %s" % e))
        continue
    bad = []
    if r["nan"]:
        bad.append("NaN顶点%d" % r["nan"])
    if r["inf"]:
        bad.append("Inf顶点%d" % r["inf"])
    if r["oob"]:
        bad.append("索引越界%d" % r["oob"])
    if r["uv_max"] > 1e4:
        bad.append("UV爆炸%.3g" % r["uv_max"])
    if r["bbox"]:
        dx = r["bbox"][1] - r["bbox"][0]
        dy = r["bbox"][3] - r["bbox"][2]
        dz = r["bbox"][5] - r["bbox"][4]
        if min(dx, dy, dz) <= 1e-6:
            bad.append("塌陷轴(%.3g,%.3g,%.3g)" % (dx, dy, dz))
        if max(dx, dy, dz) > 100:
            bad.append("尺寸离谱(%.3g,%.3g,%.3g)" % (dx, dy, dz))
    if r["uniq_ratio"] < 0.02 and r["tris"] > 100:
        bad.append("顶点塌缩uniq=%.3f" % r["uniq_ratio"])
    if r["degenerate"] and r["tris"] and r["degenerate"] / r["tris"] > 0.5:
        bad.append("退化面%.0f%%" % (100.0 * r["degenerate"] / r["tris"]))
    if bad:
        problems.append((f, ", ".join(bad)))
    if r["flat_slots"] and r["flat_slots"] == len(r["mats"]):
        flat_only.append(f)
    if r["no_uv_meshes"]:
        no_uv.append((f, r["no_uv_meshes"]))

print("\n=== 几何问题 %d 个 ===" % len(problems))
for f, b in problems[:60]:
    print("  %-26s %s" % (f, b))

print("\n=== 全部材质无贴图（纯色）的模型 %d 个 ===" % len(flat_only))
for f in flat_only[:40]:
    print("  ", f)

print("\n=== 无 UV 的模型 %d 个 ===" % len(no_uv))
for f, c in no_uv[:40]:
    print("   %-26s 无UV网格 %d" % (f, c))

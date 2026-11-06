"""【闭合性检查】验证几何生成模型的三角网格是否为【闭合流形】。

【为什么必须查这个】
  验收站渲染出的"黑白三角乱刺"（如图中的镜子），
  几何数据完全合法：GLB 结构对、索引不越界、绕序对、无退化面。
  但渲染仍然碎裂 → 只能是【网格本身不闭合】：
  某些面缺失 → 看到的是壳体内部 → DoubleSide 把内壁也画出来 →
  内壁法线方向相反 → 黑白交替。

【检查方法】
  把每条边（按无序顶点对规范化）统计出现次数：
    出现 1 次 → 边界边（洞）→ 不闭合
    出现 2 次 → 正常内部边
    出现 >2 次 → 非流形（多个面共享一条边）
  闭合流形 = 边界边为 0 且非流形边为 0。

用法：python audit_manifold.py
"""
import json
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


def read_idx(js, bn, idx):
    """读索引 accessor。

    【重要】componentType 在【accessor】上，不在 bufferView 上。
      旧实现从 bufferView 读（不存在 → 默认 5125=uint），
      把 2 字节 ushort 当 4 字节 uint 读 → 索引被放大 65536 倍
      → 误报"索引越界"。
    """
    acc = js["accessors"][idx]
    bv = acc.get("bufferView")
    if bv is None:
        return []
    v = js["bufferViews"][bv]
    ctype = acc.get("componentType", 5125)      # ← accessor，不是 bufferView
    code, size = {5121: ("B", 1), 5123: ("H", 2), 5125: ("I", 4)}[ctype]
    stride = v.get("byteStride") or size
    base = v.get("byteOffset", 0) + acc.get("byteOffset", 0)
    out = []
    for i in range(acc["count"]):
        out.append(struct.unpack_from("<" + code, bn, base + i * stride)[0])
    return out


def audit(path):
    js, bn = load_glb(path)
    edges = Counter()
    tris = 0
    for mesh in js.get("meshes") or []:
        for prim in mesh.get("primitives") or []:
            idx = read_idx(js, bn, prim["indices"])
            for t in range(0, len(idx) - 2, 3):
                a, b, c = idx[t], idx[t + 1], idx[t + 2]
                tris += 1
                for u, v in ((a, b), (b, c), (c, a)):
                    edges[(u, v) if u < v else (v, u)] += 1
    boundary = sum(1 for v in edges.values() if v == 1)
    nonman = sum(1 for v in edges.values() if v > 2)
    return tris, boundary, nonman


def main():
    files = sorted(f for f in os.listdir(ACC) if f.endswith(".glb"))
    rep_path = os.path.join(ROOT, "assets", "_asset_cache", "build_report.json")
    route = {}
    if os.path.exists(rep_path):
        for r in json.load(open(rep_path, encoding="utf-8"))["results"]:
            route[r["key"]] = r.get("route")

    open_meshes = []
    byroute = Counter()
    for f in files:
        key = f[:-4]
        try:
            tris, boundary, nonman = audit(os.path.join(ACC, f))
        except Exception as e:
            print("ERR %s: %s" % (key, e))
            continue
        if boundary or nonman:
            open_meshes.append((key, route.get(key), tris, boundary, nonman))
            byroute[route.get(key) or "?"] += 1

    print("=== 闭合性检查: %d 个模型 ===" % len(files))
    print("不闭合模型: %d" % len(open_meshes))
    print("  按路线:", dict(byroute))
    print()
    print("  %-18s %-5s %8s %10s %10s" % ("key", "route", "tris", "边界边", "非流形"))
    for key, rt, tris, b, nm in open_meshes[:30]:
        print("  %-18s %-5s %8d %10d %10d" % (key, rt or "?", tris, b, nm))


if __name__ == "__main__":
    main()

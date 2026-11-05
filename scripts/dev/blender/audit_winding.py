"""【决定性测试】检查 251 个 GLB 的三角形绕序与顶点法线是否一致。

【为什么测这个】
  验收站渲染出的"黑白三角乱刺"有三种可能根因：
    ① 顶点法线乱 → 明暗交替
    ② 三角形绕序不一致 → Three.js 对 doubleSided 材质翻转背面法线
       → 一半三角面朝里一半朝外 → 黑白交替（最典型）
    ③ UV 错 → 贴图拉花（但 mirror 无贴图仍是乱刺，排除）

  判定：对每个三角形算几何法线（叉积），与三个顶点法线的平均点乘。
      点乘 > 0 → 绕序与法线一致
      点乘 < 0 → 绕序反了
  统计每个模型"反向三角形"占比。

用法：python audit_winding.py
"""
import json
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
ACC = os.path.join(ROOT, "验收", "models")
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


def read_vec(js, bn, idx, comps):
    acc = js["accessors"][idx]
    bv = acc.get("bufferView")
    if bv is None:
        return []
    v = js["bufferViews"][bv]
    size = 4
    stride = v.get("byteStride") or comps * size
    base = v.get("byteOffset", 0) + acc.get("byteOffset", 0)
    out = []
    for i in range(acc["count"]):
        out.append(struct.unpack_from("<%df" % comps, bn, base + i * stride))
    return out


def read_idx(js, bn, idx):
    """读索引 accessor。

    【重要】componentType 在【accessor】上，不在 bufferView 上。
      glTF 规范：accessor.componentType 决定元素类型；
      bufferView 只有 byteOffset/byteLength/byteStride。
      旧实现从 bufferView 读 componentType（不存在 → 默认 5125=uint），
      把 2 字节的 ushort 当 4 字节 uint 读 → 索引值被放大 65536 倍
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
    fwd = inv = 0
    for mesh in js.get("meshes") or []:
        for prim in mesh.get("primitives") or []:
            att = prim.get("attributes") or {}
            if "POSITION" not in att or "NORMAL" not in att:
                continue
            # 【重要】PH 模型有多个 mesh，每个 mesh 的 accessor 索引都不同，
            # 不能假设 0=POSITION / 1=NORMAL —— 必须从 primitive 的 attributes 读。
            pos = read_vec(js, bn, att["POSITION"], 3)
            nrm = read_vec(js, bn, att["NORMAL"], 3)
            idx = read_idx(js, bn, prim["indices"])
            for t in range(0, len(idx) - 2, 3):
                i0, i1, i2 = idx[t], idx[t + 1], idx[t + 2]
                if i2 >= len(pos) or i0 >= len(pos):
                    continue
                p0, p1, p2 = pos[i0], pos[i1], pos[i2]
                ux, uy, uz = p1[0] - p0[0], p1[1] - p0[1], p1[2] - p0[2]
                vx, vy, vz = p2[0] - p0[0], p2[1] - p0[1], p2[2] - p0[2]
                gx = uy * vz - uz * vy
                gy = uz * vx - ux * vz
                gz = ux * vy - uy * vx
                gl = (gx * gx + gy * gy + gz * gz) ** 0.5
                if gl < 1e-12:
                    continue                      # 退化三角形，跳过
                gx, gy, gz = gx / gl, gy / gl, gz / gl
                ax = ay = az = 0.0
                for i in (i0, i1, i2):
                    if i < len(nrm):
                        ax += nrm[i][0]
                        ay += nrm[i][1]
                        az += nrm[i][2]
                al = (ax * ax + ay * ay + az * az) ** 0.5
                if al < 1e-9:
                    continue
                ax, ay, az = ax / al, ay / al, az / al
                d = gx * ax + gy * ay + gz * az
                if d >= 0:
                    fwd += 1
                else:
                    inv += 1
    return fwd, inv


def main():
    files = sorted(f for f in os.listdir(ACC) if f.endswith(".glb"))
    rep_path = os.path.join(ROOT, "assets", "_asset_cache", "build_report.json")
    route = {}
    if os.path.exists(rep_path):
        for r in json.load(open(rep_path, encoding="utf-8"))["results"]:
            route[r["key"]] = r.get("route")

    bad = []
    tot_f = tot_i = 0
    for f in files:
        key = f[:-4]
        try:
            fwd, inv = audit(os.path.join(ACC, f))
        except Exception as e:
            print("ERR %s: %s" % (key, e))
            continue
        tot_f += fwd
        tot_i += inv
        total = fwd + inv
        if total == 0:
            continue
        ratio = inv / total
        if ratio > 0.05:
            bad.append((key, route.get(key), fwd, inv, round(ratio * 100, 1)))

    print("=== 绕序审计 ===")
    print("总三角形: 正向 %d / 反向 %d  (反向占比 %.1f%%)"
          % (tot_f, tot_i, 100.0 * tot_i / max(1, tot_f + tot_i)))
    print("绕序错误模型 (>5%% 反向): %d / %d" % (len(bad), len(files)))
    print()
    for key, rt, fwd, inv, pct in bad[:30]:
        print("  %-16s [%s] 正向%-6d 反向%-6d 反向占比 %.1f%%" % (key, rt or "?", fwd, inv, pct))


if __name__ == "__main__":
    main()

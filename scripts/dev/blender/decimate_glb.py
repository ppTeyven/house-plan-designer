"""GLB 网格抽稀 —— 把超高面数的资源降到网页可用级别。

【为什么需要】
  Polyhaven 的树木类资源面数极端：
    fir_tree_01   约 700 万三角面（单 primitive 540 万顶点）→ GLB 465MB
    pine_tree_01  更高                                   → GLB 914MB
  验收站是浏览器里跑的 Three.js，465MB 的模型根本打不开；
  而且树的针叶在房间里只有几十厘米，看不出 540 万个面。

  这里做【顶点聚类抽稀】：把空间上很近的顶点合并到簇心，
  误差由容差 tol 控制；再【重建 buffer】把没用的空间真正裁掉。

【为什么不直接丢面】
  随机丢面会让针叶变成破洞。聚类合并保形，且对树木这类
  高频细节模型，视觉效果几乎无损。

【依赖】纯 Python（无 numpy 也能跑），慢但结果确定。
"""
import os
import sys
import struct
import math

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import normalize_glb as NG


# =====================================================================
# accessor 读写
# =====================================================================
_COMP_SIZE = {5120: 1, 5121: 1, 5122: 2, 5123: 2, 5125: 4, 5126: 4}
_TYPE_COUNT = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4, "MAT4": 16}


def _read_accessor(js, bin_data, idx):
    """返回 (flat_values, type_str, count, component_type)。"""
    acc = js["accessors"][idx]
    n = acc["count"]
    ctype = acc["componentType"]
    ncomp = _TYPE_COUNT.get(acc["type"], 1)
    if acc.get("bufferView") is None:
        return [0.0] * (n * ncomp), acc["type"], n, ctype
    bv = js["bufferViews"][acc["bufferView"]]
    base = bv.get("byteOffset", 0) + acc.get("byteOffset", 0)
    stride = bv.get("byteStride") or (_COMP_SIZE[ctype] * ncomp)
    cs = _COMP_SIZE[ctype]
    out = []
    for i in range(n):
        off = base + i * stride
        for c in range(ncomp):
            p = off + c * cs
            if ctype == 5126:
                out.append(struct.unpack_from("<f", bin_data, p)[0])
            elif ctype == 5123:
                out.append(struct.unpack_from("<H", bin_data, p)[0])
            elif ctype == 5125:
                out.append(struct.unpack_from("<I", bin_data, p)[0])
            elif ctype == 5121:
                out.append(bin_data[p])
            elif ctype == 5122:
                out.append(struct.unpack_from("<h", bin_data, p)[0])
            else:
                out.append(0.0)
    return out, acc["type"], n, ctype


# =====================================================================
# 顶点聚类抽稀
# =====================================================================
def _cluster(pos, nrm, uv, idx_tri, tol):
    """顶点聚类：返回 (新顶点, 新三角形索引)。

    新顶点为 [px,py,pz, nx,ny,nz, u,v] × N（扁平列表）。
    """
    n = len(pos) // 3
    if n == 0 or not idx_tri:
        return None, None

    xs = pos[0::3]
    ys = pos[1::3]
    zs = pos[2::3]
    lo = (min(xs), min(ys), min(zs))
    ext = max(max(xs) - lo[0], max(ys) - lo[1], max(zs) - lo[2]) or 1.0
    cell = tol if tol > 0 else ext / 500.0

    # 先算每个顶点的"代表簇" —— 用网格哈希，O(n)
    buckets = {}
    for i in range(n):
        key = (int((pos[i * 3] - lo[0]) / cell),
               int((pos[i * 3 + 1] - lo[1]) / cell),
               int((pos[i * 3 + 2] - lo[2]) / cell))
        b = buckets.get(key)
        if b is None:
            buckets[key] = b = []
        b.append(i)

    remap = [0] * n
    new_pos = []
    new_nrm = []
    new_uv = []
    for members in buckets.values():
        ci = len(new_pos) // 3
        cnt = float(len(members))
        new_pos.extend((
            sum(pos[m * 3] for m in members) / cnt,
            sum(pos[m * 3 + 1] for m in members) / cnt,
            sum(pos[m * 3 + 2] for m in members) / cnt,
        ))
        if nrm:
            nx = sum(nrm[m * 3] for m in members) / cnt
            ny = sum(nrm[m * 3 + 1] for m in members) / cnt
            nz = sum(nrm[m * 3 + 2] for m in members) / cnt
            L = math.sqrt(nx * nx + ny * ny + nz * nz) or 1.0
            new_nrm.extend((nx / L, ny / L, nz / L))
        if uv:
            new_uv.extend((
                sum(uv[m * 2] for m in members) / cnt,
                sum(uv[m * 2 + 1] for m in members) / cnt,
            ))
        for m in members:
            remap[m] = ci

    new_idx = []
    for t in range(0, len(idx_tri), 3):
        a = remap[idx_tri[t]]
        b = remap[idx_tri[t + 1]]
        c = remap[idx_tri[t + 2]]
        if a == b or b == c or a == c:
            continue
        new_idx.extend((a, b, c))
    return (new_pos, new_nrm, new_uv), new_idx


# =====================================================================
# 重建 GLB（紧凑 buffer）
# =====================================================================
def _rebuild(js, bin_data, new_data):
    """用抽稀后的数据重建整个 GLB 的 buffer（紧凑、无空洞）。

    new_data: {primitive_key: (pos, nrm, uv, idx)}
      primitive_key = (mesh_index, prim_index)
    """
    out_views = []
    out_accessors = []
    blob = bytearray()

    def add_view(data, ctype, target):
        bv = {"buffer": 0, "byteOffset": len(blob),
              "byteLength": len(data), "target": target}
        out_views.append(bv)
        blob.extend(data)
        return len(out_views) - 1

    def pack_f32(vals):
        b = bytearray()
        for v in vals:
            b += struct.pack("<f", v)
        return b

    def pack_u32(vals):
        b = bytearray()
        for v in vals:
            b += struct.pack("<I", int(v))
        return b

    def pack_u16(vals):
        b = bytearray()
        for v in vals:
            b += struct.pack("<H", int(max(0, min(65535, v))))
        return b

    def add_accessor(vals, ctype, atype, count, target, extra=None):
        if ctype == 5126:
            data = pack_f32(vals)
        elif ctype == 5125:
            data = pack_u32(vals)
        elif ctype == 5123:
            data = pack_u16(vals)
        else:
            data = pack_f32(vals)
        bv = add_view(data, ctype, target)
        acc = {"bufferView": bv, "componentType": ctype, "count": count,
               "type": atype}
        if extra:
            acc.update(extra)
        out_accessors.append(acc)
        return len(out_accessors) - 1

    # ---- 逐 mesh / primitive 重建 ----
    for mi, mesh in enumerate(js.get("meshes", [])):
        new_prims = []
        for pi, prim in enumerate(mesh.get("primitives", [])):
            key = (mi, pi)
            attrs = dict(prim.get("attributes", {}))
            mode = prim.get("mode", 4)
            data = new_data.get(key)
            if data is None:
                # 未抽稀的 primitive：原样搬运
                old_acc = js["accessors"][attrs["POSITION"]]
                pcount = old_acc["count"]
                pos, ptype, _, pctype = _read_accessor(js, bin_data,
                                                       attrs["POSITION"])
                a_pos = add_accessor(pos, pctype, ptype, pcount, 34962)
                attrs["POSITION"] = a_pos
                if "NORMAL" in prim.get("attributes", {}):
                    n, nt, nc, nct = _read_accessor(js, bin_data,
                                                    prim["attributes"]["NORMAL"])
                    attrs["NORMAL"] = add_accessor(n, nct, nt, nc, 34962)
                if "TEXCOORD_0" in prim.get("attributes", {}):
                    u, ut, uc, uct = _read_accessor(js, bin_data,
                                                    prim["attributes"]["TEXCOORD_0"])
                    attrs["TEXCOORD_0"] = add_accessor(u, uct, ut, uc, 34962)
                if prim.get("indices") is not None:
                    fl, ft, fc, fct = _read_accessor(js, bin_data,
                                                    prim["indices"])
                    attrs_index = add_accessor(fl, fct, ft, fc, 34963)
                else:
                    attrs_index = None
                np = {"attributes": attrs, "mode": mode}
                if "material" in prim:
                    np["material"] = prim["material"]
                new_prims.append(np)
                continue

            pos, nrm, uv, idx = data
            nvert = len(pos) // 3
            a_pos = add_accessor(pos, 5126, "VEC3", nvert, 34962)
            attrs["POSITION"] = a_pos
            if nrm:
                attrs["NORMAL"] = add_accessor(nrm, 5126, "VEC3", nvert, 34962)
            if uv:
                attrs["TEXCOORD_0"] = add_accessor(uv, 5126, "VEC2",
                                                   len(uv) // 2, 34962)
            a_idx = add_accessor(idx, 5125, "SCALAR", len(idx), 34963)
            np = {"attributes": attrs, "indices": a_idx, "mode": mode}
            if "material" in prim:
                np["material"] = prim["material"]
            new_prims.append(np)
        mesh["primitives"] = new_prims

    # ---- 图片（贴图）搬进新 buffer ----
    images = js.get("images") or []
    for img in images:
        if img.get("bufferView") is None:
            continue
        old_bv = js["bufferViews"][img["bufferView"]]
        start = old_bv.get("byteOffset", 0)
        length = old_bv.get("byteLength", 0)
        data = bytes(bin_data[start:start + length])
        bv = add_view(data, None, None)
        img["bufferView"] = bv
        img.pop("uri", None)

    # ---- 组装 ----
    new_js = dict(js)
    new_js["bufferViews"] = out_views
    new_js["accessors"] = out_accessors
    if blob:
        new_js["buffers"] = [{"byteLength": len(blob)}]
    else:
        new_js["buffers"] = []
    # accessor 的 min/max 需要更新（否则渲染器会用旧的包围盒）
    return new_js, blob


def _recompute_bounds(js):
    """重算 POSITION accessor 的 min/max（抽稀后必须更新）。"""
    for mesh in js.get("meshes", []):
        for prim in mesh.get("primitives", []):
            pidx = prim.get("attributes", {}).get("POSITION")
            if pidx is None:
                continue
            acc = js["accessors"][pidx]
            if acc.get("bufferView") is None:
                continue
            bv = js["bufferViews"][acc["bufferView"]]
            base = bv.get("byteOffset", 0) + acc.get("byteOffset", 0)
            n = acc["count"]
            mn = [1e30] * 3
            mx = [-1e30] * 3
            for i in range(n):
                p = base + i * 12
                for c in range(3):
                    v = struct.unpack_from("<f", js["_bin"], p + c * 4)[0]
                    if v < mn[c]:
                        mn[c] = v
                    if v > mx[c]:
                        mx[c] = v
            acc["min"] = mn
            acc["max"] = mx


def decimate_glb(src_glb, dest_glb, max_tris=120000, tol_ratio=0.0008):
    """把 GLB 的三角面数降到 max_tris 以内。返回 (原面数, 新面数)。"""
    js, bin_data = NG.read_glb(src_glb)
    orig = NG.count_tris(js)
    if orig <= max_tris:
        NG.write_glb(js, bin_data, dest_glb)
        return orig, orig

    # 模型最大边（用 accessor min/max 的并集）
    mn = [1e9] * 3
    mx = [-1e9] * 3
    for acc in js.get("accessors", []):
        if "min" not in acc:
            continue
        for i in range(3):
            mn[i] = min(mn[i], acc["min"][i])
            mx[i] = max(mx[i], acc["max"][i])
    ext = max((mx[i] - mn[i]) for i in range(3)) if mx[0] > -1e8 else 1.0
    tol = max(ext * tol_ratio, 1e-5)

    new_data = {}
    for mi, mesh in enumerate(js.get("meshes", [])):
        for pi, prim in enumerate(mesh.get("primitives", [])):
            attrs = prim.get("attributes", {})
            if "POSITION" not in attrs:
                continue
            pos, ptype, pcount, pctype = _read_accessor(js, bin_data,
                                                       attrs["POSITION"])
            if ptype != "VEC3":
                continue
            nrm = None
            if "NORMAL" in attrs:
                nrm, _, _, _ = _read_accessor(js, bin_data, attrs["NORMAL"])
            uv = None
            if "TEXCOORD_0" in attrs:
                uv, _, _, _ = _read_accessor(js, bin_data, attrs["TEXCOORD_0"])
            if prim.get("indices") is None:
                idx_tri = list(range(pcount))
            else:
                flat, _, _, _ = _read_accessor(js, bin_data, prim["indices"])
                idx_tri = [int(v) for v in flat]

            res = _cluster(pos, nrm, uv, idx_tri, tol)
            if res[0] is None:
                continue
            (npos, nnrm, nuv), nidx = res
            if len(nidx) >= len(idx_tri):
                continue      # 没变小就不动
            new_data[(mi, pi)] = (npos, nnrm, nuv, nidx)

    if not new_data:
        NG.write_glb(js, bin_data, dest_glb)
        return orig, orig

    new_js, blob = _rebuild(js, bin_data, new_data)
    new_js["_bin"] = blob
    _recompute_bounds(new_js)
    new_js.pop("_bin", None)
    NG.write_glb(new_js, bytes(blob), dest_glb)
    new = NG.count_tris(new_js)
    return orig, new


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("dest")
    ap.add_argument("--max-tris", type=int, default=120000)
    a = ap.parse_args()
    o, n = decimate_glb(a.src, a.dest, max_tris=a.max_tris)
    print("面数 %s -> %s" % (f"{o:,}", f"{n:,}"))

"""测量 glTF/GLB 的【世界空间】包围盒（含节点层级变换）。

【为什么不能用 accessor.min/max】
  accessor 的 min/max 是【网格局部坐标】的边界，不含节点矩阵。
  Polyhaven 的模型常把整棵树放在根节点上做缩放/平移，
  只看 accessor 会得到完全错误的尺寸
  （实测：Chandelier_01 局部 74m，含吊链；SchoolDesk_01 局部 0.7m，实际 1.2m）。
  摆放与比例校验必须用世界坐标包围盒。

【输出】(w, h, d) 单位 mm，轴序 X/Y/Z（与 fit_scale 的 out_dims 对齐）。
"""
import os
import json
import struct
import math
import numpy as np


def _read_gltf(path):
    """返回 (gltf_dict, buffers: list[bytes])。支持 .gltf+外部 .bin 与 .glb。"""
    with open(path, "rb") as f:
        raw = f.read()
    if raw[:4] == b"glTF":
        off = 12
        gltf, bin_chunk = None, None
        while off + 8 <= len(raw):
            clen, ctype = struct.unpack_from("<II", raw, off)
            data = raw[off + 8: off + 8 + clen]
            if ctype == 0x4E4F534A:
                gltf = json.loads(data.decode("utf-8"))
            elif ctype == 0x004E4942:
                bin_chunk = data
            off += 8 + clen + ((4 - clen % 4) % 4 if clen % 4 else 0)
        if gltf is None:
            raise ValueError("GLB 无 JSON chunk: %s" % path)
        bufs = [bin_chunk or b""]
    else:
        gltf = json.loads(raw.decode("utf-8"))
        bufs = []
        for b in gltf.get("buffers", []):
            uri = b.get("uri")
            if uri is None:
                bufs.append(b"")
            elif uri.startswith("data:"):
                import base64
                bufs.append(base64.b64decode(uri.split(",", 1)[1]))
            else:
                with open(os.path.join(os.path.dirname(path), uri), "rb") as bf:
                    bufs.append(bf.read())
    return gltf, bufs


def _mat4(node):
    """节点局部矩阵（glTF 顺序 TRS 或 matrix）。"""
    if "matrix" in node:
        return np.array(node["matrix"], dtype=np.float64).reshape(4, 4).T
    t = node.get("translation", [0, 0, 0])
    r = node.get("rotation", [0, 0, 0, 1])
    s = node.get("scale", [1, 1, 1])
    x, y, z, w = r
    R = np.array([
        [1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
        [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
        [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)],
    ], dtype=np.float64)
    M = np.eye(4)
    M[:3, :3] = R @ np.diag(s)
    M[:3, 3] = t
    return M


def world_bounds(path):
    """返回 (min_xyz, max_xyz) 世界坐标 numpy array（模型原始单位，通常是米）。"""
    gltf, bufs = _read_gltf(path)
    accs = gltf.get("accessors", [])
    bufviews = gltf.get("bufferViews", [])

    def read_accessor(idx):
        a = accs[idx]
        bv = bufviews[a["bufferView"]]
        off = bv.get("byteOffset", 0) + a.get("byteOffset", 0)
        n = a["count"]
        ctype = a["componentType"]
        ncomp = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4,
                 "MAT4": 16}[a["type"]]
        fmt = {5120: "i1", 5121: "u1", 5122: "i2",
               5123: "u2", 5125: "u4", 5126: "f4"}[ctype]
        arr = np.frombuffer(bufs[bv["buffer"]], dtype=np.dtype(fmt),
                            count=n * ncomp, offset=off)
        return arr.reshape(n, ncomp).astype(np.float64)

    nodes = gltf.get("nodes", [])
    meshes = gltf.get("meshes", [])

    # 遍历场景树，累积世界矩阵
    mins, maxs = [], []
    scene = gltf.get("scenes", [{}])[gltf.get("scene", 0)]
    roots = scene.get("nodes", list(range(len(nodes))))

    def walk(nid, parent):
        node = nodes[nid]
        M = parent @ _mat4(node)
        if "mesh" in node:
            mesh = meshes[node["mesh"]]
            for prim in mesh.get("primitives", []):
                if "POSITION" not in prim.get("attributes", {}):
                    continue
                P = read_accessor(prim["attributes"]["POSITION"])
                if P.size == 0:
                    continue
                ones = np.ones((P.shape[0], 1))
                Pw = np.hstack([P, ones]) @ M.T
                mins.append(Pw[:, :3].min(axis=0))
                maxs.append(Pw[:, :3].max(axis=0))
        for ch in node.get("children", []):
            walk(ch, M)

    for r in roots:
        walk(r, np.eye(4))
    if not mins:
        return np.zeros(3), np.zeros(3)
    return np.array(mins).min(axis=0), np.array(maxs).max(axis=0)


def dims_mm(path):
    """世界空间包围盒尺寸 (w, h, d) 毫米。"""
    lo, hi = world_bounds(path)
    return tuple(float(x) * 1000.0 for x in (hi - lo))


if __name__ == "__main__":
    import sys
    for p in sys.argv[1:]:
        try:
            w, h, d = dims_mm(p)
            print("%-46s w=%.0f h=%.0f d=%.0f  (%.2f x %.2f x %.2f m)"
                  % (os.path.basename(os.path.dirname(p)) or p,
                     w, h, d, w / 1000, h / 1000, d / 1000))
        except Exception as e:
            print("%-46s ERR %s" % (p, e))

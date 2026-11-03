"""GLB 体检：真实面数/顶点/材质/世界包围盒。

坐标系要点（Blender 4.5 实测确证，见 probe_export.py）：
1) Blender 导出 glTF 时做 Y-up ↔ Z-up 轴交换：Blender(x,y,z) → glTF(x, z, -y)
   实测：Blender 世界 y 0~2.0 ⇒ glTF accessor z = -2.0，y = 0~0.5
2) accessor.min/max 是【网格局部坐标】，节点保留 TRS；两者需相乘，且
   glTF 矩阵是列主序（m[col*4+row]），不能按行主序算
3) 节点无 transform 时为恒等（Blender 把变换烘进网格）
"""
import json, struct, sys, os


def read_glb(path):
    with open(path, "rb") as f:
        data = f.read()
    if data[:4] != b"glTF":
        raise ValueError("not a GLB: %s" % path)
    off = 12
    js = None
    while off < len(data):
        clen, ctype = struct.unpack_from("<II", data, off)
        off += 8
        chunk = data[off:off + clen]
        off += clen
        if ctype == 0x4E4F534A:
            js = json.loads(chunk.decode("utf-8"))
    if js is None:
        raise ValueError("no JSON chunk: %s" % path)
    return js


# Blender(Z-up) → glTF(Y-up)：实测确证
#   Blender X(宽) → glTF X
#   Blender Z(高) → glTF Y
#   Blender Y(深) → glTF -Z
# 故反向：glTF(x,y,z) → Blender(x, z, -y)
def blender_to_gltf_axes(p):
    x, y, z = p
    return (x, z, -y)


def gltf_to_blender_axes(p):
    x, y, z = p
    return (x, z, -y)


def mat_mul_colmajor(a, b):
    """列主序 4x4 相乘：m[col*4 + row]"""
    r = [0.0] * 16
    for c in range(4):
        for row in range(4):
            r[c * 4 + row] = sum(a[k * 4 + row] * b[c * 4 + k] for k in range(4))
    return r


def node_local(n):
    if "matrix" in n:
        return list(n["matrix"])
    t = n.get("translation", [0, 0, 0])
    r = n.get("rotation", [0, 0, 0, 1])
    s = n.get("scale", [1, 1, 1])
    x, y, z, w = r
    # glTF 四元数 (x,y,z,w) → 列主序旋转矩阵
    rot = [
        1 - 2 * (y * y + z * z), 2 * (x * y + z * w), 2 * (x * z - y * w),
        2 * (x * y - z * w), 1 - 2 * (x * x + z * z), 2 * (y * z + x * w),
        2 * (x * z + y * w), 2 * (y * z - x * w), 1 - 2 * (x * x + y * y),
    ]
    out = [0.0] * 16
    for c in range(3):
        for row in range(3):
            out[c * 4 + row] = rot[c * 3 + row] * s[c]
    out[3] = t[0]; out[7] = t[1]; out[11] = t[2]
    out[15] = 1.0
    return out


def identity():
    return [1.0, 0, 0, 0, 0, 1.0, 0, 0, 0, 0, 1.0, 0, 0, 0, 0, 1.0]


def transform_point(m, p):
    """列主序矩阵作用到点"""
    x, y, z = p
    return (
        m[0] * x + m[4] * y + m[8] * z + m[12],
        m[1] * x + m[5] * y + m[9] * z + m[13],
        m[2] * x + m[6] * y + m[10] * z + m[14],
    )


def stats(path):
    js = read_glb(path)
    meshes = js.get("meshes", [])
    nodes = js.get("nodes", [])

    mats, seen = [], set()
    for m in meshes:
        for p in m.get("primitives", []):
            mi = p.get("material")
            if mi is not None and mi not in seen:
                seen.add(mi)
                mats.append(js["materials"][mi].get("name") or "(unnamed)")

    verts = tris = 0
    for m in meshes:
        for p in m.get("primitives", []):
            acc = js["accessors"][p["attributes"]["POSITION"]]
            verts += acc.get("count", 0)
            mode = p.get("mode", 4)
            idx = p.get("indices")
            if mode == 4:
                tris += (js["accessors"][idx]["count"] // 3) if idx is not None else acc.get("count", 0) // 3
            elif mode in (5, 6):
                n = js["accessors"][idx]["count"] if idx is not None else acc.get("count", 0)
                tris += max(0, n - 2)

    # 世界包围盒：glTF 空间沿节点层级累积
    mn = [1e9] * 3
    mx = [-1e9] * 3

    def walk(ni, parent):
        n = nodes[ni]
        world = mat_mul_colmajor(parent, node_local(n))
        if "mesh" in n:
            m = meshes[n["mesh"]]
            for p in m.get("primitives", []):
                acc = js["accessors"][p["attributes"]["POSITION"]]
                if "min" not in acc:
                    continue
                lo = transform_point(world, acc["min"])
                hi = transform_point(world, acc["max"])
                for i in range(3):
                    mn[i] = min(mn[i], lo[i], hi[i])
                    mx[i] = max(mx[i], lo[i], hi[i])
        for ch in n.get("children", []):
            walk(ch, world)

    roots = js.get("scenes", [{}])[0].get("nodes", list(range(len(nodes))))
    for r in roots:
        walk(r, identity())

    if mn[0] > 1e8:
        mn = [0, 0, 0]; mx = [0, 0, 0]
    dims = [mx[i] - mn[i] for i in range(3)]

    # 换回 Blender 坐标（宽X / 深Y / 高Z），供尺寸自检使用。
    # 实测确证的轴映射（见 probe_export.py）：
    #   Blender X(宽) = glTF X
    #   Blender Y(深) = -glTF Z
    #   Blender Z(高) =  glTF Y
    # 每条轴都是单调映射，可直接对区间做区间变换（不能拿角点映射后再逐分量求差，会串轴）
    gmn, gmx = mn, mx
    b_x = (gmn[0], gmx[0])
    b_y = (-gmx[2], -gmn[2])
    b_z = (gmn[1], gmx[1])
    b_dims = [b_x[1] - b_x[0], b_y[1] - b_y[0], b_z[1] - b_z[0]]
    b_min = [b_x[0], b_y[0], b_z[0]]
    b_max = [b_x[1], b_y[1], b_z[1]]
    b_zmin = b_z[0]

    return {
        "file": os.path.basename(path),
        "bytes": os.path.getsize(path),
        "meshObjects": len(meshes),
        "nodes": len(nodes),
        "vertices": verts,
        "triangles": tris,
        "materials": sorted(mats),
        "bbox": {"min": b_min, "max": b_max},
        "dims": b_dims,
        "gltf_dims": dims,
        "zmin": b_zmin,
    }


if __name__ == "__main__":
    out = {}
    for p in sys.argv[1:]:
        for f in sorted(os.listdir(p)):
            if f.lower().endswith(".glb"):
                out[f[:-4]] = stats(os.path.join(p, f))
    print(json.dumps(out, ensure_ascii=False, indent=1))

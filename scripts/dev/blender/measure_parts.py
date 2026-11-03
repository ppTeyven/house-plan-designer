"""逐部件测量 GLB 的世界包围盒，定位尺寸越界的具体部件。

用法：blender --background --python measure_parts.py -- <glb> [--top N]
（不依赖 Blender 运行时也可以跑：直接解析 GLB accessor + 节点矩阵）
"""
import json, sys, os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from inspect_glb import read_glb, mat_mul_colmajor, node_local, transform_point, identity


def parts(path):
    js = read_glb(path)
    meshes = js.get("meshes", [])
    nodes = js.get("nodes", [])
    out = []

    def walk(ni, parent):
        n = nodes[ni]
        world = mat_mul_colmajor(parent, node_local(n))
        if "mesh" in n:
            m = meshes[n["mesh"]]
            mn = [1e9] * 3
            mx = [-1e9] * 3
            tris = 0
            for p in m.get("primitives", []):
                acc = js["accessors"][p["attributes"]["POSITION"]]
                if "min" not in acc:
                    continue
                lo = transform_point(world, acc["min"])
                hi = transform_point(world, acc["max"])
                for i in range(3):
                    mn[i] = min(mn[i], lo[i], hi[i])
                    mx[i] = max(mx[i], hi[i], lo[i])
                idx = p.get("indices")
                if p.get("mode", 4) == 4:
                    tris += (js["accessors"][idx]["count"] // 3) if idx is not None else acc.get("count", 0) // 3
            if mn[0] < 1e8:
                # glTF → Blender 轴: X=宽, Y=深=-Z, Z=高=Y
                b = [mn[0], -mx[2], mn[1]], [mx[0], -mn[2], mx[1]]
                out.append({
                    "name": n.get("name", "?"),
                    "min": [round(v, 4) for v in b[0]],
                    "max": [round(v, 4) for v in b[1]],
                    "dims": [round(b[1][i] - b[0][i], 4) for i in range(3)],
                    "tris": tris,
                })
        for ch in n.get("children", []):
            walk(ch, world)

    roots = js.get("scenes", [{}])[0].get("nodes", list(range(len(nodes))))
    for r in roots:
        walk(r, identity())
    return out


if __name__ == "__main__":
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    path = args[0]
    ps = parts(path)
    ps.sort(key=lambda p: -(p["dims"][0] * p["dims"][1]))
    gmn = [min(p["min"][i] for p in ps) for i in range(3)]
    gmx = [max(p["max"][i] for p in ps) for i in range(3)]
    print("TOTAL dims W/D/H =", [round(gmx[i] - gmn[i], 4) for i in range(3)],
          " min=", [round(v, 4) for v in gmn], " max=", [round(v, 4) for v in gmx])
    print("--- 按占地排序，前 25 ---")
    for p in ps[:25]:
        print(f"{p['name'][:34]:36s} dims={p['dims']} min={p['min']} max={p['max']} tris={p['tris']}")
    print("--- X 方向最外侧 10 ---")
    for p in sorted(ps, key=lambda p: -p["max"][0])[:10]:
        print(f"{p['name'][:34]:36s} x_max={p['max'][0]}  dims={p['dims']}")
    print("--- Y(深) 最外侧 10 ---")
    for p in sorted(ps, key=lambda p: -p["max"][1])[:10]:
        print(f"{p['name'][:34]:36s} y_max={p['max'][1]}  dims={p['dims']}")
    print("--- Z(高) 最高 10 ---")
    for p in sorted(ps, key=lambda p: -p["max"][2])[:10]:
        print(f"{p['name'][:34]:36s} z_max={p['max'][2]}  dims={p['dims']}")

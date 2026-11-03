"""按 Blender 世界坐标列出每个物体的尺寸/位置，定位超出蓝图尺寸的元凶。
坐标映射（实测确证）：Blender X=glTF X, Blender Y=-glTF Z, Blender Z=glTF Y
"""
import json, struct, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from inspect_glb import read_glb, node_local, identity, mat_mul_colmajor, transform_point

path = sys.argv[1]
js = read_glb(path)
nodes = js.get("nodes", []); meshes = js.get("meshes", [])
rows = []


def walk(ni, parent):
    n = nodes[ni]
    w = mat_mul_colmajor(parent, node_local(n))
    if "mesh" in n:
        m = meshes[n["mesh"]]
        mn = [1e9] * 3; mx = [-1e9] * 3
        for p in m.get("primitives", []):
            acc = js["accessors"][p["attributes"]["POSITION"]]
            if "min" not in acc:
                continue
            lo = transform_point(w, acc["min"]); hi = transform_point(w, acc["max"])
            for i in range(3):
                mn[i] = min(mn[i], lo[i], hi[i]); mx[i] = max(mx[i], lo[i], hi[i])
        if mn[0] < 1e8:
            # → Blender
            bx = (mn[0], mx[0]); by = (-mx[2], -mn[2]); bz = (mn[1], mx[1])
            rows.append((n.get("name", "?"), bx, by, bz))
    for ch in n.get("children", []):
        walk(ch, w)


for r in js.get("scenes", [{}])[0].get("nodes", list(range(len(nodes)))):
    walk(r, identity())

print(f"objects={len(rows)}")
print("--- 最大的 15 个（按 X 跨度） ---")
rows.sort(key=lambda r: -(r[1][1] - r[1][0]))
for name, bx, by, bz in rows[:15]:
    print(f"  {name:<22} X[{bx[0]:+.3f},{bx[1]:+.3f}]={bx[1]-bx[0]:.3f} "
          f"Y[{by[0]:+.3f},{by[1]:+.3f}]={by[1]-by[0]:.3f} "
          f"Z[{bz[0]:+.3f},{bz[1]:+.3f}]={bz[1]-bz[0]:.3f}")
print("--- 最高的 10 个（按 Z 上限） ---")
rows.sort(key=lambda r: -r[3][1])
for name, bx, by, bz in rows[:10]:
    print(f"  {name:<22} Ztop={bz[1]:+.3f} Yspan={by[1]-by[0]:.3f} Xspan={bx[1]-bx[0]:.3f}")
print("--- 最低的 8 个（穿地嫌疑） ---")
rows.sort(key=lambda r: r[3][0])
for name, bx, by, bz in rows[:8]:
    print(f"  {name:<22} Zmin={bz[0]:+.3f}")
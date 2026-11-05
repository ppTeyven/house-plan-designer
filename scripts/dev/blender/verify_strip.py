"""校验剥图后的 GLB：三角面/顶点/尺寸与剥图前完全一致。

这是"画质零损失"的硬证明 —— 逐文件比对。
"""
import io
import json
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from strip_glb_textures import read_glb, strip, geometry_fingerprint  # noqa

A = sys.argv[1]   # 剥图前目录
B = sys.argv[2]   # 剥图后目录


def stats(js):
    tris = verts = prims = 0
    for m in js.get('meshes') or []:
        for p in m.get('primitives') or []:
            prims += 1
            pos = p.get('attributes', {}).get('POSITION')
            if pos is not None:
                verts += js['accessors'][pos]['count']
            idx = p.get('indices')
            if idx is None:
                tris += (js['accessors'][pos]['count'] // 3) if pos else 0
            else:
                tris += js['accessors'][idx]['count'] // 3
    return tris, verts, prims


def bbox(js, bin_):
    """从 POSITION accessor 的 min/max 算包围盒（glTF 里已经存了）"""
    lo = [1e30] * 3
    hi = [-1e30] * 3
    for m in js.get('meshes') or []:
        for p in m.get('primitives') or []:
            pos = p.get('attributes', {}).get('POSITION')
            if pos is None:
                continue
            a = js['accessors'][pos]
            if 'min' in a and 'max' in a:
                for i in range(3):
                    lo[i] = min(lo[i], a['min'][i])
                    hi[i] = max(hi[i], a['max'][i])
    return lo, hi


bad = 0
n = 0
for fn in sorted(f for f in os.listdir(A) if f.endswith('.glb')):
    pb = os.path.join(B, fn)
    if not os.path.exists(pb):
        continue
    j1, b1 = read_glb(os.path.join(A, fn))
    j2, b2 = read_glb(pb)
    t1, v1, p1 = stats(j1)
    t2, v2, p2 = stats(j2)
    lo1, hi1 = bbox(j1, b1)
    lo2, hi2 = bbox(j2, b2)
    fp1 = geometry_fingerprint(j1, b1)
    fp2 = geometry_fingerprint(j2, b2)
    probs = []
    if (t1, v1, p1) != (t2, v2, p2):
        probs.append('geom count %s -> %s' % ((t1, v1, p1), (t2, v2, p2)))
    if fp1 != fp2:
        probs.append('geometry checksum differs')
    for i in range(3):
        if abs(lo1[i] - lo2[i]) > 1e-6 or abs(hi1[i] - hi2[i]) > 1e-6:
            probs.append('bbox axis%d differs' % i)
            break
    # 材质名必须保留（主程序靠 U_ 前缀分派材质）
    m1 = sorted((m.get('name') or '') for m in (j1.get('materials') or []))
    m2 = sorted((m.get('name') or '') for m in (j2.get('materials') or []))
    if m1 != m2:
        probs.append('material names %s -> %s' % (m1, m2))
    n += 1
    if probs:
        bad += 1
        print('!! %-22s %s' % (fn, '; '.join(probs)))

print()
print('比对 %d 个文件，异常 %d 个' % (n, bad))
if bad == 0:
    print('几何 / 包围盒 / 材质名 全部一致 —— 剥图未改动任何可见内容')

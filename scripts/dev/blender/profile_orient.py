"""细分高度剖面：把模型按 Z 分 20 段打印每段最高点 + 高于阈值的顶点数。

用途：区分「整端都高（真靠背）」和「两端各有一根高杆（等高）」。
"""
import io
import json
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from verify_orient_glb import load_glb, mesh_world_points  # noqa

FURN = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))))), 'assets', 'furnlib')


def world_points(path):
    j, bin_ = load_glb(path)
    nodes = j.get('nodes', [])
    child_of = {}
    for i, n in enumerate(nodes):
        for c in n.get('children', []):
            child_of[c] = i

    def trs_mat(t, r, s):
        x, y, z, w = r
        x2, y2, z2 = x + x, y + y, z + z
        xx, xy, xz = x * x2, x * y2, x * z2
        yy, yz, zz = y * y2, y * z2, z * z2
        wx, wy, wz = w * x2, w * y2, w * z2
        sx, sy, sz = s
        return [
            (1 - (yy + zz)) * sx, (xy + wz) * sx, (xz - wy) * sx, 0,
            (xy - wz) * sy, (1 - (xx + zz)) * sy, (yz + wx) * sy, 0,
            (xz + wy) * sz, (yz - wx) * sz, (1 - (xx + yy)) * sz, 0,
            t[0], t[1], t[2], 1]

    def mul(a, b):
        o = [0.0] * 16
        for i in range(4):
            for j2 in range(4):
                o[i * 4 + j2] = sum(a[i * 4 + k] * b[k * 4 + j2] for k in range(4))
        return o

    def basis(i):
        n = nodes[i]
        m = list(n['matrix']) if 'matrix' in n else trs_mat(
            n.get('translation', [0, 0, 0]),
            n.get('rotation', [0, 0, 0, 1]),
            n.get('scale', [1, 1, 1]))
        p = i
        while p in child_of:
            p = child_of[p]
            pn = nodes[p]
            pm = list(pn['matrix']) if 'matrix' in pn else trs_mat(
                pn.get('translation', [0, 0, 0]),
                pn.get('rotation', [0, 0, 0, 1]),
                pn.get('scale', [1, 1, 1]))
            m = mul(pm, m)
        return m

    mesh_mats = {}
    for i, n in enumerate(nodes):
        if 'mesh' in n:
            mesh_mats.setdefault(n['mesh'], []).append(basis(i))
    pts = []
    for mi, mats in mesh_mats.items():
        pts.extend(mesh_world_points(j, bin_, mi, mats))
    return pts


def profile(name, nb=20):
    path = os.path.join(FURN, name + '.glb')
    if not os.path.exists(path):
        print(name, 'MISSING')
        return
    pts = world_points(path)
    if not pts:
        print(name, 'NOPTS')
        return
    zmin = min(p[2] for p in pts)
    zmax = max(p[2] for p in pts)
    ymin = min(p[1] for p in pts)
    span = max(zmax - zmin, 1e-9)
    seg_h = [0.0] * nb
    seg_n = [0] * nb
    for (x, y, z) in pts:
        k = min(nb - 1, int((z - zmin) / span * nb))
        seg_n[k] += 1
        h = y - ymin
        if h > seg_h[k]:
            seg_h[k] = h
    print('=== %s  size(z)=%.2f  ymin=%.2f' % (name, span, ymin))
    print('  z-range: %s' % ' '.join(
        '[%5.2f..%5.2f]' % (zmin + span * i / nb, zmin + span * (i + 1) / nb)
        for i in range(0, nb, 4)))
    for i in range(nb):
        bar = '#' * int(seg_h[i] * 30)
        print('  seg%02d z=%+6.2f  h=%.3f  n=%-6d %s' % (
            i, zmin + span * (i + .5) / nb - (zmin + span / 2),
            seg_h[i], seg_n[i], bar))


if __name__ == '__main__':
    for n in sys.argv[1:]:
        profile(n)
        print()

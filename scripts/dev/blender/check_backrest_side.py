"""决定性判据：取模型【最高的那一撮顶点】（靠背顶），看它们的 Z 分布。

床头板 / 靠背 / 背板是家具最高的一撮顶点。
  · 靠背在 -Z → 这撮顶点的平均 Z 应为负
  · 靠背在 +Z → 平均 Z 应为正
这样不受「另一端也有一根高杆」干扰，也不受 L 形家具的形状干扰。
"""
import io
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from verify_orient_glb import load_glb, mesh_world_points  # noqa

FURN = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))))), 'assets', 'furnlib')

KEYS = [
    'bed12', 'bed15', 'bed18', 'bed20', 'kingBed', 'kidsBed', 'bunkBed',
    'dayBed', 'roundBed', 'petBed', 'bedBench',
    'sofa', 'loveseat', 'singleSofa', 'lSofa', 'chaiseSofa', 'uSofa',
    'curvedSofa', 'bendSofa', 'theaterSofa', 'booth', 'officeSofa', 'fourSofa',
    'armchair', 'officeChair', 'trainingChair', 'rockingChair', 'gamingChair',
    'armDiningChair', 'readingChair', 'chair', 'hangingChair',
]


def world_points(path):
    j, bin_ = load_glb(path)
    nodes = j.get('nodes', [])
    child_of = {}
    for i, n in enumerate(nodes):
        for c in n.get('children', []):
            child_of[c] = i

    def trs_mat(t, r, s):
        x, y, z = r[0], r[1], r[2]
        w = r[3]
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


def check(name, top_pct=0.06):
    path = os.path.join(FURN, name + '.glb')
    if not os.path.exists(path):
        return (name, 'MISSING', 0, 0, 0)
    pts = world_points(path)
    if not pts:
        return (name, 'NOPTS', 0, 0, 0)
    ymax = max(p[1] for p in pts)
    # 取最高 top_pct 的顶点（靠背顶）
    thresh = ymax - 0.02
    top = [p for p in pts if p[1] >= thresh]
    if len(top) < 4:
        top = sorted(pts, key=lambda p: -p[1])[:max(4, len(pts) // 50)]
    zs = [p[2] for p in top]
    mz = sum(zs) / len(zs)
    zmin = min(p[2] for p in pts)
    zmax = max(p[2] for p in pts)
    # 归一化：-1 = 完全在 -Z 端，+1 = 完全在 +Z 端
    mid = (zmin + zmax) / 2
    half = max((zmax - zmin) / 2, 1e-9)
    norm = (mz - mid) / half
    if norm < -0.12:
        verdict = 'OK  靠背@-Z'
    elif norm > 0.12:
        verdict = '反了 靠背@+Z'
    else:
        verdict = '居中/对称'
    return (name, verdict, mz, norm, len(top))


if __name__ == '__main__':
    keys = sys.argv[1:] or KEYS
    print('%-16s %-16s %9s %8s %7s' % (
        'model', 'verdict', 'meanZ(top)', 'norm', 'nTop'))
    print('-' * 62)
    bad = []
    for k in keys:
        r = check(k)
        print('%-16s %-16s %9.3f %8.3f %7d' % r)
        if '反了' in r[1]:
            bad.append(r[0])
    print('-' * 62)
    print('朝向反了 %d 件: %s' % (len(bad), ', '.join(bad) if bad else '无'))

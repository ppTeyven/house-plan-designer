"""逐 mesh/primitive 打印 GLB 内部各部件的 Z 范围与最大高度。

用于判断「靠背/床头」到底落在哪一端，以及是否存在整体镜像。
"""
import io
import json
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from verify_orient_glb import load_glb, CT, NC  # noqa

FURN = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))))), 'assets', 'furnlib')


def dump(name):
    path = os.path.join(FURN, name + '.glb')
    if not os.path.exists(path):
        print(name, 'MISSING')
        return
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
    mesh_names = {}
    for i, n in enumerate(nodes):
        if 'mesh' in n:
            mesh_mats.setdefault(n['mesh'], []).append(basis(i))
            mesh_names.setdefault(n['mesh'], n.get('name', ''))

    print('=== %s' % name)
    rows = []
    for mi, mats in sorted(mesh_mats.items()):
        for prim in j['meshes'][mi]['primitives']:
            acc = j['accessors'][prim['attributes']['POSITION']]
            bv = j['bufferViews'][acc['bufferView']]
            fmt, size = CT[acc['componentType']]
            n3 = NC[acc['type']]
            vstride = bv.get('byteStride') or (size * n3)
            base = bv.get('byteOffset', 0)
            astart = base + acc.get('byteOffset', 0)
            zs, ys = [], []
            for m in mats:
                for k in range(acc['count']):
                    v = struct.unpack_from('<' + fmt * n3, bin_, astart + k * vstride)
                    if n3 < 3:
                        continue
                    x, y, z = v[0], v[1], v[2]
                    zs.append(m[2] * x + m[6] * y + m[10] * z + m[14])
                    ys.append(m[1] * x + m[5] * y + m[9] * z + m[13])
            if not zs:
                continue
            mat = prim.get('material')
            matname = ''
            if mat is not None:
                matname = j['materials'][mat].get('name', '')
            rows.append((min(zs), max(zs), min(ys), max(ys),
                         len(zs), mesh_names.get(mi, ''), matname))
    rows.sort(key=lambda r: r[0])
    print('  %-9s %-9s %-9s %-9s %-8s %-14s %s' % (
        'zMin', 'zMax', 'yMin', 'yMax', 'nVerts', 'node', 'material'))
    for r in rows:
        print('  %-9.3f %-9.3f %-9.3f %-9.3f %-8d %-14s %s' % r)


if __name__ == '__main__':
    for n in sys.argv[1:]:
        dump(n)
        print()

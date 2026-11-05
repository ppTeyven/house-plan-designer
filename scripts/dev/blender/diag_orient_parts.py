"""诊断：给 Mesh.add_box / add_cylinder 打补丁，记录每个构件的最终 Z 范围。

用来回答「靠背到底落在哪一端」—— 直接看构件清单，而不是猜高度剖面。
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import geo_gen  # noqa
import geo_models as GM  # noqa
import fit_item as FI  # noqa

LOG = []

_orig_box = geo_gen.Mesh.add_box
_orig_cyl = geo_gen.Mesh.add_cylinder


def p_box(self, size, center=(0, 0, 0), mat="U_wood_walnut", rot=None):
    LOG.append(('box', tuple(size), tuple(center), mat))
    return _orig_box(self, size, center, mat, rot)


def p_cyl(self, r, h, center=(0, 0, 0), seg=16, mat="U_wood_walnut",
          radius_top=None):
    LOG.append(('cyl', (r, h), tuple(center), mat))
    return _orig_cyl(self, r, h, center, seg, mat, radius_top)


geo_gen.Mesh.add_box = p_box
geo_gen.Mesh.add_cylinder = p_cyl

SIZES = FI.load_sizes()


def dump(key):
    LOG.clear()
    if key not in GM.BUILDERS:
        print('%-14s no builder' % key)
        return
    tgt = SIZES.get(key)
    params = {}
    if tgt:
        params = {'w': tgt[0], 'd': tgt[1], 'h': tgt[2]}
    m = GM.build(key, params)
    zs = [p[2] for p in m.pos]
    ys = [p[1] for p in m.pos]
    zmin, zmax = min(zs), max(zs)
    print('=== %s  z[%.3f..%.3f]  y[%.3f..%.3f]  parts=%d'
          % (key, zmin, zmax, min(ys), max(ys), len(LOG)))
    rows = []
    for kind, size, c, mat in LOG:
        if kind == 'box':
            w, h, d = size
            z0, z1 = c[2] - d / 2, c[2] + d / 2
            y0, y1 = c[1] - h / 2, c[1] + h / 2
        else:
            r, h = size
            z0, z1 = c[2] - r, c[2] + r
            y0, y1 = c[1] - h / 2, c[1] + h / 2
        rows.append((z0, z1, y0, y1, kind, mat))
    rows.sort(key=lambda r: r[0])
    for z0, z1, y0, y1, kind, mat in rows:
        flag = '  <== 高件' if (y1 - min(ys)) > 0.75 else ''
        print('   %-4s z[%+6.3f..%+6.3f] y[%6.3f..%6.3f] %-16s%s'
              % (kind, z0, z1, y0, y1, mat, flag))


if __name__ == '__main__':
    for k in sys.argv[1:]:
        dump(k)
        print()

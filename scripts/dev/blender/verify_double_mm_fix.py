"""修复后回归检查：
1. 每个受影响模型的最终尺寸 == 目录目标尺寸
2. 没有「被压扁的小部件」（tiny part）
"""
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import geo_gen  # noqa
import geo_models as GM  # noqa
import fit_item as FI  # noqa

RAW = []
_ob = geo_gen.Mesh.add_box
_oc = geo_gen.Mesh.add_cylinder


def p_box(self, size, center=(0, 0, 0), mat="U_wood_walnut", rot=None):
    RAW.append(('box', tuple(size)))
    return _ob(self, size, center, mat, rot)


def p_cyl(self, r, h, center=(0, 0, 0), seg=16, mat="U_wood_walnut",
          radius_top=None):
    RAW.append(('cyl', (r, h)))
    return _oc(self, r, h, center, seg, mat, radius_top)


geo_gen.Mesh.add_box = p_box
geo_gen.Mesh.add_cylinder = p_cyl

SIZES = FI.load_sizes()
AFFECTED = ['barCounter', 'barStool', 'bayCushion', 'booth', 'bunkBed',
            'cabCorner', 'cabSlide', 'cabTV', 'crib', 'curveTrainingTable',
            'fireplace', 'gamingChair', 'lDesk', 'lectern', 'ovalTable',
            'reception', 'speaker', 'tatami', 'theaterSofa']

print('%-22s %-26s %-24s %6s %6s' % (
    'model', 'final (w x d x h) m', 'target (w,d,h) mm', 'parts', 'tiny'))
print('-' * 92)
bad = []
for k in AFFECTED:
    if k not in GM.BUILDERS:
        print('%-22s no builder' % k)
        continue
    tgt = SIZES.get(k)
    params = {'w': tgt[0], 'd': tgt[1], 'h': tgt[2]} if tgt else {}
    RAW.clear()
    try:
        m = GM.build(k, params)
    except Exception as e:
        print('%-22s BUILD ERROR %s' % (k, e))
        bad.append(k)
        continue
    xs = [p[0] for p in m.pos]
    zs = [p[2] for p in m.pos]
    ys = [p[1] for p in m.pos]
    final = (max(xs) - min(xs), max(zs) - min(zs), max(ys) - min(ys))
    tiny = 0
    for kind, size in RAW:
        dims = size if kind == 'box' else (size[0] * 2, size[0] * 2, size[1])
        if min(dims) < 0.0015 and max(dims) > 0.0001:
            tiny += 1
    dev = 0.0
    if tgt:
        exp = [tgt[0] / 1000, tgt[1] / 1000, tgt[2] / 1000]
        dev = max(abs(final[i] - exp[i]) / max(exp[i], 1e-6) for i in range(3))
    flag = ''
    if dev > 0.05 or tiny:
        flag = '  <== 仍有问题'
        bad.append(k)
    print('%-22s %-26s %-24s %6d %6d  dev=%.1f%%%s' % (
        k, '%.3f x %.3f x %.3f' % final,
        '%d x %d x %d' % tuple(tgt) if tgt else '',
        len(RAW), tiny, dev * 100, flag))

print('-' * 92)
print('仍有问题 %d 件: %s' % (len(bad), ', '.join(bad) if bad else '无'))

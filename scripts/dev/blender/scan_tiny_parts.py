"""检测 double-MM 造成的形变：对每个 builder，
比较【原始 add_box 参数】与【最终 GLB 实际尺寸】。

如果一个 builder 存在二次换算，那么它生成的模型里
「按字面量 mm 给出的部件」与「按变量给出的部件」比例会严重失衡。
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import geo_gen  # noqa
import geo_models as GM  # noqa
import fit_item as FI  # noqa

RAW = []

_orig_box = geo_gen.Mesh.add_box
_orig_cyl = geo_gen.Mesh.add_cylinder


def p_box(self, size, center=(0, 0, 0), mat="U_wood_walnut", rot=None):
    RAW.append(('box', tuple(size), tuple(center)))
    return _orig_box(self, size, center, mat, rot)


def p_cyl(self, r, h, center=(0, 0, 0), seg=16, mat="U_wood_walnut",
          radius_top=None):
    RAW.append(('cyl', (r, h), tuple(center)))
    return _orig_cyl(self, r, h, center, seg, mat, radius_top)


geo_gen.Mesh.add_box = p_box
geo_gen.Mesh.add_cylinder = p_cyl

SIZES = FI.load_sizes()


def check(key):
    if key not in GM.BUILDERS:
        return None
    tgt = SIZES.get(key)
    params = {}
    if tgt:
        params = {'w': tgt[0], 'd': tgt[1], 'h': tgt[2]}
    RAW.clear()
    try:
        m = GM.build(key, params)
    except Exception:
        return None
    zs = [p[2] for p in m.pos]
    ys = [p[1] for p in m.pos]
    xs = [p[0] for p in m.pos]
    final = (max(xs) - min(xs), max(zs) - min(zs), max(ys) - min(ys))

    # 找出被二次换算压扁的部件：原始尺寸 < 1mm 的
    tiny = []
    for kind, size, c in RAW:
        if kind == 'box':
            dims = size
        else:
            dims = (size[0] * 2, size[0] * 2, size[1])
        if min(dims) < 0.0015 and max(dims) > 0.0001:
            tiny.append((kind, dims, c))
    return {
        'key': key, 'final': final, 'target': tgt,
        'nparts': len(RAW), 'ntiny': len(tiny),
        'tiny': tiny[:6],
        'raw_max': max(max((size if kind == 'box' else (size[0] * 2, size[0] * 2, size[1])))
                       for kind, size, c in RAW) if RAW else 0,
    }


KEYS = sys.argv[1:] or sorted(SIZES.keys())

if __name__ == '__main__':
    print('%-18s %-22s %-22s %6s %6s' % (
        'model', 'final (x,y,z) m', 'target (w,d,h) mm', 'parts', 'tiny'))
    print('-' * 84)
    bad = []
    for k in KEYS:
        r = check(k)
        if not r:
            continue
        f = r['final']
        t = r['target'] or [0, 0, 0]
        flag = ''
        if r['ntiny']:
            flag = '  <== 二次换算'
            bad.append(k)
        print('%-18s %-22s %-22s %6d %6d%s' % (
            k,
            '%.3f x %.3f x %.3f' % (f[0], f[2], f[1]),
            '%d x %d x %d' % (t[0], t[1], t[2]) if t else '',
            r['nparts'], r['ntiny'], flag))
    print('-' * 84)
    print('疑似二次换算 %d 件: %s' % (len(bad), ', '.join(bad)))

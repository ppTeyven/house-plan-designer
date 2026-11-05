"""直接调用 builder（不经过 GLB）检查几何朝向，并与已发布 GLB 对比。

这样能区分两种情况：
  A. builder 本身就是错的 → 源码要改
  B. builder 对，但发布流程把它改了 → 导出链路要查
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import geo_models as GM  # noqa
import fit_item as FI  # noqa

SIZES = FI.load_sizes()


def mesh_profile(m, nb=20):
    """对 Mesh 对象直接做 Z 向高度剖面。"""
    if not m.pos:
        return None
    zs = [p[2] for p in m.pos]
    ys = [p[1] for p in m.pos]
    zmin, zmax = min(zs), max(zs)
    ymin = min(ys)
    span = max(zmax - zmin, 1e-9)
    seg = [0.0] * nb
    cnt = [0] * nb
    for p in m.pos:
        k = min(nb - 1, int((p[2] - zmin) / span * nb))
        cnt[k] += 1
        h = p[1] - ymin
        if h > seg[k]:
            seg[k] = h
    return seg, cnt, (zmin, zmax), ymin


def report(keys):
    for key in keys:
        if key not in GM.BUILDERS:
            print('%-16s no builder' % key)
            continue
        tgt = SIZES.get(key)
        params = {}
        if tgt:
            params = {'w': tgt[0], 'd': tgt[1], 'h': tgt[2]}
        try:
            m = GM.build(key, params)
        except Exception as e:
            print('%-16s build error: %s' % (key, e))
            continue
        r = mesh_profile(m)
        if not r:
            print('%-16s empty' % key)
            continue
        seg, cnt, (zmin, zmax), ymin = r
        nb = len(seg)

        def med(v):
            v = sorted(v)
            return v[len(v) // 2] if v else 0.0

        edge = max(2, nb // 4)
        low = med(seg[:edge])
        high = med(seg[nb - edge:])
        print('%-16s z[%.2f..%.2f]  -Z端%.3f  +Z端%.3f  diff%+.3f  %s'
              % (key, zmin, zmax, low, high, low - high,
                 'OK 靠背-Z' if low - high > 0.05 else
                 ('反了' if high - low > 0.05 else '对称/无靠背')))
        # 打印剖面
        for i in range(nb):
            bar = '#' * int(seg[i] * 26)
            print('      seg%02d z=%+6.2f h=%.3f n=%-5d %s'
                  % (i, zmin + (zmax - zmin) * (i + .5) / nb - (zmin + zmax) / 2,
                     seg[i], cnt[i], bar))


if __name__ == '__main__':
    report(sys.argv[1:])

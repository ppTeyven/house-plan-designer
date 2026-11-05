"""验证指定 builder 的靠背/床头位置（打印所有薄板部件的 z 位置）。

用法：python verify_orient.py build_bed build_sofa ...
"""
import inspect
import os
import sys

BL = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BL)

import geo_models as G
MODS = []
for nm in ('geo_models_free', 'geo_models_extra', 'geo_models_extra2',
           'geo_models_extra3', 'geo_models_extra4'):
    try:
        MODS.append(__import__(nm))
    except Exception:
        pass


def build_registry():
    reg = {}
    for mod in [G] + MODS:
        for attr in dir(mod):
            if attr.startswith('build_') and callable(getattr(mod, attr)):
                reg.setdefault(attr, getattr(mod, attr))
    return reg


def call_builder(fn):
    sig = inspect.signature(fn)
    kwargs = {}
    for pname, p in sig.parameters.items():
        if p.default is not inspect.Parameter.empty:
            continue
        if 'seat' in pname:
            kwargs[pname] = 3
        elif 'w' in pname:
            kwargs[pname] = 1800
        elif 'd' in pname:
            kwargs[pname] = 1000
        elif 'h' in pname:
            kwargs[pname] = 900
        else:
            kwargs[pname] = 1
    return fn(**kwargs)


def main():
    reg = build_registry()
    names = sys.argv[1:] or sorted(reg)
    for name in names:
        if name not in reg:
            print('%-26s 未知 builder' % name)
            continue
        mesh = call_builder(reg[name])
        # 按材质分组看包围盒
        groups = {}
        for tri, mi in zip(mesh.idx, mesh.mats):
            groups.setdefault(mi, []).append(tri)
        zmin = min(p[2] for p in mesh.pos)
        zmax = max(p[2] for p in mesh.pos)
        depth = zmax - zmin
        print('=== %-24s  z 范围 [%.2f, %.2f]' % (name, zmin, zmax))
        rows = []
        for mi, tris in groups.items():
            zs = [mesh.pos[v][2] for t in tris for v in t]
            ys = [mesh.pos[v][1] for t in tris for v in t]
            xs = [mesh.pos[v][0] for t in tris for v in t]
            dz = max(zs) - min(zs)
            dy = max(ys) - min(ys)
            dx = max(xs) - min(xs)
            zc = (max(zs) + min(zs)) / 2
            rows.append((abs(zc), mesh.mat_names[mi], zc, dz, dy, dx))
        rows.sort(reverse=True)
        for _, mat, zc, dz, dy, dx in rows:
            tag = ''
            if dz < depth * 0.25 and dy > 0.25 and dx > 0.25:
                tag = '  <== 竖直板 @ %sZ' % ('+' if zc > 0 else '-')
            print('    %-22s zc=%+.3f dz=%.2f dy=%.2f dx=%.2f%s'
                  % (mat[:22], zc, dz, dy, dx, tag))
        print()


if __name__ == '__main__':
    main()

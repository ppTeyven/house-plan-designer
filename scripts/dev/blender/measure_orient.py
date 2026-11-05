"""按"Z 轴高度剖面"判定靠背侧 —— 不依赖连通域。

【原理】
    沿 Z 轴把模型切成若干薄片，每片统计该片的最大高度。
    靠背所在的一端 → 该端的最高点远高于另一端（靠背从地面到顶）。
    床/沙发/椅子的"靠背端"高度明显高于"开放端"。

    对比两端的最大高度：靠背端更高。
    → 最高的那一端在 +Z 还是 -Z，就得出靠背侧。

【主程序约定 -Z】assets/template.html 的 kv()：
    3D 位置 l.position.set(r.x/1e3, c/1e3, r.y/1e3)
      ⇒ 2D 平面图的 -Y（图纸上方）= 3D 的 -Z
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
        pl = pname.lower()
        if 'seat' in pl or 'segment' in pl:
            kwargs[pname] = 3
        elif 'arc' in pl:
            kwargs[pname] = 90.0
        elif 'w' in pl:
            kwargs[pname] = 1800
        elif 'd' in pl:
            kwargs[pname] = 1000
        elif 'h' in pl:
            kwargs[pname] = 900
        else:
            kwargs[pname] = 1
    return fn(**kwargs)


def height_profile(mesh, slices=12):
    """返回 [(z中点, 该片最大高度)]"""
    if not mesh.pos:
        return []
    zmin = min(p[2] for p in mesh.pos)
    zmax = max(p[2] for p in mesh.pos)
    span = max(zmax - zmin, 1e-6)
    buckets = [[] for _ in range(slices)]
    for p in mesh.pos:
        k = min(slices - 1, int((p[2] - zmin) / span * slices))
        buckets[k].append(p[1])
    prof = []
    for k, b in enumerate(buckets):
        zc = zmin + (k + 0.5) * span / slices
        prof.append((zc, max(b) if b else 0.0))
    return prof


def main():
    reg = build_registry()
    names = sys.argv[1:] or sorted(reg)
    print('%-26s %-14s %-14s %s' % ('builder', '负端最大高', '正端最大高', '判定'))
    print('-' * 74)
    for name in names:
        if name not in reg:
            continue
        try:
            mesh = call_builder(reg[name])
        except Exception:
            continue
        prof = height_profile(mesh)
        if not prof:
            continue
        half = len(prof) // 2
        neg = max(h for _, h in prof[:half]) if half else 0
        pos = max(h for _, h in prof[half:]) if half else 0
        if max(neg, pos) < 1e-6:
            continue
        if neg > pos * 1.15:
            verdict = '靠背 -Z  OK'
        elif pos > neg * 1.15:
            verdict = '靠背 +Z  反了'
        else:
            verdict = '两端相近（对称/无明显靠背）'
        print('%-26s %-14.2f %-14.2f %s' % (name, neg, pos, verdict))


if __name__ == '__main__':
    main()

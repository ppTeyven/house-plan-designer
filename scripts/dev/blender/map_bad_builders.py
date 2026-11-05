"""把「存在二次单位换算」的 builder 函数映射到具体的款式 key。"""
import inspect
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import geo_models as GM  # noqa
import geo_models_extra as E1  # noqa
import geo_models_extra2 as E2  # noqa
import geo_models_extra3 as E3  # noqa
import geo_models_extra4 as E4  # noqa
import geo_models_free as EF  # noqa

BAD_FUNCS = {
    'build_theater_sofa', 'build_booth', 'build_l_desk', 'build_bar_counter',
    'build_curve_training_table', 'build_lectern', 'build_reception',
    'build_bunk_bed', 'build_crib', 'build_tatami', 'build_bay_cushion',
    'build_sliding_wardrobe', 'build_corner_wardrobe',
    'build_floating_tv_cabinet', 'build_gaming_chair', 'build_fireplace',
    'build_speaker', 'build_bar_stool', 'build_oval_table',
}

# 反查每个 key 的 lambda 里调用了哪个函数
import re  # noqa

key2func = {}
for mod in (GM, E1, E2, E3, E4, EF):
    pass

# 直接扫源码里的 lambda 映射
for src_mod, attr in ((E1, 'EXTRA_BUILDERS'), (E2, 'EXTRA2'),
                      (E3, 'EXTRA3'), (E4, 'EXTRA4'), (EF, 'FREE')):
    d = getattr(src_mod, attr)
    for key, fn in d.items():
        try:
            src = inspect.getsource(fn)
        except Exception:
            src = ''
        for bf in BAD_FUNCS:
            if bf + '(' in src:
                key2func.setdefault(key, []).append(bf)

print('=== 受影响款式 key -> builder ===')
for k in sorted(key2func):
    print('  %-22s %s' % (k, ', '.join(key2func[k])))
print('\n合计 %d 个 key' % len(key2func))

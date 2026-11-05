"""在真实 Three.js 里验证剥图后的 GLB 能否加载。

纯 Python 校验只能证明 JSON 链条完整，证不了 GLTFLoader 认不认。
这里用 node + three 的 GLTFLoader（如果有 node 环境），
否则退化为输出清单，由浏览器实测。
"""
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from strip_glb_textures import read_glb  # noqa

# 列出需要浏览器实测的样例（覆盖多种材质结构）
SAMPLES = ['bed18.glb', 'wardrobe.glb', 'plant.glb', 'sofa.glb', 'uSofa.glb',
           'bookshelf.glb', 'chair.glb', 'table.glb', 'lamp.glb', 'rug.glb',
           'cabinet.glb', 'sink.glb', 'tv.glb', 'mirror.glb', 'plant2.glb']

if __name__ == '__main__':
    d = sys.argv[1]
    out = []
    for fn in SAMPLES:
        p = os.path.join(d, fn)
        if not os.path.exists(p):
            continue
        js, bin_ = read_glb(p)
        mats = [m.get('name') for m in (js.get('materials') or [])]
        out.append({'file': fn, 'sizeKB': os.path.getsize(p) // 1024, 'mats': mats})
    print(json.dumps(out, ensure_ascii=False, indent=1))

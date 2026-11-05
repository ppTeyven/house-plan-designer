# -*- coding: utf-8 -*-
"""裁切 + 放大截图区域，便于肉眼看细节。"""
import io
import os
import sys

try:
    from PIL import Image
except ImportError:
    print('NO PIL')
    raise SystemExit(1)

SRC = r'D:\house planner\house-plan-designer-main\scripts\dev\blender\_shots'
OUT = os.path.join(SRC, 'crops')
os.makedirs(OUT, exist_ok=True)

name = sys.argv[1] if len(sys.argv) > 1 else 'aerial_real.png'
im = Image.open(os.path.join(SRC, name)).convert('RGB')
W, H = im.size
print('source', name, W, 'x', H)

# 切成 2x2 并放大 2 倍
for i in range(2):
    for j in range(2):
        box = (W * j // 2, H * i // 2, W * (j + 1) // 2, H * (i + 1) // 2)
        c = im.crop(box)
        c = c.resize((c.width * 2, c.height * 2), Image.LANCZOS)
        p = os.path.join(OUT, '%s_q%d%d.png' % (name.replace('.png', ''), i, j))
        c.save(p)
        print('wrote', p, c.size)

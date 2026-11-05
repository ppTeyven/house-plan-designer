# -*- coding: utf-8 -*-
"""Crop + upscale arbitrary regions of a render for close visual inspection."""
import os, sys
from PIL import Image

SRC = sys.argv[1]
TAG = sys.argv[2]
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '_shots')
os.makedirs(OUT, exist_ok=True)

im = Image.open(SRC).convert('RGB')
W, H = im.size
print('source', W, H)

# name,x,y,w,h in fractions
REGIONS = [
    ('a_left',  0.00, 0.25, 0.34, 0.45),
    ('b_mid',   0.30, 0.20, 0.36, 0.50),
    ('c_right', 0.62, 0.22, 0.38, 0.48),
    ('d_floor', 0.10, 0.58, 0.45, 0.40),
    ('e_ceil',  0.25, 0.00, 0.50, 0.30),
]

for name, fx, fy, fw, fh in REGIONS:
    x = int(fx * W); y = int(fy * H)
    w = int(fw * W); h = int(fh * H)
    x = max(0, min(x, W - 1)); y = max(0, min(y, H - 1))
    w = min(w, W - x); h = min(h, H - y)
    crop = im.crop((x, y, x + w, y + h))
    scale = max(1, min(4, 1500 // max(crop.size)))
    if scale > 1:
        crop = crop.resize((crop.width * scale, crop.height * scale), Image.LANCZOS)
    p = os.path.join(OUT, '%s_%s.png' % (TAG, name))
    crop.save(p)
    print(name, 'box', (x, y, w, h), '->', crop.size)

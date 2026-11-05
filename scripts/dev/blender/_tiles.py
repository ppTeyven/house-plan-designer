# -*- coding: utf-8 -*-
"""Split a render into overlapping tiles so each can be inspected at readable zoom."""
import sys, os
from PIL import Image

src = sys.argv[1]
outdir = sys.argv[2]
os.makedirs(outdir, exist_ok=True)
im = Image.open(src).convert('RGB')
W, H = im.size
print(f"{src} {W}x{H}")

# 4 quadrants with 12% overlap
tiles = {
    'tl': (0.00, 0.00, 0.56, 0.56),
    'tr': (0.44, 0.00, 0.56, 0.56),
    'bl': (0.00, 0.44, 0.56, 0.56),
    'br': (0.44, 0.44, 0.56, 0.56),
}
for name, (rx, ry, rw, rh) in tiles.items():
    box = (int(rx*W), int(ry*H), int((rx+rw)*W), int((ry+rh)*H))
    c = im.crop(box).resize((int(box[2]-box[0])*2, int(box[3]-box[1])*2), Image.LANCZOS)
    p = os.path.join(outdir, f"{name}.png")
    c.save(p)
    print("saved", p, c.size)

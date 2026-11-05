# -*- coding: utf-8 -*-
"""Sample the actual rendered floor pixels under the 3D camera and report
per-region average colour, to detect floors that went missing / turned grey."""
import sys
from collections import Counter
from PIL import Image

path = sys.argv[1]
im = Image.open(path).convert('RGB')
W, H = im.size
px = im.load()
print(f"{path} {W}x{H}")

pts = []
for gy in range(6):
    for gx in range(8):
        x = int(W * (0.06 + gx * 0.125))
        y = int(H * (0.42 + gy * 0.09))
        r, g, b = px[x, y]
        mx, mn = max(r, g, b), min(r, g, b)
        sat = 0 if mx == 0 else (mx - mn) / mx
        if mx > 245 and sat < 0.06:
            k = "white"
        elif mx > 225 and sat < 0.10:
            k = "lightgrey"
        elif mx > 190 and sat < 0.12:
            k = "grey"
        elif mx < 60:
            k = "black"
        elif sat > 0.30:
            k = "warm/wood"
        elif sat > 0.15:
            k = "tinted"
        else:
            k = "grey2"
        pts.append((x, y, r, g, b, k))

c = Counter(p[5] for p in pts)
print("classification:", dict(c))
print()
for x, y, r, g, b, k in pts:
    print(f"({x:4d},{y:4d}) rgb=({r:3d},{g:3d},{b:3d}) {k}")

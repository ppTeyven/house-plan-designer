# -*- coding: utf-8 -*-
"""Objective pixel analysis of a 3D render: detect contact-shadow darkening near
floor edges / furniture bases by comparing neighbouring pixels along horizontal runs.
"""
import sys, json
from PIL import Image

path = sys.argv[1]
im = Image.open(path).convert('RGB')
W, H = im.size
px = im.load()
print(f"{path}  {W}x{H}")

def lum(x, y):
    r, g, b = px[x, y]
    return 0.2126 * r + 0.7152 * g + 0.0722 * b

# 1) global histogram spread
vals = []
for y in range(0, H, 3):
    for x in range(0, W, 3):
        vals.append(lum(x, y))
vals.sort()
n = len(vals)
print(f"luminance: min={vals[0]:.1f} p1={vals[n//100]:.1f} p10={vals[n//10]:.1f} "
      f"med={vals[n//2]:.1f} p90={vals[9*n//10]:.1f} p99={vals[99*n//100]:.1f} max={vals[-1]:.1f}")
print(f"std={ (sum((v-vals[n//2])**2 for v in vals)/n)**0.5:.2f}")

# 2) edge energy (high-frequency contrast) -> how much contact detail exists
def line_edges(y):
    e = 0
    for x in range(1, W):
        e += abs(lum(x, y) - lum(x-1, y))
    return e / max(1, W-1)

band = [line_edges(y) for y in range(H)]
band_sorted = sorted(band)
print(f"horizontal edge energy: mean={sum(band)/len(band):.2f} "
      f"p50={band_sorted[len(band)//2]:.2f} p90={band_sorted[9*len(band)//10]:.2f} max={max(band):.2f}")

# 3) local minima ratio: fraction of pixels that are darker than both horizontal
#    neighbours by > threshold -> detects thin shadow lines under furniture
thr = 8
dark_runs = 0
for y in range(1, H-1):
    for x in range(1, W-1):
        c = lum(x, y)
        if c < lum(x-1, y) - thr and c < lum(x+1, y) - thr:
            dark_runs += 1
print(f"thin-shadow-line pixels (darker than both neighbours by >{thr}): {dark_runs} "
      f"({100.0*dark_runs/((W-2)*(H-2)):.3f}%)")

# 4) sample specific bands: top (ceiling/background) vs bottom (floor)
def bandavg(y0, y1):
    s = 0; c = 0
    for y in range(y0, min(y1, H)):
        for x in range(0, W, 2):
            s += lum(x, y); c += 1
    return s/max(1, c)
print(f"band avg  top(0-12%)={bandavg(0, int(H*0.12)):.1f} "
      f"mid(40-60%)={bandavg(int(H*0.4), int(H*0.6)):.1f} "
      f"bottom(88-100%)={bandavg(int(H*0.88), H):.1f}")

# -*- coding: utf-8 -*-
"""Crop the same region from N images and stack them side-by-side with labels,
so AO on/off differences are visible at a glance."""
import sys, os
from PIL import Image, ImageDraw

args = sys.argv[1:]
out = args[0]
files = args[1:]
# region: x y w h  (fractions of image, may be given as 4 floats)
rx, ry, rw, rh = 0.0, 0.0, 1.0, 1.0
if len(files) >= 2 and ',' in files[-1]:
    spec = files.pop().split(',')
    rx, ry, rw, rh = [float(v) for v in spec]

imgs = []
for f in files:
    im = Image.open(f).convert('RGB')
    W, H = im.size
    box = (int(rx*W), int(ry*H), int((rx+rw)*W), int((ry+rh)*H))
    imgs.append((os.path.basename(f), im.crop(box)))

if not imgs:
    print("no images"); sys.exit(1)

# upscale crop 2x for visibility
scale = 2
cw, ch = imgs[0][1].size
cw *= scale; ch *= scale
label_h = 26
pad = 8
total_w = pad + len(imgs)*(cw+pad)
total_h = label_h + ch + pad
canvas = Image.new('RGB', (total_w, total_h), (24, 26, 30))
d = ImageDraw.Draw(canvas)

x = pad
for name, im in imgs:
    im = im.resize((cw, ch), Image.LANCZOS)
    d.text((x+2, 6), name, fill=(230, 230, 235))
    canvas.paste(im, (x, label_h))
    x += cw + pad

canvas.save(out)
print(f"saved {out} {canvas.size}  region=({rx},{ry},{rw},{rh}) files={[n for n,_ in imgs]}")

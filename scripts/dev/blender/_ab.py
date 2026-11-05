# -*- coding: utf-8 -*-
"""Side-by-side A/B comparison of two renders over the same crop region."""
import os, sys
from PIL import Image, ImageDraw

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '_shots')
A, B = sys.argv[1], sys.argv[2]
TAG = sys.argv[3]
fx, fy, fw, fh = [float(v) for v in sys.argv[4:8]]
scale_to = int(sys.argv[8]) if len(sys.argv) > 8 else 760

ia = Image.open(A).convert('RGB')
ib = Image.open(B).convert('RGB')
W, H = ia.size
x, y = int(fx * W), int(fy * H)
w, h = int(fw * W), int(fh * H)
x = max(0, min(x, W - 1)); y = max(0, min(y, H - 1))
w = min(w, W - x); h = min(h, H - y)

ca = ia.crop((x, y, x + w, y + h))
cb = ib.crop((x, y, x + w, y + h))
s = max(1, scale_to // max(ca.size))
ca = ca.resize((ca.width * s, ca.height * s), Image.LANCZOS)
cb = cb.resize((cb.width * s, cb.height * s), Image.LANCZOS)

canvas = Image.new('RGB', (ca.width + cb.width + 8, max(ca.height, cb.height)), (255, 0, 255))
canvas.paste(ca, (0, 0))
canvas.paste(cb, (ca.width + 8, 0))
p = os.path.join(OUT, 'ab_%s.png' % TAG)
canvas.save(p)
print('A=%s B=%s' % (os.path.basename(A), os.path.basename(B)))
print('crop', (x, y, w, h), 'scale', s, '->', canvas.size, p)

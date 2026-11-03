"""裁剪放大渲染图的局部，用来核对细节（抱枕、扶手、缝线）。

用法：python crop.py <src.png> <out.png> <left%> <top%> <right%> <bottom%>
"""
import sys
from PIL import Image

src, out = sys.argv[1], sys.argv[2]
l, t, r, b = [float(x) / 100.0 for x in sys.argv[3:7]]
im = Image.open(src)
W, H = im.size
box = (int(W * l), int(H * t), int(W * r), int(H * b))
im2 = im.crop(box)
# 放大 2.5 倍（LANCZOS 保持清晰）
im2 = im2.resize((int(im2.width * 2.5), int(im2.height * 2.5)), Image.LANCZOS)
im2.save(out)
print("cropped %s -> %s  %dx%d" % (src, out, im2.width, im2.height))

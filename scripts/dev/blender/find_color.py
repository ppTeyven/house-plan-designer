"""在渲染图里定位指定颜色区域 —— 回答"抱枕到底有没有出现在画面上"。

用法：python find_color.py <png> <r> <g> <b> [tol]
"""
import sys
from PIL import Image

path = sys.argv[1]
tr, tg, tb = [float(x) for x in sys.argv[2:5]]
tol = float(sys.argv[5]) if len(sys.argv) > 5 else 40.0

im = Image.open(path).convert('RGB')
W, H = im.size
px = im.load()

pts = []
for y in range(0, H, 2):
    for x in range(0, W, 2):
        r, g, b = px[x, y]
        if abs(r - tr) < tol and abs(g - tg) < tol and abs(b - tb) < tol:
            pts.append((x, y))

if not pts:
    print("NO MATCH for rgb(%.0f,%.0f,%.0f) tol=%.0f in %s" % (tr, tg, tb, tol, path))
else:
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    print("MATCH %d px  bbox x[%d..%d] y[%d..%d]  (img %dx%d)"
          % (len(pts), min(xs), max(xs), min(ys), max(ys), W, H))
    # 聚类成几个大致区块
    pts.sort()
    clusters = []
    for p in pts:
        placed = False
        for c in clusters:
            if (p[0] - c[0][0]) ** 2 + (p[1] - c[0][1]) ** 2 < 120 ** 2:
                c.append(p)
                placed = True
                break
        if not placed:
            clusters.append([p])
    for c in clusters:
        if len(c) < 20:
            continue
        cx = [q[0] for q in c]
        cy = [q[1] for q in c]
        print("   区块: %5d px  x[%d..%d] y[%d..%d]  中心(%.0f,%.0f)"
              % (len(c), min(cx), max(cx), min(cy), max(cy),
                 sum(cx) / len(cx), sum(cy) / len(cy)))

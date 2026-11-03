"""采样渲染图里最饱和的像素，看抱枕到底渲成了什么颜色。"""
import sys
from PIL import Image
import numpy as np

path = sys.argv[1]
im = Image.open(path).convert('RGB')
a = np.asarray(im).astype(np.float32) / 255.0
mx = a.max(axis=2); mn = a.min(axis=2)
sat = (mx - mn) / np.maximum(mx, 1e-6)
ys, xs = np.where(sat > 0.08)
print(f"file={path}  pixels with sat>0.08: {len(ys)}")
if len(ys):
    order = np.argsort(-sat[ys, xs])[:12]
    print("--- 饱和度最高的 12 个像素 ---")
    for i in order:
        y, x = ys[i], xs[i]
        print(f"  ({x:>4},{y:>4}) rgb=({a[y,x,0]:.3f},{a[y,x,1]:.3f},{a[y,x,2]:.3f}) sat={sat[y,x]:.3f}")
else:
    print("画面里没有明显彩色像素 —— 抱枕可能未入镜或被遮挡")
    # 找非灰像素
    chroma = (np.abs(a - a.mean(axis=2, keepdims=True))).max(axis=2)
    print("max chroma =", round(float(chroma.max()), 4), "at", np.unravel_index(chroma.argmax(), chroma.shape))
    m = chroma > 0.02
    print("pixels with chroma>0.02:", int(m.sum()))
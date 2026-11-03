"""客观分析渲染图：亮度分布、对比度、是否过曝/欠曝、主体占比。
用真实像素统计，不靠肉眼判断。"""
import sys
from PIL import Image
import numpy as np

path = sys.argv[1]
im = Image.open(path).convert('RGB')
a = np.asarray(im).astype(np.float32) / 255.0
lum = a @ np.array([0.2126, 0.7152, 0.0722], dtype=np.float32)

print(f"file={path}")
print(f"size={im.size}")
print(f"mean={lum.mean():.4f} std={lum.std():.4f} min={lum.min():.4f} max={lum.max():.4f}")
print(f"p1={np.percentile(lum, 1):.4f} p50={np.percentile(lum, 50):.4f} p99={np.percentile(lum, 99):.4f}")
for t in (0.02, 0.05, 0.1, 0.5, 0.9):
    print(f"  frac<{t}: {(lum < t).mean() * 100:.1f}%   frac>{t}: {(lum > t).mean() * 100:.1f}%")
print(f"dark(<0.05) = {(lum < 0.05).mean() * 100:.1f}%")
print(f"bright(>0.6) = {(lum > 0.6).mean() * 100:.1f}%")
print(f"colorful(sat>0.15) = {((a.max(axis=2) - a.min(axis=2)) > 0.15).mean() * 100:.1f}%")
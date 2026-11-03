"""检查渲染图里是否存在特定色相区域（验证抱枕等彩色物体是否真的入镜）。"""
import sys
from PIL import Image
import numpy as np

path = sys.argv[1]
im = Image.open(path).convert('RGB')
a = np.asarray(im).astype(np.float32) / 255.0
r, g, b = a[..., 0], a[..., 1], a[..., 2]

orange = (r > 0.25) & (r > g * 1.25) & (g > b * 1.1) & (b < 0.35)
blue = (b > 0.18) & (b > r * 1.3) & (b > g * 1.05)
green = (g > 0.16) & (g > r * 1.15) & (g > b * 1.15)

print(f"file={path}  size={im.size}")
print(f"orange pixels = {orange.sum():>7}  ({orange.mean()*100:.2f}%)")
print(f"blue pixels   = {blue.sum():>7}  ({blue.mean()*100:.2f}%)")
print(f"green pixels  = {green.sum():>7}  ({green.mean()*100:.2f}%)")

# 画面四象限亮度，定位主体在哪
lum = a @ np.array([0.2126, 0.7152, 0.0722], dtype=np.float32)
h, w = lum.shape
for name, sl in (("TL", (slice(0, h//2), slice(0, w//2))),
                 ("TR", (slice(0, h//2), slice(w//2, w))),
                 ("BL", (slice(h//2, h), slice(0, w//2))),
                 ("BR", (slice(h//2, h), slice(w//2, w)))):
    print(f"  {name} mean lum = {lum[sl].mean():.4f}")

# 最亮的 5 个区域（是否是主体）
print(f"center 50% region mean lum = {lum[h//4:3*h//4, w//4:3*w//4].mean():.4f}")
print(f"edge region mean lum       = {lum[:h//8, :].mean():.4f}")
"""汇总所有渲染图的客观质量指标，判定是否有过曝/欠曝/色彩异常/主体缺失。"""
import pathlib, sys
from PIL import Image
import numpy as np

MODELS = pathlib.Path(__file__).resolve().parents[3] / "验收" / "models"
files = sorted(MODELS.glob("preview_*_studio.png")) + \
        sorted(MODELS.glob("preview_*_front.png")) + \
        sorted(MODELS.glob("preview_*_detail.png"))

print(f"{'file':<34}{'mean':>7}{'p50':>7}{'p99':>7}{'过曝%':>8}{'欠曝%':>8}{'彩色%':>8}{'std':>7}")
print("-" * 86)
bad = []
for f in files:
    a = np.asarray(Image.open(f).convert("RGB")).astype(np.float32) / 255.0
    lum = a @ np.array([0.2126, 0.7152, 0.0722], dtype=np.float32)
    sat = (a.max(axis=2) - a.min(axis=2))
    over = (lum > 0.97).mean() * 100
    under = (lum < 0.04).mean() * 100
    colorful = (sat > 0.12).mean() * 100
    print(f"{f.name:<34}{lum.mean():>7.3f}{np.percentile(lum,50):>7.3f}"
          f"{np.percentile(lum,99):>7.3f}{over:>8.1f}{under:>8.1f}{colorful:>8.1f}{lum.std():>7.3f}")
    if over > 25 or under > 40 or lum.std() < 0.08:
        bad.append(f.name)

print("-" * 86)
print(f"共 {len(files)} 张，异常 {len(bad)} 张")
for b in bad:
    print("  !", b)
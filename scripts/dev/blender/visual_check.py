#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""视觉体检：把整张联系表当作唯一判据，找出渲染异常的款式。

【为什么需要这个】
    几何审计（audit_geometry / audit_winding / audit_manifold）只能证明
    "网格是合法的"，证明不了"看起来对不对"。
    曾经出现过：所有审计全绿，但 144 个家具渲染成一坨黑
    （贴图平均亮度只有 36/255）—— 没有任何数值指标能发现。

    所以判定必须【基于像素】。

【怎么用】
    1. 在验收站点「总览图」按钮 → 渲染当前批次 → 另存为 PNG
       （或用浏览器 console 里的 window.__CS_IMG）
    2. python visual_check.py <联系表.png>

【判据】
    碎片检测 —— 轮廓的连通域数量。
    正常家具：1~3 个连通域（主体 + 分离的配件）。
    几何崩坏（缺面/法线翻转/绕序错乱）：几十上百个碎块。
    → 这是"黑白三角乱刺"的直接像素指纹。
"""
import json
import os
import sys
from collections import deque

from PIL import Image

ACC = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))))), "验收")
CATALOG = os.path.join(ACC, "models", "catalog.json")

COLS = 10
TILE = 200
BG = (13, 13, 15)          # 联系表背景色
SAMPLE = 6                # 连通域分析的采样步长（像素）


def load_items():
    with open(CATALOG, encoding="utf-8") as f:
        cat = json.load(f)
    return [it for g in cat["groups"] for it in g["items"] if it.get("file")]


def components(px, x0, y0):
    """数轮廓的连通域个数 —— 碎片数的直接度量。"""
    w = (TILE - 12) // SAMPLE
    h = (TILE - 12) // SAMPLE
    mask = [[False] * w for _ in range(h)]
    for j in range(h):
        for i in range(w):
            p = px[x0 + 6 + i * SAMPLE, y0 + 6 + j * SAMPLE]
            if abs(p[0] - BG[0]) + abs(p[1] - BG[1]) + abs(p[2] - BG[2]) > 24:
                mask[j][i] = True
    seen = [[False] * w for _ in range(h)]
    n = 0
    for j in range(h):
        for i in range(w):
            if not mask[j][i] or seen[j][i]:
                continue
            n += 1
            q = deque([(i, j)])
            seen[j][i] = True
            while q:
                a, b = q.popleft()
                for da, db in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    na, nb = a + da, b + db
                    if (0 <= na < w and 0 <= nb < h
                            and mask[nb][na] and not seen[nb][na]):
                        seen[nb][na] = True
                        q.append((na, nb))
    return n


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        print("用法: python visual_check.py <联系表.png>")
        return 1
    path = sys.argv[1]
    if not os.path.exists(path):
        print("找不到文件:", path)
        return 1

    items = load_items()
    im = Image.open(path).convert("RGB")
    px = im.load()
    need_rows = (len(items) + COLS - 1) // COLS
    if im.size[1] < need_rows * TILE:
        print("联系表高度不足: 需要 %d 行，实际 %d px"
              % (need_rows, im.size[1]))
        return 1

    res = []
    for i, it in enumerate(items):
        c = i % COLS
        r = i // COLS
        res.append((components(px, c * TILE, r * TILE), it["key"],
                    it.get("name", "")))

    res.sort(reverse=True)
    FRAG = 10          # 碎片阈值：超过就判定为几何崩坏
    bad = [x for x in res if x[0] > FRAG]
    multi = [x for x in res if 4 < x[0] <= FRAG]

    print("=== 视觉体检: %d 件 ===" % len(items))
    print("碎片崩坏 (>%d 连通域): %d 件" % (FRAG, len(bad)))
    for n, k, nm in bad:
        print("   comps=%-4d %-20s %s" % (n, k, nm))
    print("多部件 (4-%d): %d 件  (正常：主体+配件)"
          % (FRAG, len(multi)))
    for n, k, nm in multi:
        print("   comps=%-4d %-20s %s" % (n, k, nm))
    print()
    if bad:
        print("结论: 有 %d 件存在几何崩坏，需修复。" % len(bad))
        return 2
    print("结论: 全部 %d 件轮廓正常，无碎片化。" % len(items))
    return 0


if __name__ == "__main__":
    sys.exit(main())

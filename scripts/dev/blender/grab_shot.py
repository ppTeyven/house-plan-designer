"""从浏览器 CDP 抓取 3D 画布并落盘为 PNG/JPG（用于验收取证）。

用法：
  python grab_shot.py <out.jpg> [表达式文件]

需要先在浏览器里跑过：
  window.__SHOT = <dataURL>   （由 page 内的 readPixels 脚本生成）
"""
import base64
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))


def save_dataurl(dataurl, out):
    if "," in dataurl:
        dataurl = dataurl.split(",", 1)[1]
    raw = base64.b64decode(dataurl)
    with open(out, "wb") as f:
        f.write(raw)
    return len(raw)


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "assets", "_shots", "shot.jpg")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    src = sys.argv[2] if len(sys.argv) > 2 else os.path.join(HERE, "_shot_dataurl.txt")
    data = open(src, encoding="utf-8").read().strip().strip('"')
    n = save_dataurl(data, out)
    print("wrote %s  (%.1f KB)" % (out, n / 1024.0))

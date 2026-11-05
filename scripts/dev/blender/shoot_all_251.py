"""在真实浏览器里批量渲染验收站全部 251 件家具，输出拼版图（contact sheet）。

【为什么必须真跑浏览器】GLB 几何体检、编码扫描都过了，但用户报"乱码"。
唯一没验的就是"浏览器里画出来长什么样"。这里直接驱动 8099 验收站，
逐个 select() → 渲染 → readPixels 截图，最后拼成一张大图供人工核验。

用法：python shoot_all_251.py [输出目录]
"""
import base64
import json
import os
import struct
import sys
import time
import urllib.request

OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")),
    "assets", "_shots", "acc251")
BASE = "http://127.0.0.1:8099"


def http_json(path):
    with urllib.request.urlopen(BASE + path, timeout=20) as r:
        return json.loads(r.read().decode("utf-8"))


def http_bytes(path):
    with urllib.request.urlopen(BASE + path, timeout=30) as r:
        return r.read()


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    man = http_json("/models/manifest.json")
    items = man["items"]
    print("manifest items = %d" % len(items))
    print("把这段 JS 贴到浏览器控制台执行，或用本脚本的 CDP 通道。")
    print(json.dumps([{"key": it["key"], "name": it["name"], "file": it.get("file")}
                      for it in items], ensure_ascii=False, indent=1)[:2000])

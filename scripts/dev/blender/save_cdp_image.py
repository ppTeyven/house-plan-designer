"""把 CDP 保存下来的 dataURL 响应文件转成图片。

CDP 的大响应会被存到 ~/.cursor/browser-logs/cdp-response-*.json，
里面是 {"result":{"value":"data:image/jpeg;base64,..."}}。

用法：python save_cdp_image.py <cdp-json 文件> <输出图片>
"""
import base64
import json
import os
import sys

if len(sys.argv) < 3:
    print(__doc__)
    sys.exit(1)

src = sys.argv[1]
dst = sys.argv[2]

with open(src, "r", encoding="utf-8") as f:
    d = json.load(f)

v = d.get("result", {}).get("value")
if v is None:
    v = d.get("value")
if not isinstance(v, str) or "," not in v:
    print("不是 dataURL，值=%r" % (str(v)[:200],))
    sys.exit(2)

b64 = v.split(",", 1)[1]
os.makedirs(os.path.dirname(os.path.abspath(dst)), exist_ok=True)
with open(dst, "wb") as f:
    f.write(base64.b64decode(b64))
print("wrote %s  (%d bytes)" % (dst, os.path.getsize(dst)))

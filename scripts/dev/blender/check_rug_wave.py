"""(1) 检查地毯 GLB 的 Y 方向起伏（是否已有自然褶皱几何）
(2) 列出 sx() 里变量 i / e / h 的全部引用点，确认替换安全
"""
import os
import re
import struct
import json

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
TP = os.path.join(ROOT, "assets", "template.html")
GLB_DIR = os.path.join(ROOT, "assets", "furnlib")


def glb_json(path):
    with open(path, "rb") as f:
        data = f.read()
    total = struct.unpack("<III", data[:12])[2]
    off = 12
    while off < total:
        clen, ctype = struct.unpack("<II", data[off:off + 8])
        if ctype == 0x4E4F534A:
            return json.loads(data[off + 8:off + 8 + clen].decode("utf-8")), data
        off += 8 + clen
    return None, data


print("===== 地毯 Y 起伏 =====")
for name in ["rug", "roundRug", "doormat"]:
    p = os.path.join(GLB_DIR, name + ".glb")
    j, data = glb_json(p)
    bin_chunk = None
    off = 12
    total = struct.unpack("<III", data[:12])[2]
    while off < total:
        clen, ctype = struct.unpack("<II", data[off:off + 8])
        if ctype == 0x004E4942:
            bin_chunk = data[off + 8:off + 8 + clen]
        off += 8 + clen
    pr = j["meshes"][0]["primitives"][0]
    acc = j["accessors"][pr["attributes"]["POSITION"]]
    bv = j["bufferViews"][acc["bufferView"]]
    base = bv.get("byteOffset", 0) + acc.get("byteOffset", 0)
    stride = bv.get("byteStride", 12)
    n = acc["count"]
    ys = []
    for i in range(n):
        y = struct.unpack_from("<f", bin_chunk, base + i * stride + 4)[0]
        ys.append(y)
    ys_sorted = sorted(ys)
    print("%-9s verts=%5d  y_min=%.4f y_max=%.4f  p05=%.4f p50=%.4f p95=%.4f"
          % (name, n, min(ys), max(ys),
             ys_sorted[int(n * .05)], ys_sorted[n // 2], ys_sorted[int(n * .95)]))

print()
print("===== sx() 内变量引用 =====")
s = open(TP, encoding="utf-8").read()
SX = s.find("function sx(){")
END = s.find("\nfunction ", SX + 20)
if END < 0 or END > 1960000:
    END = 1960000
body = s[SX:END]

# 变量 i / e / h 在 sx 内的引用（排除成员访问 .i / .e / .h 和字符串）
for var in ["i", "e", "h", "s", "o"]:
    hits = []
    for m in re.finditer(r"(?<![.\w$])" + var + r"(?![\w$])", body):
        i = m.start()
        hits.append((i, body[max(0, i - 70):i + 70].replace("\n", " | ")))
    print("--- var '%s'  x%d" % (var, len(hits)))
    for i, ctx in hits[:6]:
        print("   %7d ...%s..." % (i, ctx))
    print()

"""提取所有 GLB 里内嵌的图片，检查它们是不是噪点/占位图。

【假设】"几乎所有物件都是乱码" 可能不是文字，而是 GLB 内嵌的贴图本身
就是随机噪声（占位图/生成失败），渲染出来就是一片彩色噪点。

检查项：
  1. 每张图的像素尺寸（太小 = 占位符）
  2. 图像熵/相邻像素差（真扫描贴图有连续纹理；纯噪声相邻差≈均匀分布）
  3. 是否大量出现完全随机的 RGB

用法：python tex_audit.py
"""
import json
import os
import struct
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
ACC = os.path.join(ROOT, "assets", "furnlib")
CT_JSON = 0x4E4F534A
CT_BIN = 0x004E4942


def load_glb(path):
    blob = open(path, "rb").read()
    total = struct.unpack("<I", blob[8:12])[0]
    off = 12
    js = None
    binchunk = None
    while off + 8 <= min(total, len(blob)):
        clen, ctype = struct.unpack("<II", blob[off:off + 8])
        data = blob[off + 8:off + 8 + clen]
        if ctype == CT_JSON:
            js = json.loads(data.decode("utf-8"))
        elif ctype == CT_BIN:
            binchunk = data
        off += 8 + clen
    return js, binchunk, blob


def img_bytes(js, binchunk, blob, iidx):
    img = js["images"][iidx]
    if "bufferView" in img:
        bv = js["bufferViews"][img["bufferView"]]
        s = bv.get("byteOffset", 0)
        return binchunk[s:s + bv["byteLength"]], img.get("mimeType", "")
    if "uri" in img:
        u = img["uri"]
        if u.startswith("data:"):
            import base64
            b64 = u.split(",", 1)[1]
            return base64.b64decode(b64), img.get("mimeType", "")
        p = os.path.join(ACC, u)
        if os.path.exists(p):
            return open(p, "rb").read(), img.get("mimeType", "")
    return b"", img.get("mimeType", "")


def analyze(data):
    """返回 (w, h, noise_score, unique_ratio, mean)"""
    try:
        from PIL import Image
        import io
        im = Image.open(io.BytesIO(data)).convert("RGB")
    except Exception as e:
        return None
    w, h = im.size
    small = im.resize((min(64, w), min(64, h)))
    px = list(small.getdata())
    n = len(px)
    if n < 2:
        return (w, h, 0, 0, 0)
    # 相邻像素平均绝对差（噪声大，真纹理小）
    diffs = []
    for y in range(small.height):
        for x in range(small.width - 1):
            a = px[y * small.width + x]
            b = px[y * small.width + x + 1]
            diffs.append(sum(abs(a[i] - b[i]) for i in range(3)) / 3.0)
    avg_diff = sum(diffs) / max(1, len(diffs))
    uniq = len(set(px)) / float(n)
    mean = sum(sum(p) for p in px) / (3.0 * n)
    return (w, h, avg_diff, uniq, mean)


files = sorted(f for f in os.listdir(ACC) if f.endswith(".glb"))
print("检查 %d 个 GLB 的内嵌贴图 ..." % len(files))
suspicious = []
ok_imgs = 0
total_imgs = 0
for f in files:
    p = os.path.join(ACC, f)
    try:
        js, binchunk, blob = load_glb(p)
    except Exception as e:
        print("  %s 解析失败 %s" % (f, e))
        continue
    imgs = js.get("images", [])
    if not imgs:
        continue
    for i, im in enumerate(imgs):
        total_imgs += 1
        data, mime = img_bytes(js, binchunk, blob, i)
        if not data:
            suspicious.append((f, i, "图片数据缺失", mime, 0, 0, 0))
            continue
        r = analyze(data)
        if r is None:
            suspicious.append((f, i, "无法解码 %s" % mime, mime, 0, 0, 0))
            continue
        w, h, diff, uniq, mean = r
        tag = None
        if w < 64 or h < 64:
            tag = "尺寸过小 %dx%d" % (w, h)
        elif diff > 55 and uniq > 0.85:
            tag = "疑似随机噪声 avgdiff=%.1f uniq=%.2f" % (diff, uniq)
        if tag:
            suspicious.append((f, i, tag, mime, w, h, diff))
        else:
            ok_imgs += 1

print("\n内嵌图片 %d 张，正常 %d 张，可疑 %d 张" % (total_imgs, ok_imgs, len(suspicious)))
print("\n=== 可疑图片 ===")
for f, i, tag, mime, w, h, diff in suspicious[:60]:
    print("  %-26s img%-3d %-42s %s %dx%d" % (f, i, tag, mime, w, h))

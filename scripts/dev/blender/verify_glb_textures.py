"""抽取 GLB 内嵌贴图并验证是否为有效 JPEG/PNG。

"乱码"最可能的表现：物件表面贴图解码出来是噪点/色块。
如果 patch 脚本把 JPEG 二进制写坏了（截断/偏移错/换了张图），
Three.js 加载时会给出一张纯色或噪点图 —— 视觉上就是"乱码"。
"""
import os
import struct
import sys
import io
import json

try:
    from PIL import Image
except Exception:
    Image = None

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
GLB_DIR = os.path.join(ROOT, "assets", "furnlib")


def read_glb(path):
    with open(path, "rb") as f:
        data = f.read()
    ver, total = struct.unpack("<II", data[4:12])
    off, js, bin_ = 12, None, b""
    while off + 8 <= len(data):
        clen, ctype = struct.unpack("<II", data[off:off + 8])
        chunk = data[off + 8:off + 8 + clen]
        if ctype == 0x4E4F534A:
            js = json.loads(chunk.decode("utf-8"))
        elif ctype == 0x004E4942:
            bin_ = chunk
        off += 8 + clen
    return js, bin_


def check(path, dump_dir=None):
    key = os.path.splitext(os.path.basename(path))[0]
    js, bin_ = read_glb(path)
    bvs = js.get("bufferViews", [])
    out = []
    for idx, im in enumerate(js.get("images", [])):
        mime = im.get("mimeType", "?")
        bv = im.get("bufferView")
        if bv is None:
            out.append((idx, mime, "EXTERNAL-URI", im.get("uri", "")[:60], ""))
            continue
        b = bvs[bv]
        off = b.get("byteOffset", 0)
        ln = b.get("byteLength", 0)
        blob = bin_[off:off + ln]
        info = ""
        ok = False
        if mime == "image/jpeg" and blob[:2] == b"\xff\xd8":
            ok = True
        elif mime == "image/png" and blob[:8] == b"\x89PNG\r\n\x1a\n":
            ok = True
        if Image is not None:
            try:
                im2 = Image.open(io.BytesIO(blob))
                im2.load()
                ex = im2.size
                gray = im2.convert("L")
                h = gray.histogram()
                mean = sum(i * c for i, c in enumerate(h)) / float(sum(h) or 1)
                std = (sum(((i - mean) ** 2) * c for i, c in enumerate(h)) / float(sum(h) or 1)) ** 0.5
                info = "%s %s mean=%.1f std=%.1f" % (im2.format, ex, mean, std)
                ok = True
            except Exception as e:
                info = "DECODE-FAIL: %s" % e
                ok = False
        if not blob:
            info = "EMPTY"
            ok = False
        out.append((idx, mime, "bv%d" % bv, "len=%d" % ln, info, ok))
    return key, out


def main():
    names = sys.argv[1:] or ["sofa", "armchair", "bed18", "plant", "diningTable"]
    for nm in names:
        p = os.path.join(GLB_DIR, nm + ".glb")
        if not os.path.exists(p):
            print("%s MISSING" % nm)
            continue
        key, out = check(p)
        print("=" * 78)
        print("%s" % key)
        for row in out:
            print("   ", row)


if __name__ == "__main__":
    main()

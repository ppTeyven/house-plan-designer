"""下载参考素材图（按原版建模找相似图）到 验收/refs/。

用法: python fetch_refs.py <key> <url> [name]
只接受 http/https，避免意外来源。
"""
import sys, urllib.request, pathlib, re

REFS = pathlib.Path(__file__).resolve().parents[3] / "验收" / "refs"
REFS.mkdir(parents=True, exist_ok=True)

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")


def fetch(url, dest):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "image/*,*/*"})
    with urllib.request.urlopen(req, timeout=30) as r:
        data = r.read()
    if len(data) < 2000:
        raise RuntimeError("too small (%d bytes) - not an image: %s" % (len(data), url))
    dest.write_bytes(data)
    return len(data)


def ext_for(url, data):
    """按【实际内容】判定扩展名，不靠 URL 后缀。
    （实测：官方规格图链接常无后缀，或后缀是 .pdf 但服务端返回 PDF；
      早期版本按 URL 猜后缀，把 PDF 存成了 .jpg，浏览器无法渲染）
    """
    if data[:4] == b"%PDF":
        return ".pdf"
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return ".png"
    if data[:3] == b"\xff\xd8\xff":
        return ".jpg"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return ".webp"
    if data[:5] in (b"<?xml", b"<svg"):
        return ".svg"
    # 兜底：WebP/AVIF 等新格式，统一存为 .bin 之外不可知 → 用 .jpg 会被浏览器拒绝
    raise RuntimeError("unknown content type: %r" % data[:16])


def main():
    key, url = sys.argv[1], sys.argv[2]
    name = sys.argv[3] if len(sys.argv) > 3 else key
    assert url.startswith(("http://", "https://")), "only http(s) allowed"
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
    with urllib.request.urlopen(req, timeout=45) as r:
        data = r.read()
    if len(data) < 2000:
        raise RuntimeError("too small (%d bytes) - not an asset: %s" % (len(data), url))
    dest = REFS / (name + ext_for(url, data))
    dest.write_bytes(data)
    print(f"OK {dest.name} {len(data)} bytes  <- {url}")


if __name__ == "__main__":
    main()
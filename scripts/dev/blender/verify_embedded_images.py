"""校验 GLB 内嵌图片是否【真的能被解码】——引用合法 ≠ 像素合法。

【为什么需要】
  实测：sofa.glb 的 JSON 里 textures/images/bufferViews 引用全部合法
  （bv 在 bin 范围内、mimeType 正确、sampler 存在），
  但浏览器 three.js 读出来 material.map === null，
  运行时统计 maps:0 / norm:0 → 渲染成纯色。

  所以必须逐张把内嵌字节取出来，交给真正的 JPEG 解码器验证：
    · 能解出 size → 像素合法
    · PIL 报 truncated / cannot identify → 字节损坏

用法：python verify_embedded_images.py
"""
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
ACC = os.path.join(ROOT, "assets", "furnlib")

import normalize_glb as NG

try:
    from PIL import Image
except ImportError:
    Image = None


def check(path):
    """返回 (总数, 正常, 损坏列表)。"""
    js, bin_data = NG.read_glb(path)
    imgs = js.get("images", [])
    bad = []
    ok = 0
    for i, im in enumerate(imgs):
        bv = im.get("bufferView")
        if bv is None:
            bad.append((i, "no_bufferView"))
            continue
        view = js["bufferViews"][bv]
        off = view.get("byteOffset", 0)
        length = view.get("byteLength", 0)
        if off + length > len(bin_data):
            bad.append((i, "out_of_range"))
            continue
        data = bin_data[off:off + length]
        if not data:
            bad.append((i, "empty"))
            continue
        if Image is None:
            ok += 1
            continue
        try:
            with Image.open(io.BytesIO(data)) as im2:
                im2.load()          # 真正解码（不只看头部）
            ok += 1
        except Exception as exc:
            bad.append((i, "%s: %s" % (type(exc).__name__, str(exc)[:60])))
    return len(imgs), ok, bad


def main():
    man = json.load(open(os.path.join(ACC, "manifest.json"), encoding="utf-8"))
    total_models = 0
    models_with_img = 0
    models_bad = 0
    all_bad = []
    total_imgs = 0
    good_imgs = 0
    for it in man["items"]:
        key = it["key"]
        path = os.path.join(ACC, key + ".glb")
        if not os.path.exists(path):
            continue
        total_models += 1
        n, ok, bad = check(path)
        total_imgs += n
        good_imgs += ok
        if n:
            models_with_img += 1
        if bad:
            models_bad += 1
            all_bad.append((key, n, ok, bad))

    print("模型 %d 个，其中带内嵌图片的 %d 个" % (total_models, models_with_img))
    print("内嵌图片 %d 张，可解码 %d 张，损坏 %d 张"
          % (total_imgs, good_imgs, total_imgs - good_imgs))
    print("有损坏图片的模型: %d 个" % models_bad)
    for key, n, ok, bad in all_bad[:40]:
        print("   %-20s %d 张，坏 %d 张  %s" % (key, n, n - ok, bad[:3]))


if __name__ == "__main__":
    main()

"""检查 catalog.json / manifest.json 里有没有乱码字段（编码损坏）。

【症状】用户反馈"验收不合格，几乎所有的物件都是乱码"。
先排除数据层：文件名、id、name 字段是否含替换字符/乱码序列。

用法：python check_encoding.py
"""
import json
import os
import re
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
FILES = [
    os.path.join(ROOT, "验收", "models", "catalog.json"),
    os.path.join(ROOT, "验收", "models", "manifest.json"),
    os.path.join(ROOT, "assets", "furnlib", "index.json"),
    os.path.join(ROOT, "assets", "furnlib", "manifest.json"),
    os.path.join(ROOT, "assets", "furnlib", "catalog.json"),
]

BAD_CHARS = ["�", "□", "?????"]
MOJIBAKE = re.compile(r"[ÃÂåæçèéêëì][\x80-\xbf-ÿ]")


def scan_text(t, path=""):
    issues = []
    for b in BAD_CHARS:
        if b in t:
            issues.append("含替换字符 %r @ %s" % (b, path))
    if MOJIBAKE.search(t):
        issues.append("疑似 UTF-8 当 Latin-1 解码 @ %s" % path)
    return issues


def walk(obj, path, out):
    if isinstance(obj, str):
        for m in scan_text(obj, path):
            out.append((m, obj[:90]))
    elif isinstance(obj, dict):
        for k, v in obj.items():
            walk(v, path + "." + str(k), out)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            walk(v, path + "[%d]" % i, out)


for f in FILES:
    if not os.path.exists(f):
        print("[缺失] %s" % os.path.relpath(f, ROOT))
        continue
    raw = open(f, "rb").read()
    print("\n===== %s  (%.1f KB) =====" % (os.path.relpath(f, ROOT), len(raw) / 1024.0))
    # 编码探测
    for enc in ("utf-8", "utf-8-sig", "gbk"):
        try:
            raw.decode(enc)
            print("  编码可用: %s" % enc)
            break
        except UnicodeDecodeError:
            continue
    else:
        print("  !! 无法用 utf-8/gbk 解码")
        continue
    try:
        data = json.loads(raw.decode("utf-8-sig"))
    except Exception as e:
        print("  !! JSON 解析失败: %s" % e)
        continue
    out = []
    walk(data, "$", out)
    if out:
        print("  ⚠ 发现 %d 处可疑文本：" % len(out))
        for m, sample in out[:20]:
            print("     %s" % m)
            print("        sample=%r" % sample)
    else:
        print("  ✓ 无替换字符 / 无 mojibake")
    # 抽样打印几个 name
    items = data.get("items") if isinstance(data, dict) else data
    if isinstance(items, list) and items:
        print("  条目 %d，抽样 8 条 name/key/file:" % len(items))
        for it in items[:8]:
            if isinstance(it, dict):
                print("     name=%-18s key=%-18s file=%s"
                      % (it.get("name"), it.get("key"), it.get("file") or it.get("id")))

"""全项目扫描编码损坏（U+FFFD 替换字符 / UTF-8 被当 GBK 解读的乱码）。

【背景】用户报"几乎所有的物件都是乱码"。主程序 template.html 第 13327 行
出现 "可��构件" —— 这是典型的 UTF-8 字节被截断/误解码产生的替换字符，
写进 JS 源文件后可能直接让整个 script 块语法错误、界面表现成乱码。

本脚本扫：
  - 所有 .html/.js/.css/.json/.py/.md
  - 原始字节层面找 EF BF BD（U+FFFD 的 UTF-8 编码）
  - 以及经典 mojibake 特征（Ã/Â/ä¸/ï¿½ 等）

用法：python scan_corruption.py [目录...]
"""
import os
import re
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
TARGET_DIRS = sys.argv[1:] or [ROOT]

SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv",
             "vendor", "tex", "models", "furnlib", "previews", "refs",
             "_shots", "assets_raw", "downloads", "blender_cache"}
TEXT_EXT = {".html", ".js", ".css", ".json", ".py", ".md", ".txt", ".csv", ".svg"}

# 经典 UTF-8→Latin1/GBK 误解码残留
MOJIBAKE = re.compile(
    "[\u00c2\u00c3\u00c4\u00c5\u00e3\u00e4\u00e5\u00e6\u00e7\u00e8\u00e9"
    "\u00ea\u00eb\u00ec\u00ed\u00ee\u00ef]|\u00ef\u00bf\u00bd|\ufffd"
    "|Ã[\u0080-\u00bf]|â[\u0080-\u00bf]{1,2}"
)


def is_texty(p):
    return os.path.splitext(p)[1].lower() in TEXT_EXT


def scan_file(p):
    raw = open(p, "rb").read()
    hits = []
    # 1) 原始 U+FFFD 字节序列
    cnt = raw.count(b"\xef\xbf\xbd")
    if cnt:
        hits.append(("U+FFFD字节", cnt))
    # 2) 解码后逐行找
    try:
        txt = raw.decode("utf-8")
    except UnicodeDecodeError as e:
        hits.append(("非UTF-8", 1))
        return hits, txt if isinstance(txt, str) else None, e
    for i, line in enumerate(txt.splitlines(), 1):
        if "\ufffd" in line:
            hits.append(("行%d含U+FFFD" % i, line.count("\ufffd")))
        m = MOJIBAKE.search(line)
        if m and not is_legit_unicode(line, m.group(0)):
            hits.append(("行%d mojibake %r" % (i, m.group(0)), 1))
    return hits, txt, None


def is_legit_unicode(line, frag):
    """排除真正的数学/希腊字母等合法用法。"""
    legit = {"Ã", "Â"}  # 极少见于代码；仍标记
    if frag in legit and len(line.strip()) > 200:
        return False
    return False


total = 0
bad_files = []
for td in TARGET_DIRS:
    for dirpath, dirnames, filenames in os.walk(td):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and not d.startswith(".")]
        for fn in filenames:
            p = os.path.join(dirpath, fn)
            if not is_texty(p):
                continue
            try:
                hits, txt, err = scan_file(p)
            except Exception as e:
                print("读取失败 %s: %s" % (p, e))
                continue
            if hits:
                total += 1
                bad_files.append((p, hits, txt))
            else:
                total += 1

print("扫描 %d 个文本文件" % total)
print("\n=== 发现损坏的文件 %d 个 ===" % len(bad_files))
for p, hits, txt in bad_files:
    rel = os.path.relpath(p, ROOT)
    print("\n--- %s" % rel)
    for h, c in hits[:12]:
        print("    %s  x%d" % (h, c))
    if txt:
        for i, line in enumerate(txt.splitlines(), 1):
            if "\ufffd" in line:
                s = line.strip()
                print("    行%-6d %s" % (i, s[:160]))
                if len(s) > 160:
                    print("             ...%s" % s[-120:])

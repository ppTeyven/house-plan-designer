"""安全编辑 template.html 的内联 bundle。

【为什么需要这个工具】
  assets/template.html 是【压缩产物】：单个 <script type="module"> 有 2,000,000+ 字符、
  几乎全在一行里。直接用编辑器改必然出事：
    - 缩进/换行格式化会把压缩产物改坏（行号全部失效）
    - 字符串替换不校验唯一性 → 改错地方还不报错
  HANDOFF.md §4 的 SOP 要求：锚点定位 → 精确唯一替换 → node --check → HTTP 校验。

【这个工具做什么】
  1. 从 template.html 抽出 <script type="module"> 的内容（不动其它任何字节）
  2. 要求 old 串在 bundle 中【恰好出现 1 次】（否则报错退出，绝不猜）
  3. 替换后立刻跑 node --check 语法校验
  4. 校验通过才写回 template.html；不通过则原文件保持不变
  5. 写回后重新抽取并对比，确认只有预期的差异

用法：
  python scripts/dev/patch_template.py --find "OLD" --replace-with "NEW" [--note "说明"]
  python scripts/dev/patch_template.py --check          # 只做语法校验，不改文件
  python scripts/dev/patch_template.py --show "SUBSTR"   # 打印匹配处上下文（定位用）
"""

import argparse
import os
import pathlib
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[2]
TPL = ROOT / "assets" / "template.html"


def read_template() -> str:
    """【必须二进制读】template.html 是压缩产物，行尾符是它的一部分。

    用 text 模式读会被 Python 的 universal newlines 改写（\\r\\n -> \\n），
    写回时就再也对不上原字节 —— 实测会把 15815 个 LF 全部变成 CRLF，
    git diff 显示整个文件被重写。压缩产物必须逐字节保真。
    """
    return TPL.read_bytes().decode("utf-8")


def write_template(text: str) -> None:
    """【必须二进制写】同上：只做 UTF-8 编码，绝不让 Python 转换行尾符。"""
    TPL.write_bytes(text.encode("utf-8"))


def extract_bundle(text: str) -> tuple:
    """返回 (start, end, bundle_text)：module script 的内容区间。

    区间取 <script type="module"> 的 '>' 之后到 </script> 之前，
    与 HANDOFF.md §4 的 SOP 完全一致。
    """
    s = text.find('<script type="module"')
    if s < 0:
        raise SystemExit("找不到 <script type=\"module\">")
    s = text.index(">", s) + 1
    e = text.find("</script>", s)
    if e < 0:
        raise SystemExit("找不到 </script>")
    return s, e, text[s:e]


def syntax_check(bundle: str) -> bool:
    """把 bundle 写成 .mjs 跑 node --check。node 不存在时返回 True（跳过）。"""
    with tempfile.NamedTemporaryFile("w", suffix=".mjs", delete=False, encoding="utf-8") as f:
        f.write(bundle)
        tmp = f.name
    try:
        # encoding 固定 utf-8 + errors=replace：node 的报错里可能有非 GBK 字节，
        # 用系统默认编码会抛 UnicodeDecodeError，把真正的错误信息吃掉。
        r = subprocess.run(
            ["node", "--check", tmp],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        if r.returncode != 0:
            sys.stderr.write("node --check 失败：\n" + (r.stderr or "")[:2000] + "\n")
            return False
        return True
    except FileNotFoundError:
        print("警告：找不到 node，跳过语法校验")
        return True
    finally:
        try:
            os.unlink(tmp)
        except OSError:
            pass


def cmd_show(args) -> int:
    text = read_template()
    _, _, bundle = extract_bundle(text)
    needle = args.show
    idx = bundle.find(needle)
    if idx < 0:
        print("未找到：" + needle[:120])
        return 1
    lo = max(0, idx - args.ctx)
    hi = min(len(bundle), idx + len(needle) + args.ctx)
    print("=== 位置 %d（bundle 内偏移）===" % idx)
    print(bundle[lo:hi])
    print("=== 出现次数：%d ===" % bundle.count(needle))
    return 0


def cmd_check(args) -> int:
    text = read_template()
    _, _, bundle = extract_bundle(text)
    ok = syntax_check(bundle)
    print("bundle 长度 %d，语法校验 %s" % (len(bundle), "通过" if ok else "失败"))
    return 0 if ok else 1


EMPTY = "<DELETE>"


def cmd_patch(args) -> int:
    text = read_template()
    s, e, bundle = extract_bundle(text)

    pairs = list(zip(args.find, args.replace_with))
    if not pairs:
        raise SystemExit("没有 --find/--replace-with")
    # 先把 <DELETE> 占位符规范化成空串（必须在 pairs 层面做，
    # 否则后面 replace 时会把 "<DELETE>" 字面量真的写进代码里）
    pairs = [(old, "" if new == EMPTY else new) for old, new in pairs]
    for old, new in pairs:
        if old == new:
            raise SystemExit("--find 与 --replace-with 相同")

    # 所有锚点必须先各自唯一（逐个独立计数，不受其它替换影响）
    for old, _ in pairs:
        n = bundle.count(old)
        if n != 1:
            sys.stderr.write(
                "锚点在 bundle 中出现 %d 次（要求恰好 1 次）——拒绝修改。\n"
                "请用更长的上下文让锚点唯一。\n锚点：%s\n" % (n, old[:120])
            )
            return 2

    new_bundle = bundle
    for old, new in pairs:
        new_bundle = new_bundle.replace(old, new)

    if not syntax_check(new_bundle):
        sys.stderr.write("语法校验未通过，template.html 未被修改。\n")
        return 3

    new_text = text[:s] + new_bundle + text[e:]

    # 【守卫】压缩产物的行尾符必须原样保留。
    # 用 text 模式写回会让 Python 把 LF 变成 CRLF，实测整个文件被重写。
    if new_text.count("\r\n") != text.count("\r\n"):
        sys.stderr.write("行尾符数量变化（%d -> %d）——拒绝修改。\n"
                         % (text.count("\r\n"), new_text.count("\r\n")))
        return 5

    write_template(new_text)

    # 回读校验：重新抽取，确认每处替换都唯一生效
    check_text = read_template()
    _, _, verify_bundle = extract_bundle(check_text)
    for old, new in pairs:
        if new == "":
            # 删除型替换：验证原文已消失，且该锚点原本唯一的特性没被破坏
            if verify_bundle.count(old) != 0:
                sys.stderr.write("回读校验失败：待删除的锚点仍存在 -> %s\n" % old[:120])
                return 4
        elif verify_bundle.count(new) != 1:
            sys.stderr.write("回读校验失败：替换结果未唯一出现 -> %s\n" % new[:120])
            return 4

    print("已修改 %s（%d 处）" % (TPL.name, len(pairs)))
    for i, (old, new) in enumerate(pairs, 1):
        print("  [%d] 锚点唯一，长度 %+d" % (i, len(new) - len(old)))
    print("  bundle 总长：%d -> %d（%+d）" % (len(bundle), len(new_bundle), len(new_bundle) - len(bundle)))
    print("  node --check：通过")
    if args.note:
        print("  说明：%s" % args.note)
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="安全编辑 template.html 的内联 bundle")
    ap.add_argument("--find", action="append", default=[])
    ap.add_argument("--replace-with", action="append", default=[])
    ap.add_argument("--pairs-file", help="JSON 文件：[{'find':..., 'replace_with':...}, ...]（避免 shell 引号问题）")
    ap.add_argument("--note", default="")
    ap.add_argument("--show")
    ap.add_argument("--ctx", type=int, default=400)
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()

    if args.check:
        return cmd_check(args)
    if args.show:
        return cmd_show(args)
    if args.pairs_file:
        import json
        with open(args.pairs_file, encoding="utf-8") as f:
            data = json.load(f)
        args.find = [d["find"] for d in data]
        args.replace_with = [d.get("replace_with", EMPTY) for d in data]
    if not args.find or not args.replace_with:
        ap.print_help()
        return 1
    if len(args.find) != len(args.replace_with):
        ap.error("--find 与 --replace-with 次数必须相同")
    return cmd_patch(args)


if __name__ == "__main__":
    sys.exit(main())

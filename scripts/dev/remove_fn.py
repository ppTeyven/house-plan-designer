"""删除 bundle 里的【顶层函数声明】。

【为什么需要】
  压缩产物里有 9 个只声明、从未被调用的函数（日照系数 G7/OL/UL、
  天空淡入淡出 skyDim/skyFade、分屏过渡 __riSmooth/__syncCam3d/__riToFull、
  墙面贴图 __furnWallTex）。它们在 bundle 里各只出现 1 次 —— 就是声明本身。
  手工在 200 万字符的单行里剪函数体风险极高，必须工具化。

【安全策略】
  1. 只删【顶层】函数：花括号配对 + 字符串/模板字面量/正则跳过
  2. 删之前先确认该函数名在整个 bundle 里只出现 1 次（否则有调用方，拒绝）
  3. 一次只删一个，删完立刻 node --check；失败则回滚
  4. 全部删完后做一次全量校验

用法：python scripts/dev/remove_fn.py G7 OL UL ...
"""
import pathlib
import subprocess
import sys
import tempfile
import os

ROOT = pathlib.Path(__file__).resolve().parents[2]
TPL = ROOT / "assets" / "template.html"


def read_tpl():
    return TPL.read_bytes().decode("utf-8")


def write_tpl(text):
    TPL.write_bytes(text.encode("utf-8"))


def extract(text):
    s = text.find('<script type="module"')
    s = text.index(">", s) + 1
    e = text.find("</script>", s)
    return s, e, text[s:e]


def syntax_check(bundle):
    with tempfile.NamedTemporaryFile("w", suffix=".mjs", delete=False, encoding="utf-8") as f:
        f.write(bundle)
        tmp = f.name
    try:
        r = subprocess.run(["node", "--check", tmp], capture_output=True, text=True,
                           encoding="utf-8", errors="replace")
        if r.returncode != 0:
            sys.stderr.write((r.stderr or "")[:1500] + "\n")
            return False
        return True
    finally:
        try:
            os.unlink(tmp)
        except OSError:
            pass


def find_function_end(bundle, start):
    """从 `function` 关键字处找到函数体的结束位置（含右花括号）。

    需要跳过字符串字面量 / 模板字面量 / 正则字面量里的花括号。
    """
    i = bundle.index("{", start)
    depth = 0
    n = len(bundle)
    while i < n:
        ch = bundle[i]
        if ch == '"' or ch == "'":
            quote = ch
            i += 1
            while i < n:
                if bundle[i] == "\\":
                    i += 2
                    continue
                if bundle[i] == quote:
                    break
                i += 1
            i += 1
            continue
        if ch == "`":
            i += 1
            while i < n:
                if bundle[i] == "\\":
                    i += 2
                    continue
                if bundle[i] == "`":
                    break
                # 模板里的 ${ ... } 也可能有花括号，粗暴跳过整段
                i += 1
            i += 1
            continue
        if ch == "/" and i + 1 < n and bundle[i + 1] == "/":
            j = bundle.find("\n", i)
            i = n if j < 0 else j
            continue
        if ch == "/" and i + 1 < n and bundle[i + 1] == "*":
            j = bundle.find("*/", i)
            i = n if j < 0 else j + 2
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return i + 1
        i += 1
    raise SystemExit("花括号未配对，函数结束位置找不到")


def count_refs(bundle, name):
    """统计标识符 name 在 bundle 里出现的次数（排除属性访问 obj.name）。"""
    import re
    pat = re.compile(r'(?<![\w$.])%s(?![\w$])' % re.escape(name))
    return len(pat.findall(bundle))


def remove_one(bundle, name):
    import re
    m = re.search(r'function\s+%s\s*\(' % re.escape(name), bundle)
    if not m:
        print("  跳过 %s：找不到声明" % name)
        return bundle, False
    decl_start = m.start()
    end = find_function_end(bundle, decl_start)
    refs = count_refs(bundle, name)
    if refs != 1:
        print("  拒绝删除 %s：全 bundle 出现 %d 次（>1 说明有调用方）" % (name, refs))
        return bundle, False
    removed = bundle[:decl_start] + bundle[end:]
    print("  删除 %-16s 位置 %d，长度 %d" % (name, decl_start, end - decl_start))
    return removed, True


def main():
    names = sys.argv[1:]
    if not names:
        print(__doc__)
        return 1

    text = read_tpl()
    s, e, bundle = extract(text)
    original = bundle

    for name in names:
        bundle, ok = remove_one(bundle, name)
        if ok:
            if not syntax_check(bundle):
                sys.stderr.write("语法校验失败 —— 回滚，未修改文件。\n")
                return 3
            print("    node --check 通过")

    if bundle == original:
        print("没有任何改动。")
        return 0

    new_text = text[:s] + bundle + text[e:]
    if new_text.count("\r\n") != text.count("\r\n"):
        sys.stderr.write("行尾符变化 —— 拒绝写入。\n")
        return 5
    write_tpl(new_text)

    # 回读校验
    _, _, vb = extract(read_tpl())
    for name in names:
        if count_refs(vb, name) != 0:
            sys.stderr.write("回读校验失败：%s 仍存在\n" % name)
            return 4
    print("已写入 %s；bundle %d -> %d（%+d）" % (TPL.name, len(original), len(bundle), len(bundle) - len(original)))
    return 0


if __name__ == "__main__":
    sys.exit(main())

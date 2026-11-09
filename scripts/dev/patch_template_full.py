"""安全编辑 template.html 的【整个文件】（含 <style> / <body> 部分，不只是 module bundle）。

patch_template.py 只能改 <script type="module"> 里的 bundle；
CSS(.crosshair/.loading3d) 和 HTML(#loading3d) 都在 bundle 之外，需要本工具。

与 patch_template.py 相同的纪律：
  1. 每个 old 串在整个文件里必须【恰好出现 1 次】，否则拒绝写入
  2. 二进制读写，UTF-8，不动行尾符
  3. 写回后回读校验
  4. module bundle 部分额外跑 node --check
"""
import argparse
import json
import os
import pathlib
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[2]
TPL = ROOT / "assets" / "template.html"


def read_bytes() -> bytes:
    return TPL.read_bytes()


def bundle_of(text: str) -> tuple:
    s = text.find('<script type="module"')
    if s < 0:
        raise SystemExit("找不到 <script type=\"module\">")
    s = text.index(">", s) + 1
    e = text.find("</script>", s)
    if e < 0:
        raise SystemExit("找不到 </script>")
    return s, e, text[s:e]


def syntax_check(bundle: str) -> bool:
    with tempfile.NamedTemporaryFile("w", suffix=".mjs", delete=False, encoding="utf-8") as f:
        f.write(bundle)
        tmp = f.name
    try:
        r = subprocess.run(["node", "--check", tmp], capture_output=True, text=True,
                           encoding="utf-8", errors="replace")
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


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pairs-file", required=True)
    ap.add_argument("--note", default="")
    args = ap.parse_args()

    with open(args.pairs_file, encoding="utf-8") as f:
        pairs = json.load(f)
    pairs = [(d["find"], d.get("replace_with", "")) for d in pairs]

    raw = read_bytes()
    text = raw.decode("utf-8")

    for old, new in pairs:
        n = text.count(old)
        if n != 1:
            sys.stderr.write("锚点在整个文件中出现 %d 次（要求恰好 1 次）——拒绝修改。\n锚点：%s\n"
                             % (n, old[:160]))
            return 2
        if old == new:
            sys.stderr.write("--find 与 --replace-with 相同\n")
            return 2

    new_text = text
    for old, new in pairs:
        new_text = new_text.replace(old, new)

    # 行尾符守卫
    if new_text.count("\r\n") != text.count("\r\n"):
        sys.stderr.write("行尾符数量变化（%d -> %d）——拒绝修改。\n"
                         % (text.count("\r\n"), new_text.count("\r\n")))
        return 5

    # module bundle 语法校验
    _, _, nb = bundle_of(new_text)
    if not syntax_check(nb):
        sys.stderr.write("bundle 语法校验未通过，文件未被修改。\n")
        return 3

    TPL.write_bytes(new_text.encode("utf-8"))

    # 回读校验（注意：不能简单查 old 是否消失 ——
    # 新代码里可能包含 old 作为子串（例如 old="function Aw(){"，
    # 而新代码以 "function Aw(){" 结尾）。改为逐对检查替换结果唯一。
    verify = read_bytes().decode("utf-8")
    for old, new in pairs:
        if new and verify.count(new) != 1:
            sys.stderr.write("回读校验失败：替换结果未唯一出现 -> %s\n" % new[:160])
            return 4
        if not new and verify.count(old) != 0:
            sys.stderr.write("回读校验失败：待删除锚点仍存在 -> %s\n" % old[:160])
            return 4

    print("已修改 %s（%d 处）" % (TPL.name, len(pairs)))
    for i, (old, new) in enumerate(pairs, 1):
        print("  [%d] 长度 %+d" % (i, len(new) - len(old)))
    print("  行尾符：LF %d / CRLF %d（保持不变）" % (text.count("\n"), text.count("\r\n")))
    print("  node --check：通过")
    if args.note:
        print("  说明：%s" % args.note)
    return 0


if __name__ == "__main__":
    sys.exit(main())

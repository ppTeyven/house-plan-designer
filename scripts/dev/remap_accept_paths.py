"""把 scripts/ 里指向已删除的「验收/」目录的路径，重映射到新的落点。

【背景】
  用户要求删掉验收站目录（验收/）。但 scripts/dev 下有 100+ 个脚本把
  产物写到 验收/models、验收/previews、验收/logs、验收/refs —— 目录没了，
  这些脚本一跑就 FileNotFoundError。

【为什么不直接删掉这些脚本】
  它们里有一批是【还活着】的贴图/材质流水线（产出 assets/furnlib/*.jpg，
  是主程序运行时真正在用的 PBR 贴图），以及大量有工程价值的分析工具。
  删掉等于把可复用的工具链一起扔了。路径重映射是保留工具的最小改动。

【映射规则】
  验收/models   -> assets/furnlib     （家具模型真源唯一化后的唯一真源）
  验收/previews -> scripts/dev/_previews
  验收/logs     -> scripts/dev/_logs
  验收/refs     -> scripts/dev/_refs
  验收/assets   -> assets
  其它 验收/xxx -> scripts/dev/_accept_xxx

【用法】
  python scripts/dev/remap_accept_paths.py --dry-run    # 只看会改哪些
  python scripts/dev/remap_accept_paths.py --apply      # 实际写入
"""
import argparse
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
DEV = ROOT / "scripts"

RULES = [
    (r'os\.path\.join\(ROOT,\s*"验收",\s*"models"\)', 'os.path.join(ROOT, "assets", "furnlib")'),
    (r'os\.path\.join\(ROOT,\s*"验收",\s*"previews"\)', 'os.path.join(ROOT, "scripts", "dev", "_previews")'),
    (r'os\.path\.join\(ROOT,\s*"验收",\s*"logs"\)', 'os.path.join(ROOT, "scripts", "dev", "_logs")'),
    (r'os\.path\.join\(ROOT,\s*"验收",\s*"refs"\)', 'os.path.join(ROOT, "scripts", "dev", "_refs")'),
    (r'os\.path\.join\(ROOT,\s*"验收"\)', 'os.path.join(ROOT, "scripts", "dev", "_accept")'),
    (r'os\.path\.join\(ROOT,\s*"验收",\s*"assets"\)', 'os.path.join(ROOT, "assets")'),
    (r'os\.path\.join\(ROOT,\s*"验收",\s*"([^"]+)"\)', r'os.path.join(ROOT, "scripts", "dev", "_accept_\1")'),
    # 字面量路径（正斜杠 / 反斜杠）
    (r'验收/models', 'assets/furnlib'),
    (r'验收\\models', 'assets\\furnlib'),
    (r'验收/previews', 'scripts/dev/_previews'),
    (r'验收\\previews', 'scripts\\dev\\_previews'),
    (r'验收/logs', 'scripts/dev/_logs'),
    (r'验收\\logs', 'scripts\\dev\\_logs'),
    (r'验收/refs', 'scripts/dev/_refs'),
    (r'验收\\refs', 'scripts\\dev\\_refs'),
    (r'验收/assets', 'assets'),
    (r'验收\\assets', 'assets'),
]

# 注意：'验收' 作为目录名在注释/文档里出现时也要改，但先只处理代码里的路径。
CODE_PATH = re.compile(r'(?:ROOT|BASE|base|root|__file__|os\.path\.dirname\([^)]*\))[^"\']{0,40}["\']验收')

EXT = {".py", ".mjs", ".js", ".ps1", ".sh", ".json", ".md"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    if not args.apply and not args.dry_run:
        ap.print_help()
        return 1

    changed = []
    total_subs = 0
    for f in sorted(DEV.rglob("*")):
        if not f.is_file() or f.suffix not in EXT:
            continue
        if "node_modules" in f.parts:
            continue
        src = f.read_text(encoding="utf-8", errors="replace")
        if "验收" not in src:
            continue
        if f.name == pathlib.Path(__file__).name:
            continue  # 映射表本身不能被改
        if "classify_accept_refs" in f.name or "remap_accept_paths" in f.name:
            continue
        new = src
        n = 0
        for pat, rep in RULES:
            # 用 lambda 而不是字符串替换：替换串里的 \1 会被 re 当成转义序列。
            # 只有模式里真的有捕获组时才做组替换，否则原样返回。
            def _sub(m, _r=rep, _p=pat):
                if "\\1" not in _r:
                    return _r
                if m.groups():
                    return _r.replace("\\1", m.group(1))
                return _r
            new, k = re.subn(pat, _sub, new)
            n += k
        # 剩下的裸 "验收/xxx" 字面量（不在 os.path.join 里）
        def repl_any(m):
            inner = m.group(1)
            if inner in ("models", "previews", "logs", "refs"):
                return '"' + {
                    "models": "assets/furnlib",
                    "previews": "scripts/dev/_previews",
                    "logs": "scripts/dev/_logs",
                    "refs": "scripts/dev/_refs",
                }[inner] + '"'
            return '"scripts/dev/_accept_' + inner + '"'
        new, k2 = re.subn(r'["\']验收[/\\]([^"\'/\\]+)["\']', repl_any, new)
        n += k2
        if new != src:
            changed.append((f.relative_to(ROOT).as_posix(), n))
            total_subs += n
            if args.apply:
                f.write_text(new, encoding="utf-8")

    print("改动文件 %d 个，共 %d 处替换" % (len(changed), total_subs))
    for p, n in changed:
        print("  %-60s %d 处" % (p, n))
    if args.apply:
        print("\n已写入。")
    else:
        print("\n（dry-run，未写入）")
    return 0


if __name__ == "__main__":
    sys.exit(main())

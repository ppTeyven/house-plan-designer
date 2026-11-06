"""判定 scripts/ 下的脚本是「在用」还是「一次性补丁残留」。

【判定依据】
  1. SKILL.md / README.md / HANDOFF.md 里有没有提到它 —— 提到了就是在用
  2. 它是不是「补丁型」脚本：读一个文件 → 正则替换 → 写回
     补丁型脚本只对【当时的】文件内容有效，源文件一改就失效（零命中）
  3. 它的目标锚点在当前 assets/template.html 里还有没有命中
     零命中 = 它的修改早已被别的手段覆盖（或已进 git 历史），留着是误导

【输出】
  对每个脚本打印：被文档引用？是否补丁型？目标锚点命中数？结论
"""
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
TPL = ROOT / "assets" / "template.html"

DOCS = ["SKILL.md", "README.md", "HANDOFF.md", "docs/decisions-furniture-library.md"]

tpl = TPL.read_bytes().decode("utf-8")

# 补丁型脚本的特征
PATCH_SIGNS = [
    "replace(", ".replace(", "re.sub", "assert old", "anchor", "ANCHOR",
    "if old not in", "count(", "assert count", "patch", "PATCH",
]


def is_patch_style(src):
    hits = sum(1 for s in PATCH_SIGNS if s in src)
    return hits >= 2


def extract_anchors(src):
    """从补丁脚本里抽出它要找的目标字符串（尽量准）。"""
    out = []
    # 形如  old = "...."   /  anchor = '....'  /  find = "...."
    for m in re.finditer(r'''(?:old|anchor|find|needle|target|pat|pat1|pat2|OLD|ANCHOR)\s*=\s*(?:r?)("([^"]{6,})"|'([^']{6,})')''', src):
        s = m.group(2) or m.group(3)
        out.append(s)
    # 或者字面量里的长串
    for m in re.finditer(r'''\b(?:replace|re\.sub|sub)\s*\(\s*(?:r?)"([^"]{12,})"''', src):
        out.append(m.group(1))
    return out


results = []
for f in sorted(SCRIPTS.glob("*.py")) + sorted(SCRIPTS.glob("*.mjs")):
    name = f.name
    src = f.read_text(encoding="utf-8", errors="replace")

    # 1) 文档引用
    refs = []
    for d in DOCS:
        p = ROOT / d
        if p.exists() and name in p.read_text(encoding="utf-8", errors="replace"):
            refs.append(d)
    # 也检查 dev 目录里其它脚本的引用
    cross = []
    for g in SCRIPTS.rglob("*"):
        if g.is_file() and g.suffix in (".py", ".mjs", ".js") and g != f:
            try:
                if name in g.read_text(encoding="utf-8", errors="replace"):
                    cross.append(g.relative_to(ROOT).as_posix())
            except Exception:
                pass

    patch = is_patch_style(src)
    anchors = extract_anchors(src)
    matched = 0
    for a in anchors:
        if a and a in tpl:
            matched += 1

    results.append({
        "name": name, "refs": refs, "cross": cross, "patch": patch,
        "anchors": len(anchors), "matched": matched,
    })

print("%-26s %-6s %-6s %-8s %-8s %s" % ("脚本", "文档引用", "被引用", "补丁型", "锚点命中", "结论"))
print("-" * 96)
for r in results:
    doc = ",".join(r["refs"]) or "-"
    cross = ("%d处" % len(r["cross"])) if r["cross"] else "-"
    verdict = "在用" if r["refs"] or r["cross"] else ("疑似残留" if r["patch"] else "待定")
    print("%-26s %-6s %-6s %-8s %-8s %s" % (
        r["name"], "有" if r["refs"] else "无", cross,
        "是" if r["patch"] else "否",
        "%d/%d" % (r["matched"], r["anchors"]),
        verdict))

"""批量语法校验 scripts/ 下的 python / node 脚本。

【为什么需要】
  路径重映射、删脚本之后，必须确认没有把任何脚本改坏。
  python 用 compile() 校验；node 用 --check 校验（.mjs/.js）。

用法：python scripts/dev/check_scripts_syntax.py
"""
import pathlib
import subprocess
import sys
import tempfile
import os

ROOT = pathlib.Path(__file__).resolve().parents[2]
DEV = ROOT / "scripts"

py_ok = py_bad = 0
bad_list = []

for f in sorted(DEV.rglob("*.py")):
    if "node_modules" in f.parts or "_archive" in f.parts:
        continue
    try:
        src = f.read_text(encoding="utf-8")
        compile(src, str(f), "exec")
        py_ok += 1
    except SyntaxError as e:
        py_bad += 1
        bad_list.append("%s: %s" % (f.relative_to(ROOT).as_posix(), e))
    except Exception as e:
        py_bad += 1
        bad_list.append("%s: %s" % (f.relative_to(ROOT).as_posix(), e))

js_ok = js_bad = 0
for f in sorted(list(DEV.rglob("*.mjs")) + list(DEV.rglob("*.js"))):
    if "node_modules" in f.parts or "_archive" in f.parts:
        continue
    with tempfile.NamedTemporaryFile("w", suffix=".mjs", delete=False, encoding="utf-8") as t:
        t.write(f.read_text(encoding="utf-8", errors="replace"))
        tmp = t.name
    r = subprocess.run(["node", "--check", tmp], capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    os.unlink(tmp)
    if r.returncode == 0:
        js_ok += 1
    else:
        js_bad += 1
        err = (r.stderr or "").strip().splitlines()
        bad_list.append("%s: %s" % (f.relative_to(ROOT).as_posix(),
                                    err[1] if len(err) > 1 else (err[0] if err else "?")))

print("Python: %d 通过, %d 失败" % (py_ok, py_bad))
print("Node  : %d 通过, %d 失败" % (js_ok, js_bad))
if bad_list:
    print("\n失败明细：")
    for b in bad_list:
        print("  " + b)
sys.exit(1 if bad_list else 0)

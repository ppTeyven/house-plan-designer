"""template.html 改动后的完整验证。

【为什么需要独立脚本】
  patch_template.py / remove_fn.py 是「改」的工具；这个是「验」的工具。
  两者分开，避免验证逻辑和修改逻辑互相掩盖问题。

检查项：
  1. node --check 语法
  2. 行尾符与 HEAD 一致（压缩产物必须逐字节保真）
  3. 关键符号状态：死函数已删、泄漏已除、崩溃已修
  4. bundle 内没有残留的调试钩子
"""
import pathlib
import re
import subprocess
import sys
import tempfile
import os

ROOT = pathlib.Path(__file__).resolve().parents[2]
TPL = ROOT / "assets" / "template.html"

ok_all = True


def check(name, cond, detail=""):
    global ok_all
    mark = "OK " if cond else "FAIL"
    if not cond:
        ok_all = False
    print("[%s] %s%s" % (mark, name, ("  -> " + detail) if detail else ""))


raw = TPL.read_bytes()
text = raw.decode("utf-8")
s = text.find('<script type="module"')
s = text.index(">", s) + 1
e = text.find("</script>", s)
bundle = text[s:e]

# 1) 语法
with tempfile.NamedTemporaryFile("w", suffix=".mjs", delete=False, encoding="utf-8") as f:
    f.write(bundle)
    tmp = f.name
r = subprocess.run(["node", "--check", tmp], capture_output=True, text=True,
                   encoding="utf-8", errors="replace")
os.unlink(tmp)
check("node --check 语法", r.returncode == 0, (r.stderr or "")[:300])

# 2) 行尾符
crlf = raw.count(b"\r\n")
lf = raw.count(b"\n")
check("行尾符保持 LF（无 CRLF）", crlf == 0, "CRLF=%d LF=%d" % (crlf, lf))

# 与 HEAD 比对行尾符
try:
    head = subprocess.run(["git", "show", "HEAD:assets/template.html"],
                          cwd=str(ROOT), capture_output=True)
    if head.returncode == 0:
        hb = head.stdout
        check("行尾符与 HEAD 一致", hb.count(b"\r\n") == crlf,
              "HEAD CRLF=%d, 现在 CRLF=%d" % (hb.count(b"\r\n"), crlf))
except Exception as e:
    print("[warn] 无法比对 HEAD：%s" % e)

# 3) 死函数必须为 0 次
DEAD = ['G7', 'OL', 'UL', '__furnWallTex', 'skyDim', 'skyFade',
        '__riSmooth', '__syncCam3d', '__riToFull']
for n in DEAD:
    cnt = len(re.findall(r'(?<![\w$.])%s(?![\w$])' % re.escape(n), bundle))
    check("死函数 %s 已删除" % n, cnt == 0, "剩余 %d 次" % cnt)

# 4) 泄漏必须清干净
check("__YV_TRACE 已移除", "__YV_TRACE" not in bundle)
check("__YVT 已移除", "__YVT" not in bundle)

# 5) 崩溃修复
old_bug = "const a=o.material;if(!a.userData._cached)"
check("数组材质崩溃已修", old_bug not in bundle and "Array.isArray(o.material)" in bundle)

# 6) 死分支
check("if(false) 已清除", not re.search(r'if\s*\(\s*false\s*\)', bundle))

# 7) 孤立实例
# 注意：不能用 "new Be;" 粗判 —— 那会命中 `const Gn=new Be;` 这类【具名常量声明】。
# 孤立实例的特征是：前面不是标识符/等号（不是赋值给某个变量）。
orphan = re.search(r'(?<![\w$.=])new Be\s*;', bundle)
check("孤立 new Be 已清除", orphan is None,
      ("仍存在于 offset %d" % orphan.start()) if orphan else "")
check("具名 new Be 常量保留", "const Gn=new Be" in bundle)

# 8) bundle 规模
print()
print("bundle 长度: %d" % len(bundle))
print("template.html 大小: %d 字节" % len(raw))

print()
print("=== 总结: %s ===" % ("全部通过" if ok_all else "有失败项"))
sys.exit(0 if ok_all else 1)

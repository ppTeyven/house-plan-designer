"""从 template.html 抽出内联 <script type="module"> 做语法校验。

【为什么需要】
  handbook 附录 A：修改压缩/构建产物后必须做语法校验，
  语法不通过 = 任务未完成。
  template.html 是 2MB 单文件，里面的 ES module 只能靠抽取后 node --check 验证。

用法：python check_tpl_syntax.py
"""
import os
import re
import subprocess
import sys

ROOT = r'D:\house planner\house-plan-designer-main'
TP = os.path.join(ROOT, "assets", "template.html")
TMP = os.path.join(ROOT, "assets", "dev", "_tpl_module_check.mjs")

s = open(TP, encoding="utf-8").read()

# 抽取所有 type="module" 的 script 内容
blocks = re.findall(r'<script[^>]*type=["\']module["\'][^>]*>(.*?)</script>', s, re.S)
if not blocks:
    print("没找到 type=module 的 script —— 校验跳过")
    sys.exit(0)

print("内联 module 块数:", len(blocks))
body = "\n".join(blocks)
print("抽取字节: %d" % len(body))

os.makedirs(os.path.dirname(TMP), exist_ok=True)
with open(TMP, "w", encoding="utf-8") as f:
    f.write(body)
r = subprocess.run(["node", "--check", TMP], capture_output=True, text=True)
print("node --check exit:", r.returncode)
if r.stdout and r.stdout.strip():
    print("stdout:", r.stdout[:2000])
if r.stderr and r.stderr.strip():
    print("stderr:", r.stderr[:3000])
sys.exit(r.returncode)

# -*- coding: utf-8 -*-
"""校验 template.html module script 语法（按 ES module 解析，支持 import.meta）。"""
import io
import os
import re
import subprocess
import sys

P = sys.argv[1] if len(sys.argv) > 1 else r'D:\house planner\house-plan-designer-main\assets\template.html'
s = io.open(P, encoding='utf-8').read()

CHK = (
    "const fs=require('fs');\n"
    "const vm=require('vm');\n"
    "const src=fs.readFileSync(process.argv[2],'utf8');\n"
    "try{ new vm.SourceTextModule(src); process.stdout.write('OK'); }\n"
    "catch(e){ process.stdout.write('ERR:'+e.message); }\n"
)
open('_synchk4.cjs', 'w', encoding='utf-8').write(CHK)

bad = 0
for i, m in enumerate(re.finditer(r'<script[^>]*>([\s\S]*?)</script>', s), 1):
    code = m.group(1)
    if not code.strip():
        continue
    open('_synsrc4.mjs', 'w', encoding='utf-8').write(code)
    r = subprocess.run(
        ['node', '--experimental-vm-modules', '_synchk4.cjs', '_synsrc4.mjs'],
        capture_output=True, text=True)
    out = r.stdout.strip()
    if not out:
        out = 'NODE-FAIL ' + r.stderr.strip()[:300]
    print('script#%d len=%d -> %s' % (i, len(code), out))
    if out != 'OK':
        bad += 1
print('RESULT:', 'ALL OK' if bad == 0 else '%d script(s) broken' % bad)

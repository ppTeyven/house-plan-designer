# -*- coding: utf-8 -*-
"""可靠的内联 module 语法校验器（Windows/GBK 安全）。

handbook 附录 A 要求：修改压缩产物后必须做语法校验，语法不通过 = 任务未完成。
用法：python check_syntax.py
"""
import io
import os
import re
import subprocess
import sys

ROOT = r'D:\house planner\house-plan-designer-main'
TP = os.path.join(ROOT, 'assets', 'template.html')
TMP = os.path.join(ROOT, 'assets', 'dev', '_tpl_module_check.mjs')


def main():
    with io.open(TP, encoding='utf-8') as f:
        s = f.read()

    blocks = re.findall(r'<script[^>]*type=["\']module["\'][^>]*>(.*?)</script>', s, re.S)
    if not blocks:
        print('没找到 type=module 的 script —— 校验跳过')
        return 0

    body = '\n'.join(blocks)
    print('内联 module 块数: %d   抽取字节: %d' % (len(blocks), len(body)))

    os.makedirs(os.path.dirname(TMP), exist_ok=True)
    with io.open(TMP, 'w', encoding='utf-8', newline='\n') as f:
        f.write(body)

    # Windows 下 node 默认可能按本地编码读；显式用 utf-8
    env = dict(os.environ)
    env['NODE_OPTIONS'] = ''
    r = subprocess.run(['node', '--check', TMP], capture_output=True, env=env)

    out = (r.stdout or b'').decode('utf-8', 'replace')
    err = (r.stderr or b'').decode('utf-8', 'replace')
    print('node --check exit: %d' % r.returncode)
    if out.strip():
        print(out[:2000])
    if err.strip():
        print(err[:4000])
    return r.returncode


if __name__ == '__main__':
    sys.exit(main())

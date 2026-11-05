"""精确列出「二次单位换算」的函数 + 文件 + 行号，并给出自动修复补丁。"""
import io
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
FILES = ['geo_models.py', 'geo_models_extra.py', 'geo_models_extra2.py',
         'geo_models_extra3.py', 'geo_models_extra4.py', 'geo_models_free.py']

FUNC_RE = re.compile(r'^def (\w+)\(', re.M)
MM_RE = re.compile(r'\bM\(\s*([^()]*)\)')
# 已经是「米」的变量名（转换行里的那些）
CONV_RE = re.compile(
    r'^\s*(\w+)\s*,\s*(\w+)\s*,\s*(\w+)\s*=\s*M\((\w+)\)\s*,\s*M\((\w+)\)\s*,\s*M\((\w+)\)')


def find_conversion(blines):
    """返回 (行号, [变量名]) 或 None"""
    for ln, line in enumerate(blines):
        st = line.strip()
        if st.startswith('#'):
            continue
        m = CONV_RE.match(st)
        if m:
            return ln, [m.group(1), m.group(2), m.group(3)]
    return None


def scan(path, apply_fix=False):
    src = io.open(path, encoding='utf-8').read()
    starts = [(m.start(), m.group(1)) for m in FUNC_RE.finditer(src)]
    out = []
    for i, (pos, name) in enumerate(starts):
        end = starts[i + 1][0] if i + 1 < len(starts) else len(src)
        body = src[pos:end]
        blines = body.split('\n')
        conv = find_conversion(blines)
        if conv is None:
            continue
        conv_ln, conv_vars = conv
        hits = []
        for ln, line in enumerate(blines):
            if ln <= conv_ln:
                continue
            st = line.strip()
            if st.startswith('#') or st.startswith('*'):
                continue
            for m in MM_RE.finditer(line):
                inner = m.group(1)
                # 变量名必须出现在 conv_vars 里，且不是别的标识符的一部分
                for v in conv_vars:
                    if re.search(r'(?<![A-Za-z0-9_.])' + re.escape(v) +
                                 r'(?![A-Za-z0-9_])', inner):
                        hits.append((ln, line))
                        break
                else:
                    continue
                break
        if hits:
            out.append((name, conv_ln, conv_vars, hits))
    return out


if __name__ == '__main__':
    total = 0
    for f in FILES:
        p = os.path.join(HERE, f)
        if not os.path.exists(p):
            continue
        res = scan(p)
        if not res:
            continue
        print('=' * 70)
        print(f)
        for name, conv_ln, vars_, hits in res:
            print('  %-26s 转换行 L%d  变量 %s  → %d 处'
                  % (name, conv_ln + 1, '/'.join(vars_), len(hits)))
            total += len(hits)
    print('\n总计 %d 处二次换算' % total)

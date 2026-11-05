"""列出每个 geo builder 里所有 add_box 的 Z 侧分布，供人工一次性核对。

用法：python dump_orient_parts.py [名字片段...]
"""
import io
import os
import re
import sys

BL = os.path.dirname(os.path.abspath(__file__))
FILES = ['geo_models.py', 'geo_models_free.py', 'geo_models_extra.py',
         'geo_models_extra2.py', 'geo_models_extra3.py', 'geo_models_extra4.py']

WORDS = ['床头板', '床头', '靠背', '背板', '柜门', '枕头', '靠垫', '屏风',
         '正面', '朝向', '门板', '抽屉面', '柜面']


def split_args(s):
    out, depth, cur = [], 0, ''
    for ch in s:
        if ch in '([{':
            depth += 1
        elif ch in ')]}':
            depth -= 1
        if ch == ',' and depth == 0:
            out.append(cur.strip())
            cur = ''
        else:
            cur += ch
    if cur.strip():
        out.append(cur.strip())
    return out


def all_boxes(lines):
    """返回 [(行号, z表达式, 注释)]"""
    out = []
    for j, ln in enumerate(lines):
        if 'add_box' not in ln:
            continue
        # 往前找最近的注释
        cmt = ''
        for k in range(j - 1, max(-1, j - 6), -1):
            t = lines[k].strip()
            if t.startswith('#'):
                cmt = t.lstrip('# ').strip()
                break
        text = '\n'.join(lines[j:j + 12])
        m = re.search(r'add_box\s*\(', text)
        if not m:
            continue
        k, depth, st = m.end() - 1, 0, m.end() - 1
        while k < len(text):
            if text[k] == '(':
                depth += 1
            elif text[k] == ')':
                depth -= 1
                if depth == 0:
                    break
            k += 1
        args = split_args(text[st + 1:k])
        ctr = None
        for a in args:
            if a.startswith('center='):
                ctr = a.split('=', 1)[1]
        if ctr is None and len(args) >= 3:
            ctr = args[2]
        if ctr is None:
            continue
        cp = split_args(ctr.strip('()'))
        if len(cp) < 3:
            continue
        out.append((j, cp[2].strip(), cmt))
    return out


def sign_of(expr):
    e = expr.replace(' ', '').replace('M(', 'M')
    e = e.replace('M(d)/2', 'H').replace('d/2', 'H')
    e = e.replace('M(d)', 'D').replace('d', 'D')
    if 'H' not in e:
        return None
    prefix = e[:e.index('H')]
    ops = list(re.finditer(r'[-+]', prefix))
    if not ops:
        return None
    return -1 if ops[-1].group(0) == '-' else 1


filt = sys.argv[1:]
for f in FILES:
    p = os.path.join(BL, f)
    if not os.path.exists(p):
        continue
    s = io.open(p, encoding='utf-8').read()
    for fm in re.finditer(r'def (build_\w+)\(', s):
        name = fm.group(1)
        if filt and not any(x in name for x in filt):
            continue
        st = fm.start()
        nxt = s.find('\ndef ', st + 1)
        body = s[st:nxt if nxt > 0 else st + 6000]
        lines = body.split('\n')
        boxes = all_boxes(lines)
        if not boxes:
            continue
        # 只输出有语义注释的，或 z 有明确符号且靠端的
        interesting = []
        for j, z, cmt in boxes:
            sg = sign_of(z)
            has_word = any(w in cmt for w in WORDS)
            if has_word or sg is not None:
                interesting.append((j, z, cmt, sg))
        if not interesting:
            continue
        print('### %s :: %s' % (f, name))
        for j, z, cmt, sg in interesting:
            mark = ('%+d' % sg) if sg is not None else ' ? '
            print('   %-4s z=%-30s | %s' % (mark, z[:30], cmt[:44]))
        print()

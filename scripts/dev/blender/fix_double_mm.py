"""【正确版】修复 builder 里的「二次单位换算」。

背景
----
很多 builder 长这样：
    def build_xxx(w=1800, d=900, h=1050):
        w, d, h = M(w), M(d), M(h)      ← 这行把 w/d/h 变成了【米】
        m.add_box((M(w), M(h) * 0.62, M(d)), ...)   ← 又套了一层 M()
                                                   M(0.7)=0.0007m=0.7mm
⇒ 家具的每个部件都被压成 0.7mm 的薄片 —— 渲染出来就是"乱码/纸片"。

为什么不能简单删掉 M()
------------------------
`M(h - 60)` 这种混写：h 已是米，60 是毫米。
    错删 M  →  h - 60       （单位错了 1000 倍）
    正确    →  h - M(60)
所以必须做「加法项级」拆分：
    · 引用了米制变量的项 → 保留原样（去掉 M 外壳）
    · 纯数字项          → 保留 M()（毫米字面量）
    · 乘法里带无量纲小数 → 跟米制项一起保留

实现
----
逐行处理函数体，维护一个「已知是米」的变量集合：
    · 转换行之后 w/d/h 是米
    · `seg = w / 3`      → seg 是米
    · `back = d * 0.20`  → back 是米
    · `x = M(520)`       → x 是毫米
然后把每个 M(expr) 按加法项拆开，逐项决定去壳或保留。

用法：
  python fix_double_mm.py            # 只报告（打印将要改的每一行）
  python fix_double_mm.py --apply    # 改文件（备份 .bak）
"""
import io
import os
import re
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
FILES = ['geo_models.py', 'geo_models_extra.py', 'geo_models_extra2.py',
         'geo_models_extra3.py', 'geo_models_extra4.py', 'geo_models_free.py']

FUNC_RE = re.compile(r'^def (\w+)\(', re.M)
CONV_RE = re.compile(
    r'^\s*(\w+)\s*,\s*(\w+)\s*,\s*(\w+)\s*=\s*M\((\w+)\)\s*,\s*M\((\w+)\)\s*,\s*M\((\w+)\)')
ASSIGN_RE = re.compile(r'^(\s*)([A-Za-z_]\w*)\s*=\s*(?!=)(.+?)\s*$')


# ---------------------------------------------------------------- 表达式工具
def split_additive(expr):
    """按顶层 + / - 把表达式拆成带符号的项列表。"""
    terms = []
    depth = 0
    cur = ''
    sign = '+'
    i = 0
    n = len(expr)
    while i < n:
        c = expr[i]
        if c in '([{':
            depth += 1
        elif c in ')]}':
            depth -= 1
        if depth == 0 and c in '+-' and cur.strip():
            # 负号/减号
            if c == '-' and cur.strip()[-1] in '*/+-':
                cur += c
                i += 1
                continue
            terms.append((sign, cur))
            sign = c
            cur = ''
            i += 1
            continue
        cur += c
        i += 1
    if cur.strip():
        terms.append((sign, cur))
    return terms


def ids_in(text):
    """返回 text 里所有标识符（去掉属性访问与数字）。"""
    out = []
    for m in re.finditer(r'(?<![A-Za-z0-9_.])([A-Za-z_]\w*)(?![A-Za-z0-9_])', text):
        out.append(m.group(1))
    return out


def is_pure_number(text):
    t = text.strip()
    if not t:
        return False
    try:
        float(t)
        return True
    except ValueError:
        return False


def rewrite_m_call(expr, meter_vars, mm_vars):
    """把 expr（已确认在 M(...) 内）改写。

    返回 (新表达式, 是否改动)
    """
    terms = split_additive(expr)
    if len(terms) == 1:
        term = terms[0][1].strip()
        idl = set(ids_in(term))
        # 纯数字 → 保留 M
        if is_pure_number(term):
            return expr, False
        # 引用了米制变量 → 去壳
        if idl & meter_vars:
            return term, True
        # 引用了毫米变量（如 M(520) 定义的 x）→ 保留 M
        if idl & mm_vars:
            return expr, False
        # 未知标识符 + 数字（如 i * 22）→ 保留 M（毫米）
        return expr, False

    # 多项：逐项判断
    parts = []
    changed = False
    for sign, term in terms:
        t = term.strip()
        idl = set(ids_in(t))
        if is_pure_number(t):
            parts.append((sign, t, True))       # 数字 → 要保留 M
        elif idl & meter_vars:
            parts.append((sign, t, False))      # 米制 → 去壳
        else:
            parts.append((sign, t, True))
    if not any(p[2] for p in parts):
        return expr, False

    out = ''
    for idx, (sign, t, keep_m) in enumerate(parts):
        piece = ('M(%s)' % t) if keep_m else t
        if idx == 0:
            out = piece if sign == '+' else ('-' + piece)
        else:
            out += (' + ' + piece) if sign == '+' else (' - ' + piece)
        changed = True
    return out, changed


def rewrite_line(line, meter_vars, mm_vars):
    """把一行里所有 M(...) 改写（只处理顶层的 M 调用）。"""
    out = ''
    i = 0
    n = len(line)
    changed = False
    while i < n:
        m = re.compile(r'(?<![A-Za-z0-9_.])M\(').search(line, i)
        if not m:
            out += line[i:]
            break
        out += line[i:m.start()]
        depth = 1
        j = m.end()
        while j < n and depth:
            if line[j] == '(':
                depth += 1
            elif line[j] == ')':
                depth -= 1
            j += 1
        inner = line[m.end():j - 1]
        new, ch = rewrite_m_call(inner, meter_vars, mm_vars)
        out += new if ch else line[m.start():j]
        changed = changed or ch
        i = j
    return out, changed


# ---------------------------------------------------------------- 主流程
def find_conv(blines):
    for ln, line in enumerate(blines):
        st = line.strip()
        if st.startswith('#'):
            continue
        m = CONV_RE.match(st)
        if m:
            return ln, [m.group(1), m.group(2), m.group(3)]
    return None, None


def fix_func_body(blines, verbose=False):
    conv_ln, conv_vars = find_conv(blines)
    if conv_ln is None:
        return blines, False, []
    meter = set(conv_vars)
    mm = set()
    changed = False
    log = []
    for ln in range(conv_ln + 1, len(blines)):
        line = blines[ln]
        st = line.strip()
        if not st or st.startswith('#') or st.startswith('*'):
            continue
        new, ch = rewrite_line(line, meter, mm)
        if ch:
            blines[ln] = new
            changed = True
            log.append((ln + 1, line.strip(), new.strip()))
        # 更新变量类型集合
        am = ASSIGN_RE.match(new)
        if am:
            name = am.group(2)
            rhs = am.group(3)
            idl = set(ids_in(rhs))
            if idl & meter:
                meter.add(name)
                mm.discard(name)
            elif is_pure_number(rhs.strip()):
                mm.add(name)
                meter.discard(name)
    return blines, changed, log


def fix_file(path, apply_fix):
    src = io.open(path, encoding='utf-8').read()
    starts = [(m.start(), m.group(1)) for m in FUNC_RE.finditer(src)]
    report = []
    for i in range(len(starts) - 1, -1, -1):
        pos, name = starts[i]
        end = starts[i + 1][0] if i + 1 < len(starts) else len(src)
        body = src[pos:end]
        blines = body.split('\n')
        blines, ch, log = fix_func_body(blines)
        if ch:
            src = src[:pos] + '\n'.join(blines) + src[end:]
            report.append((name, log))
    if report and apply_fix:
        shutil.copy2(path, path + '.bak')
        io.open(path, 'w', encoding='utf-8', newline='').write(src)
    return report


if __name__ == '__main__':
    apply_fix = '--apply' in sys.argv
    print('模式: %s' % ('写入' if apply_fix else '只报告'))
    for f in FILES:
        p = os.path.join(HERE, f)
        if not os.path.exists(p):
            continue
        rep = fix_file(p, apply_fix)
        if not rep:
            continue
        print('=' * 72)
        print(f)
        for name, log in rep:
            print('  --- %s (%d 处)' % (name, len(log)))
            for ln, old, new in log:
                print('    L%-5d - %s' % (ln, old))
                print('    %7s + %s' % ('', new))

import os, re, io

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
p = os.path.join(ROOT, 'assets', 'template.html')
s = open(p, encoding='utf-8').read()


def func_body(name):
    """Extract a minified function body by brace matching."""
    i = s.find('function %s(' % name)
    if i < 0:
        return None, -1
    # find first '{' after the arg list
    j = s.find('{', i)
    depth = 0
    k = j
    while k < len(s):
        c = s[k]
        if c == '{':
            depth += 1
        elif c == '}':
            depth -= 1
            if depth == 0:
                return s[i:k + 1], i
        k += 1
    return None, i


out = io.StringIO()
for fn in ['hn', 'Wd', 'gs', 'Is']:
    b, i = func_body(fn)
    out.write('===== function %s()  at %d  len %s =====\n' % (fn, i, len(b) if b else 'NA'))
    if b:
        out.write((b[:3000]) + '\n\n')

out.write('===== capMat occurrences =====\n')
for m in re.finditer(r'capMat', s):
    out.write('  %d  ...%s...\n' % (m.start(), s[max(0, m.start() - 120):m.start() + 120].replace('\n', ' | ')))
    out.write('\n')

out.write('===== colorPlan / Wd usage of wallsG =====\n')
for m in re.finditer(r'wallsG', s):
    out.write('  %d  ...%s...\n' % (m.start(), s[max(0, m.start() - 100):m.start() + 140].replace('\n', ' | ')))
    out.write('\n')

open('_audit_flat.txt', 'w', encoding='utf-8').write(out.getvalue())
print('written, len', len(out.getvalue()))

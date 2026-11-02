import pathlib, re
t = pathlib.Path('assets/template.html').read_text(encoding='utf-8')
for m in re.finditer(r'#toast\{[^}]*\}', t):
    s = m.group(0)
    print('POS', m.start(), 'LEN', len(s))
    print(s[:600])
    print('---')

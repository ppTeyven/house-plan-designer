import pathlib, re
t=pathlib.Path('assets/template.html').read_text(encoding='utf-8')
for pat in [r'function tL', r'const tL=', r'tL\s*=\s*\(', r'\btL\(']:
    print('===', pat)
    for m in re.finditer(pat, t):
        p=m.start()
        print(p, repr(t[p-100:p+600])[:1200])
        if p>500000:
            break
    print()

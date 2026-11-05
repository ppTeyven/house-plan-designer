import pathlib, re
t=pathlib.Path('assets/template.html').read_text(encoding='utf-8')
def show(pat, L=1200):
    for m in re.finditer(pat, t):
        p=m.start()
        print('===',pat,'at',p)
        print(t[p:p+L].replace('\n',' | ')[:3000])
        print()
        break
for pat in [r'function L\(', r'function we\(', r'function Cc\(', r'function MD\(', r'function wD\(', r'function MR', r'const L=', r'function M7\(', r'function xD\(']:
    show(pat)
print('len',len(t))

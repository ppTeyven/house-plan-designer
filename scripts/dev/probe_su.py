import pathlib,re
t=pathlib.Path('assets/template.html').read_text(encoding='utf-8')
for pat in [r'su=\[.{0,80}', r'let su[^;]{0,80}', r'const su[^;]{0,80}', r'Zh\.push[^;]{0,80}', r'for\(let s=0;s<2;s\+\+\)[^;]{0,200}', r'suWant|suCur']:
    ms=list(re.finditer(pat,t))
    print('===',pat,'n',len(ms))
    for m in ms[:4]:
        s=max(0,m.start()-250); print(t[s:m.end()+250].replace('\n',' | ')[:1600]); print('---POS',m.start())
    print()
print('LEN',len(t))

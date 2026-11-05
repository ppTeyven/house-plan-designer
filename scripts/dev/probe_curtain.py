import pathlib,re
t=pathlib.Path('assets/template.html').read_text(encoding='utf-8')
for pat in [r'case"curtain"', r'curtain.{0,30}pleat', r'Jr\(n\.id\)', r'j0\.get\(w\.id\)']:
    ms=list(re.finditer(pat,t))
    print('===',pat,'count',len(ms))
    for m in ms[:3]:
        s=max(0,m.start()-400); e=min(len(t),m.end()+800)
        print(t[s:e].replace('\n',' | ')[:2800])
        print('---POS',m.start())
    print()
print('LEN',len(t))

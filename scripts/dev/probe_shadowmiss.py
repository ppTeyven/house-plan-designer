import pathlib,re
t=pathlib.Path('assets/template.html').read_text(encoding='utf-8')
for pat in [r'castShadow=!1', r'castShadow=l', r'\.castShadow=[^,;]{0,20}']:
    ms=list(re.finditer(pat,t))
    print('===',pat,'count',len(ms))
print()
# list contexts of castShadow=!1 (explicit disables) — need to know which are glass/2D-only vs real misses
for m in list(re.finditer(r'castShadow=!1',t))[:40]:
    s=max(0,m.start()-180); e=min(len(t),m.end()+180)
    print(t[s:e].replace('\n',' | ')[:900]); print('---POS',m.start())

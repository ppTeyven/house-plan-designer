import pathlib,re
t=pathlib.Path('assets/template.html').read_text(encoding='utf-8')
# 1. shadow type switch func context
for pat in [r'.{0,400}const o=e\?Hs:xd.{0,400}', r'.{0,300}a\.shadow\.radius=e\?4.{0,300}', r'function j5\(.{0,200}', r'su\.length|su\[0\]|new ro\(.{0,80}', r'S\.exp|toneMappingExposure=']:
    ms=list(re.finditer(pat,t))
    print('===',pat[:40],'count',len(ms))
    for m in ms[:4]:
        print(t[m.start():m.end()].replace('\n',' | ')[:2500]); print('---POS',m.start())
    print()

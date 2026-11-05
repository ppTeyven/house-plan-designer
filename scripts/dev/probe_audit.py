import pathlib,re
t=pathlib.Path('assets/template.html').read_text(encoding='utf-8')
def find(pat):
    m=re.search(pat,t)
    print(pat, '=>', (m.group(0)[:500] if m else 'NOTFOUND'))
    if m: print(' POS',m.start())
find(r'jt\.toneMappingExposure=[^;]+;')
find(r'S\.envI[^;]*;')
find(r'S\.exp[^;]*;')
find(r'Tn=new Lb\([^;]+\);')
find(r'Oa=new _h\([^;]+\);')
find(r'pt\.environmentIntensity[^;]+;')
find(r'const i=new _h\(16774373[^;]+\);')
find(r'shadow\.mapSize\.set\([^;]+\);')
find(r'shadow\.bias[^;]+;')
find(r'shadow\.normalBias[^;]+;')
find(r'Xd|Hs|shadowMap\.type')
find(r'su\s*=\s*\[|su\.length|new ro\(16769976[^;]+;')
find(r'__setLT\(su')
# sliding door shadow
for pat in [r'te\.receiveShadow=!0,j\.add\(te\)', r'oe=new Me[^;]+;oe\.position[^;]+;', r'F\.add\(X\)']:
    ms=list(re.finditer(pat,t))
    print('==',pat,'n',len(ms))
    for m in ms[:3]:
        s=max(0,m.start()-200); print(t[s:m.end()+200].replace('\n',' | ')[:1200])

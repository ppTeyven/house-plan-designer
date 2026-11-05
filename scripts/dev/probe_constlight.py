import pathlib,re
t=pathlib.Path('assets/template.html').read_text(encoding='utf-8')
i=t.find('S.envI')
print(t[i-600:i+600].replace('\n',' | ')[:3000])
print('---')
i2=t.find('S.exp')
print(t[i2-600:i2+600].replace('\n',' | ')[:3000])
print('---CONST-LIGHT count', t.count('CONST-LIGHT'))
for m in re.finditer(r'CONST-LIGHT.{0,120}', t):
    s=max(0,m.start()-200); print(t[s:m.end()+200].replace('\n',' | ')[:1200])

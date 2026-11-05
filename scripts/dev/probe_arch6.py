import pathlib,re
t=pathlib.Path('assets/template.html').read_text(encoding='utf-8')
for m in re.finditer(r'userData\.role="(wallface|skirt|floor|ceil)"', t):
    p=m.start()
    print('=== ',m.group(1),p)
    print(t[max(0,p-1500):p+300].replace('\n',' | ')[-1900:])
    print()

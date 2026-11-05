import pathlib,re
t=pathlib.Path('assets/template.html').read_text(encoding='utf-8')
for name in ['function dD(','function yD(']:
    p=t.find(name)
    print('==',name,p)
    print(t[p:p+2600].replace('\n',' | '))
    print()

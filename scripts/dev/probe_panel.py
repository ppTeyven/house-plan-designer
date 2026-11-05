import pathlib
t=pathlib.Path('assets/template.html').read_text(encoding='utf-8')
for name in ['function _0(','function pn(','function Ys(','function Ae(']:
    p=t.find(name)
    print('==',name,p)
    print(t[p:p+700].replace('\n',' | '))
    print()

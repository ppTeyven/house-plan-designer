import pathlib,re
t=pathlib.Path('assets/template.html').read_text(encoding='utf-8')
for name in ['function N(','function ue(','function ft(','function mr(','function L(','function we(','function Bt(']:
    p=t.find(name)
    print('==',name,p)
    if p>=0:
        print(t[p:p+700].replace('\n',' | '))
    print()

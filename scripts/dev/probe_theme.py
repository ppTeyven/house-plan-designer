import pathlib
t=pathlib.Path('assets/template.html').read_text(encoding='utf-8')
for name in ['function VD(', 'function GD(', 'function Dv(', 'function L7(', 'function bi', 'function qo(', 'function bp(']:
    p=t.find(name)
    print('====',name,'at',p)
    print((t[p:p+2500].replace('\n',' | ')[:2800]) if p>=0 else 'NOT FOUND')
    print()

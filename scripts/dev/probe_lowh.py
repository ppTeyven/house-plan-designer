import pathlib, re
t=pathlib.Path('assets/template.html').read_text(encoding='utf-8')
for name in ['function Lo(', 'function Wh(', 'function Kv(', 'function Yo(', 'function en(', 'function NM(', 'function A7(']:
    p=t.find(name)
    print('====',name,'at',p)
    print(t[p:p+1200].replace('\n',' | ')[:1600] if p>=0 else 'NOT FOUND')
    print()

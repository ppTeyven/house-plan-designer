import pathlib
t=pathlib.Path('assets/template.html').read_text(encoding='utf-8')
for key in ['N(t,r*2,.025,.02', 'N(t,.09,.014,.05', 'N(n,t*.87,.02,.035']:
    p=t.find(key)
    print('KEY',key,p)
    print(repr(t[max(0,p-500):p+400]))
    print('======')

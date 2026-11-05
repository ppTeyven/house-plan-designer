import pathlib
t=pathlib.Path('assets/template.html').read_text(encoding='utf-8')
def show(key, L=3000):
    p=t.find(key)
    print('===',key,p)
    if p>=0:
        print(t[p:p+L].replace('\n',' | ')[:4000])
        print()
for k in ['case"sofa"', 'case"bed', 'case"diningTable"', 'case"wardrobe', 'case"chair"', 'case"armchair"', 'function ft(', 'const ft=', '=>ft(', 'function N(']:
    show(k, 2500)
print('len', len(t))

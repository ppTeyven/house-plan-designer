import pathlib
t=pathlib.Path('assets/template.html').read_text(encoding='utf-8')
def show(key, L=900):
    p=t.find(key)
    print('===',key,p)
    if p>=0:
        print(t[p:p+L].replace('\n',' | ')[:3000])
        print()
for k in ['function mD(', 'function yD(', 'function gD(', 'function f0(', 'case"vanity":mD', 'case"kitchenIsland":yD']:
    show(k)

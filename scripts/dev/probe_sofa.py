import pathlib
t=pathlib.Path('assets/template.html').read_text(encoding='utf-8')
for key in ['case"sofa"', 'case"bed"', 'case"cabinet"', 'case"diningTable"']:
    p=t.find(key)
    print('====',key,p)
    if p>=0:
        print(t[p:p+2500].replace('\n',' | ')[:3000])
        print()

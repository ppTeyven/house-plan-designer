import pathlib
t=pathlib.Path('assets/template.html').read_text(encoding='utf-8')
for key in ['case"sofa":case"armchair"','case"bed":','case"chair":{ft','case"wardrobe":','case"diningTable":N(t,i,.05','case"coffeeTable":N(t,i,.04']:
    p=t.find(key)
    print('====',key,'at',p)
    print(t[p:p+2500].replace(chr(10),' | ')[:3500])
    print()

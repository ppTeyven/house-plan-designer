import pathlib
t=pathlib.Path('assets/template.html').read_text(encoding='utf-8')
def show(key, L=700):
    p=t.find(key)
    print('===',key,p)
    if p>=0:
        print(t[p:p+L].replace('\n',' | ')[:2500])
        print()
for k in ['case"floorLamp"', 'case"chandelier"', 'case"microwave"', 'case"waterHeater"', 'case"toilet"', 'case"deskLamp"', 'case"tableLamp"', 'case"lamp"', 'case"fridge"', 'case"tvStand"', 'case"sideboard"', 'case"showerSet"', 'case"bathtub"', 'case"washer"']:
    show(k)

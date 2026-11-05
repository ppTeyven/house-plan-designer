import pathlib
t=pathlib.Path('assets/template.html').read_text(encoding='utf-8')
def show(key, L=700):
    import re
    # find all occurrences, show 3D-like (with N( / ue( nearby)
    idx=0
    n=0
    while True:
        p=t.find(key, idx)
        if p<0: break
        seg=t[p:p+L].replace('\n',' | ')[:2500]
        # only show if contains N( or ue(
        if 'N(' in seg[:700] or 'ue(' in seg[:700] or 'la(' in seg[:700]:
            print('===',key,p)
            print(seg)
            print()
            n+=1
            if n>3: break
        idx=p+1
        if idx>len(t)-10: break
for k in ['"floorLamp"', '"chandelier"', '"microwave"', '"waterHeater"', '"toilet"', '"showerSet"', '"bathtub"', '"vanity"', '"fridge"', '"tv"', '"sideboard"']:
    show('case'+k)

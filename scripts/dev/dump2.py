import pathlib
t=pathlib.Path('assets/template.html').read_text(encoding='utf-8')
keys=['case"sofa":case"armchair":case"lounge":{','case"bed":{','case"nightstand":','case"diningTable":','case"wardrobe":{']
for k in keys:
    p=t.find(k)
    print('KEY',k,'POS',p)
    if p>=0:
        print(t[p:p+2500].replace('|','/'))
        print('---END---')

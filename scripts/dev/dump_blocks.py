import pathlib
t=pathlib.Path('assets/template.html').read_text(encoding='utf-8')
def dump(key):
    p=t.find(key)
    print(key, p)
    if p>=0:
        seg=t[p:p+4000]
        pathlib.Path('C:/Temp/'+key.replace('"','').replace(':','')+'.txt').write_text(seg, encoding='utf-8')
        print(seg[:3500].replace('\n',' | '))
for k in ['case"sofa"', 'case"bed"', 'case"nightstand"', 'case"diningTable"', 'case"wardrobe"']:
    dump(k)
    print('====')

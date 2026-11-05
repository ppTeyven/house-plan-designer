import pathlib,re
t=pathlib.Path('assets/template.html').read_text(encoding='utf-8')
p=t.find('function kv(')
seg=t[p:p+200000]
def show(key, n=1400):
    ps=[m.start() for m in re.finditer(re.escape('case"'+key+'":'), seg)]
    print('===',key,ps[:3])
    for q in ps[:1]:
        print(seg[q:q+n].replace('\n',' | '))
    print()
for k in ['cabinet','counter','lCounter','uCounter','chest','dresser','sideboard','tvCabinet','fridge','floorLamp','chandelier','bathtub','washer','desk','bookshelf','shower']:
    show(k)

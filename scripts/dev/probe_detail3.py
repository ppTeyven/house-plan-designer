import pathlib,re
t=pathlib.Path('assets/template.html').read_text(encoding='utf-8')
def show(name, pat):
    ms=list(re.finditer(pat,t))
    print('===',name,'count',len(ms))
    for m in ms[:5]:
        s=max(0,m.start()-300); e=min(len(t),m.end()+300)
        print(t[s:e].replace('\n',' | ')[:2600]); print('---POS',m.start())
    print()
# curtain builder
show('curtain-builder', r'type==="curtain".{0,80}|case"curtain"|\"curtain\":|curtain.{0,40}pleat')
show('pleat-wave', r'sin\(.{0,60}pleat|wave|fold|__pl')
show('sofa-builder', r'case"sofa"|type:"sofa"|\"sofa\"')
show('bed-builder', r'case"bed"|\"bed\"')
show('cabinet-builder', r'case"cabinet"|case"wardrobe"|case"tvCabinet"')
show('table-builder', r'case"(?:diningTable|coffeeTable|desk|roundTable)"')
show('door-handle-v2', r'__rs|__pn|__fr2')
show('shadow-missing', r'\.receiveShadow=!0')

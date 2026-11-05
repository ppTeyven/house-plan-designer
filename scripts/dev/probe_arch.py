import pathlib
t=pathlib.Path('assets/template.html').read_text(encoding='utf-8')
def get(sub, ctx=1400):
    p=t.find(sub)
    print('KEY',sub[:70],'POS',p)
    if p>=0:
        print(t[p:p+ctx].replace('\n',' | ')[:1700])
        print('---')
get('function vn(')
get('function an(')
get('floorTexture')
get('function vn2(')
get('skirting')
get('baseboard')
get('__floorTex')
get('weave')

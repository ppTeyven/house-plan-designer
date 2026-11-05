import pathlib
t=pathlib.Path('assets/template.html').read_text(encoding='utf-8')
def get(sub, ctx=1200):
    p=t.find(sub)
    print('KEY',sub[:70],'POS',p)
    if p>=0:
        print(t[p:p+ctx].replace('\n',' | ')[:1600])
        print('---')
get('pleats:Array.from')
get('case"toilet":{const f=L(a,.2)')
get('case"vanity":mD')
get('case"floorLamp"')
get('function mD(')
get('function hD(')

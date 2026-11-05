import pathlib
t=pathlib.Path('assets/template.html').read_text(encoding='utf-8')
def get(key):
    p=t.find(key)
    print(key, p)
    if p<0: return
    # find end: next 'break}case' after p
    q=t.find('break}case', p)
    seg=t[p:q+5] if q>0 else t[p:p+5000]
    print('LEN', len(seg))
    print(seg[:6000])
    return seg
s=get('case"sofa":case"armchair":case"lounge":{const f=L(')
print('====SOFA3D-ABOVE====')
b=get('case"bed":{const f=L(')
print('====BED3D-ABOVE====')

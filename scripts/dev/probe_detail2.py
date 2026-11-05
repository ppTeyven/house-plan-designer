import pathlib,re
t=pathlib.Path('assets/template.html').read_text(encoding='utf-8')
def show(name, pat, w=350):
    ms=list(re.finditer(pat,t))
    print('===',name,'count',len(ms))
    for m in ms[:3]:
        s=max(0,m.start()-w); e=min(len(t),m.end()+w)
        print(t[s:e].replace('\n',' | ')[:2500])
        print('---POS',m.start()); print()
show('sill-P0', r'if\(P>0\)\{const W=new Me')
show('wallface', r'userData\.role="wallface"')
show('skirt-rail', r'userData\.role="rail"')
show('ceil-band', r'for\(const c of o\.band\)')
show('base-O', r'O\.position\.set\(D,\.03,I\)')

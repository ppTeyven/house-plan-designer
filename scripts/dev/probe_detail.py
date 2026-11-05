import pathlib,re
t=pathlib.Path('assets/template.html').read_text(encoding='utf-8')
def show(name, pat, w=400):
    ms=list(re.finditer(pat,t))
    print('===',name,'count',len(ms))
    for m in ms[:3]:
        s=max(0,m.start()-w); e=min(len(t),m.end()+w)
        print(t[s:e].replace('\n',' | ')[:2500])
        print('---POS',m.start()); print()
show('C-def', r'C=\(F,W,B,K,Q=0,j=[^)]+\)=>\{[^}]{0,300}')
show('C-use-sill', r'W\.receiveShadow=!0,f\.add\(W\)')
show('curtain-rod', r'N\(t,i\+\.1,\.03,\.03,0,o-\.03,-l\+\.02')
show('door-B', r'ce\.position\.set\(j\*\.02,U/2,F\*Q/2\),ce\.castShadow')

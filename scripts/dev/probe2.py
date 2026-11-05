import pathlib,re
t=pathlib.Path('assets/template.html').read_text(encoding='utf-8')
def show(name, pat, w=600):
    ms=list(re.finditer(pat,t))
    print('===',name,'count',len(ms))
    for m in ms[:3]:
        s=max(0,m.start()-w); e=min(len(t),m.end()+w)
        print(t[s:e].replace('\n',' | ')[:2800])
        print('---POS',m.start())
        print()
show('la-def', r'function la\(n,e,t,i,s,o\)')
show('door-leaf', r'ce=new Me\(new ot\(\.04,U')
show('win-glass', r'te=new Me\(new ot\(K,G')
show('wall-base', r'userData\.role="rail"')
show('sun-block', r'Tn=new Lb\(.*?pt\.add\(Tn\)')
show('hemi-fill', r'const S = \{ lock')
show('grade-block', r'GRADELUTZ|G5=\{uniforms')

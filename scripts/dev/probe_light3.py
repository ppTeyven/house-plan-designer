import pathlib,re
t=pathlib.Path('assets/template.html').read_text(encoding='utf-8')
def show(name, pat, w=700):
    ms=list(re.finditer(pat,t))
    print('===',name,'count',len(ms))
    for m in ms[:4]:
        s=max(0,m.start()-w); e=min(len(t),m.end()+w)
        print(t[s:e].replace('\n',' | ')[:3200])
        print('---POS',m.start()); print()
show('Ai-assign', r'Ai\.hemi\s*=')
show('Ai-fill-assign', r'Ai\.fill\s*=')
show('Ai-env-assign', r'Ai\.env\s*=')
show('ax-def', r'function ax\(\)')
show('S-hemi', r'S\.hemi\s*=')
show('S-fill', r'S\.fill\s*=')
show('S-envI', r'S\.envI\s*=')
show('S-exp', r'S\.exp\s*=')

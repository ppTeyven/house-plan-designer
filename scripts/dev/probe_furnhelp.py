import pathlib,re
t=pathlib.Path('assets/template.html').read_text(encoding='utf-8')
def show(name, pat):
    ms=list(re.finditer(pat,t))
    print('===',name,'count',len(ms))
    for m in ms[:3]:
        s=max(0,m.start()-300); e=min(len(t),m.end()+500)
        print(t[s:e].replace('\n',' | ')[:3000]); print('---POS',m.start())
    print()
show('helper-ft', r'function ft\(.{0,160}')
show('helper-A7', r'function A7\(.{0,400}')
show('helper-E7', r'function E7\(.{0,300}')
show('helper-dD', r'function dD\(.{0,300}')
show('sliding-glass', r'te=new Me\(new ot\(K,G-\.004,\.01\),_s\(\)\)[^;]+;[^;]+;')
show('pocket-case', r'else\{const W=new ht,B=')

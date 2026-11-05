import pathlib,re
t=pathlib.Path('assets/template.html').read_text(encoding='utf-8')
def show(name, pat, ctx=350):
    ms=list(re.finditer(pat,t))
    print('===',name,'count',len(ms))
    for m in ms[:4]:
        s=max(0,m.start()-ctx); e=min(len(t),m.end()+ctx)
        print(t[s:e].replace('\n',' | ')[:3000]); print('---POS',m.start())
    print()
# helpers
show('helper-N', r'function N\(.{0,120}')
show('helper-la', r'function la\(.{0,120}')
show('helper-ue', r'function ue\(.{0,120}')
show('helper-L', r'function L\(.{0,120}')
show('tone-F4', r'F4\s*=\s*[^,;]{0,60}|toneMapping=F4|F4,')
show('exp-S', r'S\.envI|S\.exp|toneMappingExposure')
show('env-set', r'pt\.environment[^;]{0,120}|environmentIntensity[^;]{0,80}')
# furniture 3D dispatch around curtain
pos=t.find('case"curtain":{const f=n.key==="sheer"')
print('curtain pos',pos)
print(t[pos-2000:pos+3000].replace('\n',' | ')[:6000])

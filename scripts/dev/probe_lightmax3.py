import pathlib,re
t=pathlib.Path('assets/template.html').read_text(encoding='utf-8')
def show(name, pat):
    ms=list(re.finditer(pat,t))
    print('===',name,'count',len(ms))
    for m in ms[:8]:
        s=max(0,m.start()-260); e=min(len(t),m.end()+260)
        print(t[s:e].replace('\n',' | ')[:2400]); print('---POS',m.start())
    print()
show('renderer', r'new (WebGLRenderer|kd)[^;]{0,220}')
show('tone-exp', r'toneMapping(Exposure)?[^;]{0,120}|outputColorSpace[^;]{0,80}')
show('shadow-type', r'shadowMap\.(type|enabled)[^;]{0,80}')
show('phys-light', r'useLegacyLights|physicallyCorrectLights')
show('door-leaf', r'te\.add\(ce\)|ce\.position\.set\(j\*\.02')
show('curtain-mesh', r'curtain|Curtain|__pleat|o-\.03')
show('furn-groups', r'function [A-Za-z0-9$_]{1,4}\([^)]*\)\{[^|]{0,80}?(?:sofa|bed|cabinet|table|chair)')

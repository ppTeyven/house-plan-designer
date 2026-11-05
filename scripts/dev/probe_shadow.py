import pathlib, re
t = pathlib.Path('assets/template.html').read_text(encoding='utf-8')
def show(name, pat, w=700):
    ms = list(re.finditer(pat, t))
    print('===', name, 'count', len(ms))
    for m in ms[:4]:
        s = max(0, m.start()-w)
        e = min(len(t), m.end()+w)
        print(t[s:e].replace('\n',' | ')[:3000])
        print('---POS', m.start())
        print()
show('curtain-case', r'case"curtain"')
show('window-builder', r'function [A-Za-z0-9$_]{1,8}\(n,e,t,i,s,o,a\)\{[^}]{0,200}window')
show('la-helper', r'function la\(')
show('ue-helper', r'function ue\(')
show('N-helper', r'function N\(')

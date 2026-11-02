t = open('assets/template.html', encoding='utf-8').read()
import re
def show(tag, pat, pre=200, ln=1800):
    i = t.find(pat)
    print('###', tag, 'idx=', i)
    if i < 0:
        print('NOT FOUND'); print(); return
    print(t[max(0,i-pre):i+ln].replace('\n',' ')[:2600]); print()
show('qR-def', 'const qR', 0, 900)
show('Zh-use', 'Zh.push', 300, 900)
show('Zh-decl', 'Zh=', 0, 300)
show('hn-def', 'function hn(', 0, 800)
show('qd-def', 'function qd(', 0, 600)
show('Ga-def', 'function Ga(', 0, 600)
show('KB-rest', 'ts.particles.visible', 0, 1500)
show('UB-def', 'UB=', 0, 400)
show('Ps-def', 'Ps=', 0, 400)
show('lz-def', 'function lz(', 0, 1200)
show('dollar-d-add', '$d.add', 0, 300)
show('modeFade-css', '#modeFade', 0, 600)
show('smart-ui-css', '.smart-ui', 0, 500)

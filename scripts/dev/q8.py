t = open('assets/template.html', encoding='utf-8').read()
import re
def find_all(pat):
    return [m.start() for m in re.finditer(re.escape(pat), t)]
for pat in ['zB(', 'setView', 'smartBtn', 'id="smart', 'smExit', '"3d"', "'3d'", 'function Ua(', 'bw(', 'bw=', 'Xc()', 're.active&&Ns', 'function Ns(', '__walkPre(', '__walkFinish(', 'Oa.position', 'Oa.intensity', 'Oa.target', 'function JL(', 's0.p+(e.to.p', 'fromT.clone().lerp', 'function wi(', 'L1(Se', 'L1(fit', 'P1(fit', 'P1(Se', 'Hv(0,0)', 'ao(uo())', 'wi(uo()']:
    print(pat, '->', find_all(pat)[:8])

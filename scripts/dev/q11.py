t = open('assets/template.html', encoding='utf-8').read()
import re
def find(pat):
    return [m.start() for m in re.finditer(re.escape(pat), t)][:6]
for pat in ['Zh=', 'Zh.push', 'function Al(', 'Al=', 'const qR', 'qR=', '=qR', 'function KB(', 'function Qc(', 'function FB(', 'function _w(', 'function qd(', 'function Ga(', 'function Zr(', 'Ps=', 'Ps.on', 'function hn(', 'function H1', 'H1=', 'function lz(', '$d.add', 'function x4(', 'lt.tab', 'UB=', 'function Xi(', 'Cn.classList', 'smPins', 'function Qr(', 'robotFor', 'ad.innerHTML', 'function xw(']:
    print(pat, '->', find(pat))

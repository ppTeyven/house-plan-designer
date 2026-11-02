# -*- coding: utf-8 -*-
t = open('assets/template.html', encoding='utf-8').read()
import re
for pat in ['ts=', 'let ts', 'const ts', 'ts={', 'ts =', 'flows=', 'yc=', 'let yc', 'function Qr(', 'Qr=', 'PB=', 'function PB(', 'b0=', 'xi=', 'j0=', 'nf=', 'v4=', 'function fa(', 'fa=', 'i5=', 'function ww(', 'ww=', 'function WB(', 'WB=']:
    idxs = [m.start() for m in re.finditer(re.escape(pat), t)][:4]
    print(pat, '->', idxs)

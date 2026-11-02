# -*- coding: utf-8 -*-
t = open('assets/template.html', encoding='utf-8').read()
import re
for pat in ['let ay', 'ay=', 'function OB(', 'OB=', 'function JB(', 'const kr', 'kr=', 'oy=', 'let oy', 'function NN(', 'function EP(', 'fn=', 'ih=', 'let ih', 'ih =']:
    idxs = [m.start() for m in re.finditer(re.escape(pat), t)][:3]
    print(pat, '->', idxs)
for pat in ['function OB(', 'function JB(', 'let ay', 'const kr=', 'kr=Fi(40)', 'let oy']:
    i = t.find(pat)
    if i >= 0:
        print('----', pat, i)
        print(t[max(0,i-100):i+1200].replace('\n',' ')[:1400])
        print()

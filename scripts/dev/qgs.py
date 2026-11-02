# -*- coding: utf-8 -*-
t = open('assets/template.html', encoding='utf-8').read()
import re
for pat in ['function gs(', 'gs=', 'function Is(', 'Is=', 'function Yh(', 'function Pp(', 'Pp=']:
    idxs = [m.start() for m in re.finditer(re.escape(pat), t)][:4]
    print(pat, '->', idxs)
for pat in ['function gs(', 'function Is(']:
    i = t.find(pat)
    if i>=0:
        print('----', pat, i)
        print(t[i:i+1800].replace('\n',' ')[:1800])
        print()

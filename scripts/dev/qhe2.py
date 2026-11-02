# -*- coding: utf-8 -*-
t = open('assets/template.html', encoding='utf-8').read()
import re
for pat in ['he=', 'function he(', 'const he', 'let he', ' he=', '(he=', ',he=']:
    idxs=[m.start() for m in re.finditer(re.escape(pat), t)][:4]
    print(pat,'->',idxs)
for pat in ['function he(','he=']:
    i=t.find(pat)
    if i>=0:
        print('---',pat,i)
        print(t[max(0,i-20):i+500].replace('\n',' ')[:600])

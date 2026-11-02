# -*- coding: utf-8 -*-
t = open('assets/template.html', encoding='utf-8').read()
import re
for pat in ['qR=', 'qR =', 'const qR', 'let qR', 'var qR', 'function qR', 'class qR', 'qR(']:
    idxs = [m.start() for m in re.finditer(re.escape(pat), t)][:6]
    print(pat, '->', idxs)
i = t.find('Zh=[]')
print('Zh decl ctx:', t[max(0,i-200):i+300].replace('\n',' ')[:600])

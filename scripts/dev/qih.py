# -*- coding: utf-8 -*-
t = open('assets/template.html', encoding='utf-8').read()
for pat in ['let ih', 'function Fi(', 'Fi=', 'function Xo(', 'Xo=', 'function gdApply', 'gdApply=', 'function OB(']:
    i = t.find(pat)
    print('====', pat, i)
    if i >= 0:
        print(t[max(0,i-50):i+900].replace('\n',' ')[:1000])
    print()

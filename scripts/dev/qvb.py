# -*- coding: utf-8 -*-
t = open('assets/template.html', encoding='utf-8').read()
for pat in ['D0=', 'l0=', 'function Ye(', 'Ye=', 'function VB(', 'function GB(', 'GB=']:
    i = t.find(pat)
    print('====', pat, i)
    if i >= 0:
        print(t[max(0,i-80):i+1400].replace('\n',' ')[:1500])
    print()

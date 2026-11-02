# -*- coding: utf-8 -*-
t = open('assets/template.html', encoding='utf-8').read()
i = t.find('class qR')
print('qR class idx', i)
print(t[max(0,i-200):i+1200].replace('\n',' ')[:1500])
print()
for pat in ['function iP(', 'iP=', 'function Yh(', 'Yh=', 'function fI(', 'fI=', 'function hx(', 'function Ir(', 'Ir=']:
    j = t.find(pat)
    print(pat, j)
    if j>=0:
        print(t[max(0,j-60):j+700].replace('\n',' ')[:800])
        print()

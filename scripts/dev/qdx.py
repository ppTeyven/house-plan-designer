# -*- coding: utf-8 -*-
t = open('assets/template.html', encoding='utf-8').read()
i = t.find('function dx(n){')
print('dx idx', i)
open('scripts/dev/dump_dx.txt','w',encoding='utf-8').write(t[i:i+2500])
print(t[i:i+2500].replace('\n',' ')[:2500])
print()
j = t.find('let ih=0;')
print(t[max(0,j-400):j+600].replace('\n',' ')[:1100])

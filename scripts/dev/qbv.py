# -*- coding: utf-8 -*-
t = open('assets/template.html', encoding='utf-8').read()
i = t.find('function Bv(n,e){')
print('Bv idx', i)
open('scripts/dev/dump_Bv.txt','w',encoding='utf-8').write(t[i:i+4500])
print(t[i:i+4500].replace('\n',' ')[:4500])

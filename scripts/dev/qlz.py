# -*- coding: utf-8 -*-
t = open('assets/template.html', encoding='utf-8').read()
i = t.find('function lz(n,e){')
print('lz idx', i)
open('scripts/dev/dump_lz.txt', 'w', encoding='utf-8').write(t[i:i+3000])
print(t[i:i+3000].replace('\n', ' ')[:3000])

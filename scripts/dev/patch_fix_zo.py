# -*- coding: utf-8 -*-
import sys
p = 'assets/template.html'
t = open(p, encoding='utf-8').read()
fixes = [
    ('const ZO=n=>1-Math.pow(1-n,3);', 'const __ZOease=n=>1-Math.pow(1-n,3);'),
    ('try{skyFade(1)}catch(e){}})},ZO)}', 'try{skyFade(1)}catch(e){}})},__ZOease)}'),
    ('wi({...i,r:i.r*.8},1200,null,ZO)', 'wi({...i,r:i.r*.8},1200,null,__ZOease)'),
]
fails = []
for old, new in fixes:
    c = t.count(old)
    if c != 1:
        fails.append((old, c))
        continue
    t = t.replace(old, new)
if fails:
    print('FIX FAIL:', fails)
    sys.exit(1)
open(p, 'w', encoding='utf-8').write(t)
print('fix3 OK')

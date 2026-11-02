# -*- coding: utf-8 -*-
import sys
p = 'assets/template.html'
t = open(p, encoding='utf-8').read()
old = '}catch(_){try{wi(Hv(0,0),1100)}catch(_){}})(),ts.particles'
new = '}catch(_){try{wi(Hv(0,0),1100)}catch(_){}}})(),ts.particles'
c = t.count(old)
print('count', c)
if c != 1:
    sys.exit(1)
t = t.replace(old, new)
open(p, 'w', encoding='utf-8').write(t)
print('brace fix OK')

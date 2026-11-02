# -*- coding: utf-8 -*-
import sys
p = 'assets/template.html'
t = open(p, encoding='utf-8').read()
old = 'try{skyFade(1)}catch(e){}})})},ZO)}'
new = 'try{skyFade(1)}catch(e){}})},ZO)}'
c = t.count(old)
print('count', c)
if c != 1:
    # show surrounding
    i = t.find('try{skyFade(1)}catch(e){}')
    print(repr(t[i-50:i+80]))
    sys.exit(1)
t = t.replace(old, new)
open(p, 'w', encoding='utf-8').write(t)
print('fix2 OK')

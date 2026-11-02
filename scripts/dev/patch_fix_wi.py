# -*- coding: utf-8 -*-
import sys
p = 'assets/template.html'
t = open(p, encoding='utf-8').read()
fixes = [
    ('function wi(n,e,t,i){const i=', 'function wi(n,e,t,f){const i='),
    ('done:t,ease:i},Tt.enabled', 'done:t,ease:f},Tt.enabled'),
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
print('fix OK')

# -*- coding: utf-8 -*-
t=open('assets/template.html',encoding='utf-8').read()
def dump(pat, ln=4000):
    i=t.find(pat)
    if i<0:
        print(pat,'NOT FOUND'); return
    print('===='+pat+'==== LN '+str(i))
    print(t[i:i+ln])
    print('\n')
for p in ['async function Ua(','function Vp(','function Ns(','async function rh(','function wi(','function __walkPre','function __fade(','function ja(']:
    dump(p, 3500)

# -*- coding: utf-8 -*-
p = 'assets/template.html'
t = open(p, encoding='utf-8').read()
old = 'i!==lt.sig&&(lt.sig=i,try{lt.devs=VB()}'
print('count old', t.count(old))
assert t.count(old) == 1
# find full span: from old to ,ad.innerHTML
i = t.find(old)
# locate the segment to replace: up to ',ad.innerHTML=""'
tail_marker = ',ad.innerHTML=""'
j = t.find(tail_marker, i)
assert j > i
seg = t[i:j]
print('SEG len', len(seg))
print(seg[:2000])
new_seg = 'i!==lt.sig&&(lt.sig=i,(function(){try{lt.devs=VB()}catch(_e){try{window.__smartErr="VB:"+String((_e&&_e.stack)||_e).slice(0,800)}catch(_){}try{lt.devs=[]}catch(_){}})()'
t = t[:i] + new_seg + t[j:]
open(p, 'w', encoding='utf-8').write(t)
print('fixed VB guard')

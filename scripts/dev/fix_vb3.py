# -*- coding: utf-8 -*-
p = 'assets/template.html'
t = open(p, encoding='utf-8').read()
marker = 'i!==lt.sig&&(lt.sig=i,(function(){try{lt.devs=VB()}'
assert t.count(marker) == 1, t.count(marker)
i = t.find(marker)
# find end of the &&(...) expression: it ends with '))}const Gl'
tail = '))}const Gl'
j = t.find(tail, i)
assert j > i
seg = t[i:j]
print('SEG len', len(seg))
# Build replacement: if-block version
# seg = i!==lt.sig&&(lt.sig=i,IIFE(),ad.innerHTML="",!lt.all&&FOREACH)
# split at ',ad.innerHTML=""'
part_marker = ',ad.innerHTML=""'
k = seg.find(part_marker)
assert k > 0
head_part = seg[:k]  # i!==lt.sig&&(lt.sig=i,(function...})()
rest = seg[k:]  # ,ad.innerHTML="",!lt.all&&...forEach((s,o)=>{...})
print('HEAD tail:', head_part[-120:])
print('REST head:', rest[:120])
print('REST tail:', rest[-200:])
# new code:
new_code = ('if(i!==lt.sig){lt.sig=i;(function(){try{lt.devs=VB()}catch(_e){try{window.__smartErr="VB:"+String((_e&&_e.stack)||_e).slice(0,800)}catch(_){}try{lt.devs=[]}catch(_){}}})();ad.innerHTML="";'
            + rest[len(part_marker)+1:]  # skip leading comma -> starts with !lt.all&&...
            + '}')
print('NEW tail:', new_code[-200:])
t = t[:i] + new_code + t[j:]
open(p, 'w', encoding='utf-8').write(t)
print('fixed VB to if-block OK')

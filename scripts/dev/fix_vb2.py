# -*- coding: utf-8 -*-
p = 'assets/template.html'
t = open(p, encoding='utf-8').read()
old = '(lt.sig=i,(function(){try{lt.devs=VB()}'
assert t.count(old) == 1, t.count(old)
i = t.find(old)
# find the matching end: search for ")))}const Gl" after i
tail = '))}const Gl'
j = t.find(tail, i)
assert j > i, 'tail not found'
seg = t[i:j]
print('SEG tail:', seg[-300:])
new_seg = ('{lt.sig=i;(function(){try{lt.devs=VB()}catch(_e){try{window.__smartErr="VB:"+String((_e&&_e.stack)||_e).slice(0,800)}catch(_){}try{lt.devs=[]}catch(_){}})();ad.innerHTML="";if(!lt.all)lt.devs.filter(s=>GB(s,lt.tab)).forEach((s,o)=>{const a=document.createElement("button");a.className=`sm-pin k-${s.kind}`,a.dataset.id=s.id,a.title=s.name,a.innerHTML=bc[s.kind==="door"&&s.entry?"lock":s.kind],a.style.transitionDelay=`${Math.min(o*25,400)}ms`,a.onpointerdown=r=>r.stopPropagation(),a.onclick=()=>jB(s),ad.appendChild(a),requestAnimationFrame(()=>requestAnimationFrame(()=>a.classList.add("in")))})}')
t = t[:i] + new_seg + t[j:]
# now fix the head: 'i!==lt.sig&&(' -> 'if(i!==lt.sig)'
head_old = 'i!==lt.sig&&(' + new_seg[:10]
# simpler: replace 'i!==lt.sig&&(lt.sig=i;' with 'if(i!==lt.sig)'
h = t.find('i!==lt.sig&&(lt.sig=i;')
print('head count', t.count('i!==lt.sig&&(lt.sig=i;'))
assert t.count('i!==lt.sig&&(lt.sig=i;') == 1
t = t.replace('i!==lt.sig&&(lt.sig=i;', 'if(i!==lt.sig){lt.sig=i;')
open(p, 'w', encoding='utf-8').write(t)
print('fixed VB to if-block')

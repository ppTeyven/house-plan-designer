# -*- coding: utf-8 -*-
import re
p = 'assets/template.html'
t = open(p, encoding='utf-8').read()
start_marker = 'function $B(){const n=E.plan'
i = t.find(start_marker)
assert i > 0, 'head not found'
end_marker = 'const Gl=new z'
j = t.find(end_marker, i)
assert j > i, 'tail not found'
seg = t[i:j]
print('OLD seg len', len(seg))
print('OLD tail:', seg[-150:])
new_fn = ('function $B(){const n=E.plan,e=(s,o)=>s*31+Math.round(o)|0;let t=0;'
 'for(const s of n.elec)t=e(e(t,s.x),s.y+s.kind.length);'
 'for(const s of n.furniture)t=e(e(e(t,s.x),s.y),s.type.length+s.rot);'
 'for(const s of n.openings)t=e(e(t,s.pos),s.width+s.type.length);'
 'for(const s of E.rooms.regions)for(const o of s.labels)t=e(e(t,o.x+o.name.length),o.y);'
 'const i=[lt.tab,lt.all,Z.cur,n.furniture.length,n.elec.length,n.openings.length,n.walls.length,t].join("|");'
 'if(i!==lt.sig){lt.sig=i;(function(){try{lt.devs=VB()}catch(_e){try{window.__smartErr="VB:"+String((_e&&_e.stack)||_e).slice(0,800)}catch(_){}try{lt.devs=[]}catch(_){}}})();ad.innerHTML="";'
 'if(!lt.all){lt.devs.filter(s=>GB(s,lt.tab)).forEach((s,o)=>{const a=document.createElement("button");a.className=`sm-pin k-${s.kind}`,a.dataset.id=s.id,a.title=s.name,a.innerHTML=bc[s.kind==="door"&&s.entry?"lock":s.kind],a.style.transitionDelay=`${Math.min(o*25,400)}ms`,a.onpointerdown=r=>r.stopPropagation(),a.onclick=()=>jB(s),ad.appendChild(a),requestAnimationFrame(()=>requestAnimationFrame(()=>a.classList.add("in")))})}}}')
t = t[:i] + new_fn + t[j:]
open(p, 'w', encoding='utf-8').write(t)
print('rewrote $B OK, new len', len(new_fn))

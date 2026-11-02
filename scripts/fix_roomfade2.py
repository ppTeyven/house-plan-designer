import pathlib
p = pathlib.Path('assets/template.html').read_text(encoding='utf-8')
orig = len(p)
miss = []
# 1) fix extra brace: '}catch(_){}}function q5(n){' -> '}catch(_){}function q5(n){'
old_brace = '}catch(_){}}function q5(n){'
if old_brace in p:
    p = p.replace(old_brace, '}catch(_){}function q5(n){')
else:
    miss.append('brace')
# 2) su intensity + pooled original -> smooth via __setLT, fade unused su
old_su2 = ('.slice(0,su.length).forEach((c,u)=>{const f=su[u];'
 'if(f.userData.__pt)f.userData.__pt.copy(c.pos);else{f.userData.__pt=c.pos.clone();f.position.copy(c.pos)}'
 ',f.color.copy(c.light.color),f.intensity=c.base*c.lv,')
new_su2 = ('.slice(0,su.length).forEach((c,u)=>{const f=su[u];'
 'if(f.userData.__pt)f.userData.__pt.copy(c.pos);else{f.userData.__pt=c.pos.clone();f.position.copy(c.pos)}'
 ',f.color.copy(c.light.color),__setLT(f,c.base*c.lv),')
if old_su2 not in p:
    miss.append('su2')
else:
    p = p.replace(old_su2, new_su2)
old_zero = 'c.light.intensity=0,f.shadow.needsUpdate=!0})}'
new_zero = '__setLT(c.light,0),f.shadow.needsUpdate=!0});const __usedSU=new Set(n.filter(c=>c.lv>0&&c.r&&t.includes(c.r)).sort((c,u)=>c.pos.distanceTo(l)-u.pos.distanceTo(l)).slice(0,su.length).map(c=>su[n.filter(c=>c.lv>0&&c.r&&t.includes(c.r)).sort((c,u)=>c.pos.distanceTo(l)-u.pos.distanceTo(l)).slice(0,su.length).indexOf(c)]));}'
# Simpler: after forEach, fade unused su to 0. Build without recompute mess:
old_tail = '__setLT(c.light,0),f.shadow.needsUpdate=!0})}'
new_tail = ('__setLT(c.light,0),f.shadow.needsUpdate=!0});'
 'try{const _pl=n.filter(c=>c.lv>0&&c.r&&t.includes(c.r)).sort((c,u)=>c.pos.distanceTo(l)-u.pos.distanceTo(l)).slice(0,su.length);'
 'const _set=new Set();for(let _i=0;_i<_pl.length;_i++)_set.add(su[_i]);'
 'for(const _f of su)if(!_set.has(_f))__setLT(_f,0);}catch(_){}}')
if old_tail not in p:
    miss.append('tail')
else:
    p = p.replace(old_tail, new_tail)
pathlib.Path('assets/template.html').write_text(p, encoding='utf-8')
print('miss:', miss)
print('len', orig, '->', len(p))
i = p.find('const __LT=new Map')
print(p[i-100:i+1400].replace('\n', ' | ')[:1600])

import pathlib
p = pathlib.Path('assets/template.html').read_text(encoding='utf-8')
orig = len(p)
miss = []
old = '__setLT(f,c.base*c.lv),f.distance=c.light.distance||7,f.decay=c.light.decay??1.6,c.light.intensity=0,f.shadow.needsUpdate=!0})}'
new = ('__setLT(f,c.base*c.lv),f.distance=c.light.distance||7,f.decay=c.light.decay??1.6,__setLT(c.light,0),f.shadow.needsUpdate=!0});'
 'try{var _pl=n.filter(c=>c.lv>0&&c.r&&t.includes(c.r)).sort((c,u)=>c.pos.distanceTo(l)-u.pos.distanceTo(l)).slice(0,su.length);'
 'var _set=new Set();for(var _i=0;_i<_pl.length;_i++)_set.add(su[_i]);'
 'for(var _j=0;_j<su.length;_j++)if(!_set.has(su[_j]))__setLT(su[_j],0);}catch(_){}}')
if old not in p:
    miss.append('su-tail')
else:
    p = p.replace(old, new)
pathlib.Path('assets/template.html').write_text(p, encoding='utf-8')
print('miss:', miss)
print('len', orig, '->', len(p))
i = p.find('var _set=new Set')
print(p[i-300:i+500].replace('\n', ' | ')[:900])

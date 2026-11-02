import pathlib
p = pathlib.Path('assets/template.html').read_text(encoding='utf-8')
orig = len(p)
miss = []
reps = [
 ('h.intensity=u*(1.5+5.5*i)}),a.length>0}',
  '__setLT(h,u*(1.5+5.5*i))}),a.length>0}'),
 ('su[0].intensity=.55;su[0].distance=16;',
  '__setLT(su[0],.55);su[0].distance=16;'),
 ('for(let _k=1;_k<su.length;_k++){su[_k].intensity=0}',
  'for(let _k=1;_k<su.length;_k++){__setLT(su[_k],0)}'),
 ('F5.forEach((s,o)=>{const a=t[o];if(!a){s.intensity=0;return}',
  'F5.forEach((s,o)=>{const a=t[o];if(!a){__setLT(s,0);return}'),
 ('s.intensity=a.l.intensity,s.distance=a.l.distance,s.decay=a.l.decay})',
  '__setLT(s,a.l.intensity),s.distance=a.l.distance,s.decay=a.l.decay})'),
 ('Iv.forEach((s,o)=>{const a=i[o];if(!a){s.intensity=0;return}',
  'Iv.forEach((s,o)=>{const a=i[o];if(!a){__setLT(s,0);return}'),
 ('s.intensity=a.l.intensity,s.distance=a.l.distance,s.decay=a.l.decay,s.angle=a.l.angle',
  '__setLT(s,a.l.intensity),s.distance=a.l.distance,s.decay=a.l.decay,s.angle=a.l.angle'),
]
for a, b in reps:
    if a not in p:
        miss.append(a[:60])
    else:
        p = p.replace(a, b)
pathlib.Path('assets/template.html').write_text(p, encoding='utf-8')
print('miss:', miss)
print('len', orig, '->', len(p))

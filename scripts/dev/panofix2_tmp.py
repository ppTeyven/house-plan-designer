p = 'assets/template.html'
t = open(p, encoding='utf-8').read()
old = '};he("#panoBtn").onclick=async()=>{if(!m0)return;'
assert t.count(old) == 1, t.count(old)
new = '};try{const _pb=he("#panoBtn");if(_pb)_pb.onclick=async()=>{if(!m0)return;'
t = t.replace(old, new)
old2 = 'OU(e,"720\xb0 \u5168\u666f\u9884\u89c8",()=>vi(n,`${E.plan.name}-\u5168\u666f.jpg`))};he("#leftToggle")'
assert t.count(old2) == 1, ('tail', t.count(old2))
new2 = 'OU(e,"720\xb0 \u5168\u666f\u9884\u89c8",()=>vi(n,`${E.plan.name}-\u5168\u666f.jpg`))}}catch(_){}he("#leftToggle")'
t = t.replace(old2, new2)
open(p, 'w', encoding='utf-8').write(t)
print('pano guard fixed')

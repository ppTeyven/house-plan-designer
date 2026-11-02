p = 'assets/template.html'
t = open(p, encoding='utf-8').read()
bad = 't>=1&&(Bi=null,Tt.enabled=!re.active,try{Ir()}catch(_){},Tt.update(),(a=e.done)==null||a.call(e))'
assert t.count(bad) == 1, t.count(bad)
good = 't>=1&&(Bi=null,Tt.enabled=!re.active,(function(){try{Ir()}catch(_){}})(),Tt.update(),(a=e.done)==null||a.call(e))'
t = t.replace(bad, good)
open(p, 'w', encoding='utf-8').write(t)
print('fixed B2')

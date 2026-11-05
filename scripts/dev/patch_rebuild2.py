import pathlib
p = pathlib.Path('assets/template.html')
t = p.read_text(encoding='utf-8')
reps = []
# R3: dining/coffee/desk — under-top apron inset (mortise-tenon shoulder look, no outer size change)
reps.append((
'else mr(n,t,i,s,o-h,e.type==="coffeeTable"?.06:.08);return N(n,i,h,s,0,o-h,0,d)',
'else mr(n,t,i,s,o-h,e.type==="coffeeTable"?.06:.08);N(n,i-.16,.06,s-.16,0,o-h-.09,0,Bt(t,-.06));return N(n,i,h,s,0,o-h,0,d)'
))
# R4: wardrobe — recessed vertical finger groove shadow per door (25-28mm door logic, inset only)
reps.append((
'const y=-a+d*(g+(g%2?.1:.9));N(n,.012,t.legs==="gold"?.5:.3,.02,y,o*.45,r+.01,Mn(t),!1)}',
'const y=-a+d*(g+(g%2?.1:.9));N(n,.012,t.legs==="gold"?.5:.3,.02,y,o*.45,r+.01,Mn(t),!1),N(n,.014,o-p-.06,.01,m+d/2-.012,p+.04,r+.002,L(we(l,-.3),.8),!1)}'
))
# R5: chair — seat edge welt cord (2-4mm piping logic, inset)
reps.append((
'ft(n,i-.02,.06,s-.05,0,h,.02,f,.02,{puff:[0,.008,0]});const d=o-h;',
'ft(n,i-.02,.06,s-.05,0,h,.02,f,.02,{puff:[0,.008,0]}),N(n,i-.05,.014,.014,0,h+.045,.02,L(we(l,-.15),.8));const d=o-h;'
))
for old, new in reps:
    c = t.count(old)
    print('CHECK', c, old[:90])
    assert c == 1, old[:160]
    t = t.replace(old, new)
p.write_text(t, encoding='utf-8')
print('OK rebuild2', len(reps))

import pathlib
p = pathlib.Path('assets/template.html')
t = p.read_text(encoding='utf-8')
reps = []
# 1. la helper: add receiveShadow (small cylinders, rails, handles) - safe, was cast only
reps.append((
"function la(n,e,t,i,s,o){const a=new Me(new Go(e,18,14),Cc(o));return a.position.set(t,i,s),a.castShadow=!0,n.add(a),a}",
"function la(n,e,t,i,s,o){const a=new Me(new Go(e,18,14),Cc(o));return a.position.set(t,i,s),a.castShadow=!0,a.receiveShadow=!0,n.add(a),a}"
))
# 2. sliding door frames: add receiveShadow alongside castShadow
reps.append((
"const oe=new Me(new ot(X,ne,.035),i);oe.position.set(ce,ie+ne/2,B),oe.castShadow=!0,j.add(oe)",
"const oe=new Me(new ot(X,ne,.035),i);oe.position.set(ce,ie+ne/2,B),oe.castShadow=!0,oe.receiveShadow=!0,j.add(oe)"
))
# 3. wall rails H/O: add shadows (P already has cast; add receive to P, cast+receive to H/O)
reps.append((
"H.position.set(D,.53,I),H.rotation.y=k,H.userData.role=\"rail\",an.add(H);const P=new Me(new ot(R,.05,.06),a);P.position.set(D,1.05,I),P.rotation.y=k,P.castShadow=!0,P.userData.role=\"rail\",an.add(P);const O=new Me(new ot(R,.06,.06),a);O.position.set(D,.03,I),O.rotation.y=k,O.userData.role=\"rail\",an.add(O)",
"H.position.set(D,.53,I),H.rotation.y=k,H.castShadow=!0,H.receiveShadow=!0,H.userData.role=\"rail\",an.add(H);const P=new Me(new ot(R,.05,.06),a);P.position.set(D,1.05,I),P.rotation.y=k,P.castShadow=!0,P.receiveShadow=!0,P.userData.role=\"rail\",an.add(P);const O=new Me(new ot(R,.06,.06),a);O.position.set(D,.03,I),O.rotation.y=k,O.castShadow=!0,O.receiveShadow=!0,O.userData.role=\"rail\",an.add(O)"
))
for old, new in reps:
    c = t.count(old)
    print('CHECK', c, old[:80])
    assert c >= 1, old[:120]
    t = t.replace(old, new)
p.write_text(t, encoding='utf-8')
print('OK shadow patch', len(reps))

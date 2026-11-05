import pathlib
p = pathlib.Path('assets/template.html')
t = p.read_text(encoding='utf-8')
reps = []
# W1: window sill nosing + apron (physical step, both cast+receive)
reps.append((
'if(P>0){const W=new Me(new ot(O+.06,.03,u+.08),L("#e8e4dc",.5));W.position.set(V,Y,0),W.receiveShadow=!0,f.add(W)}',
'if(P>0){const W=new Me(new ot(O+.06,.03,u+.08),L("#e8e4dc",.5));W.position.set(V,Y,0),W.castShadow=!0,W.receiveShadow=!0,f.add(W);const __sn=new Me(new ot(O+.09,.014,u+.11),L("#e8e4dc",.5));__sn.position.set(V,Y-.022,0),__sn.castShadow=!0,__sn.receiveShadow=!0,f.add(__sn);const __sa=new Me(new ot(O+.02,.05,.015),L("#e8e4dc",.5));__sa.position.set(V,Y-.055,F),__sa.castShadow=!0,__sa.receiveShadow=!0,f.add(__sa)}'
))
# W2: baseboard top lip (physical chamfer cap over O, follows same rotation)
reps.append((
'const O=new Me(new ot(R,.06,.06),a);O.position.set(D,.03,I),O.rotation.y=k,O.castShadow=!0,O.receiveShadow=!0,O.userData.role="rail",an.add(O)',
'const O=new Me(new ot(R,.06,.06),a);O.position.set(D,.03,I),O.rotation.y=k,O.castShadow=!0,O.receiveShadow=!0,O.userData.role="rail",an.add(O);const __bl=new Me(new ot(R,.015,.075),a);__bl.position.set(D,.0675,I),__bl.rotation.y=k,__bl.castShadow=!0,__bl.receiveShadow=!0,__bl.userData.role="rail",an.add(__bl)'
))
for old, new in reps:
    c = t.count(old)
    print('CHECK', c, old[:80])
    assert c == 1, old[:120]
    t = t.replace(old, new)
p.write_text(t, encoding='utf-8')
print('OK detail2', len(reps))

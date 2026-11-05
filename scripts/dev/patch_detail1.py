import pathlib
p = pathlib.Path('assets/template.html')
t = p.read_text(encoding='utf-8')
reps = []
# D1: door leaf micro panels + handle rosettes (physical geometry, symmetric, no hinge guess)
reps.append((
"ce.position.set(j*.02,U/2,F*Q/2),ce.castShadow=!0,ce.receiveShadow=!0,te.add(ce);for(const X of[1,-1]){const ie=new Me(new Go(.025,10,8),L(\"#b9bec6\",.3,.8));ie.position.set(j*.02+X*.035,1,F*(Q-.07)),ie.castShadow=!0,ie.receiveShadow=!0,te.add(ie)}",
"ce.position.set(j*.02,U/2,F*Q/2),ce.castShadow=!0,ce.receiveShadow=!0,te.add(ce);{const __pw=Q-.18,__ph1=(U-.01)*.38,__ph2=(U-.01)*.26,__py1=U*.68,__py2=U*.22;for(const __f of[1,-1]){const __x=j*.02+__f*.023;for(const __pp of[[__py1,__ph1],[__py2,__ph2]]){const __pn=new Me(new ot(.006,__pp[1],__pw),le);__pn.position.set(__x,__pp[0],F*Q/2),__pn.castShadow=!0,__pn.receiveShadow=!0,te.add(__pn);const __fr=new Me(new ot(.008,.022,__pw+.02),le);__fr.position.set(__x,__pp[0]+__pp[1]/2,F*Q/2),__fr.castShadow=!0,__fr.receiveShadow=!0,te.add(__fr);const __fr2=new Me(new ot(.008,.022,__pw+.02),le);__fr2.position.set(__x,__pp[0]-__pp[1]/2,F*Q/2),__fr2.castShadow=!0,__fr2.receiveShadow=!0,te.add(__fr2)}}}for(const X of[1,-1]){const __rs=new Me(new Bn(.032,.032,.01,20),L(\"#c8ced4\",.3,.7));__rs.rotation.z=Math.PI/2,__rs.position.set(j*.02+X*.012,1,F*(Q-.07)),__rs.castShadow=!0,__rs.receiveShadow=!0,te.add(__rs);const ie=new Me(new Go(.025,10,8),L(\"#b9bec6\",.3,.8));ie.position.set(j*.02+X*.035,1,F*(Q-.07)),ie.castShadow=!0,ie.receiveShadow=!0,te.add(ie)}"
))
# D2: window/door frame cap + shoe (stepped molding, only tall frames)
reps.append((
"C=(F,W,B,K,Q=0,j=.06)=>{const te=new Me(new ot(W,K,j),i);te.position.set(F,B+K/2,Q),te.castShadow=!0,te.receiveShadow=!0,f.add(te)}",
"C=(F,W,B,K,Q=0,j=.06)=>{const te=new Me(new ot(W,K,j),i);te.position.set(F,B+K/2,Q),te.castShadow=!0,te.receiveShadow=!0,f.add(te);if(K>.3){const __cp=new Me(new ot(W+.02,.025,j+.02),i);__cp.position.set(F,B+K+.012,Q),__cp.castShadow=!0,__cp.receiveShadow=!0,f.add(__cp);const __sh=new Me(new ot(W+.016,.03,j+.016),i);__sh.position.set(F,B+.015,Q),__sh.castShadow=!0,__sh.receiveShadow=!0,f.add(__sh)}}"
))
# D3: curtain rod finials + wall brackets (physical ends, no behavior change)
reps.append((
"N(t,i+.1,.03,.03,0,o-.03,-l+.02,L(\"#9aa1a8\",.3,.7))",
"N(t,i+.1,.03,.03,0,o-.03,-l+.02,L(\"#9aa1a8\",.3,.7)),la(t,.03,(i+.1)/2,o-.015,-l+.02,L(\"#9aa1a8\",.3,.7)),la(t,.03,-(i+.1)/2,o-.015,-l+.02,L(\"#9aa1a8\",.3,.7)),N(t,.025,.09,.05,-r*.6,o-.06,-l+.02,L(\"#9aa1a8\",.3,.7)),N(t,.025,.09,.05,r*.6,o-.06,-l+.02,L(\"#9aa1a8\",.3,.7))"
))
for old, new in reps:
    c = t.count(old)
    print('CHECK', c, old[:80])
    assert c == 1, old[:120]
    t = t.replace(old, new)
p.write_text(t, encoding='utf-8')
print('OK detail1', len(reps))

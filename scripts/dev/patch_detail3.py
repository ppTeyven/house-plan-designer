import pathlib
p = pathlib.Path('assets/template.html')
t = p.read_text(encoding='utf-8')
reps = []
# D1: sofa/cushion piping tube also casts+receives (was castShadow=!1, tiny tube, safe)
reps.append((
'const y=new Me(new sp(new vb(m,!0),64,.0045,6,!0),Cc(L(c.pipe,.9)));y.castShadow=!1,u.add(y)',
'const y=new Me(new sp(new vb(m,!0),64,.0045,6,!0),Cc(L(c.pipe,.9)));y.castShadow=!0,y.receiveShadow=!0,u.add(y)'
))
# D2: garage top housing box also receives (was cast only)
reps.append((
'te.position.set(V,G-.15,j),te.castShadow=!0,f.add(te)',
'te.position.set(V,G-.15,j),te.castShadow=!0,te.receiveShadow=!0,f.add(te)'
))
# D3: dining table apron under top (physical inset box, cast+receive via N default)
reps.append((
'ue(t,.08,.05,.18,0,o,0,L("#f2f0ea",.3)),la(t,.07,.05,o+.2,.02,"#7aa36a");break;',
'ue(t,.08,.05,.18,0,o,0,L("#f2f0ea",.3)),N(t,i-.18,.07,s-.18,0,o-.115,0,L(we(a,-.3),.55)),la(t,.07,.05,o+.2,.02,"#7aa36a");break;'
))
for old, new in reps:
    c = t.count(old)
    print('CHECK', c, old[:90])
    assert c == 1, old[:140]
    t = t.replace(old, new)
p.write_text(t, encoding='utf-8')
print('OK detail3', len(reps))

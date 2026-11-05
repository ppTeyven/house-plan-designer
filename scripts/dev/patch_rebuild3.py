import pathlib
p = pathlib.Path('assets/template.html')
t = p.read_text(encoding='utf-8')
reps = []
# R6: curtain — bottom lead hem bar (within bounds, same set fabric darker, no outer size change)
reps.append((
's:Fi(Jr(n.id))};t.userData.anim=y,Hd(y);break}case"showerScreen"',
's:Fi(Jr(n.id))};t.userData.anim=y,Hd(y),N(t,r*2,.025,.02,0,.025,0,L(we(a,-.22),.7));break}case"showerScreen"'
))
# R7: toilet — top flush plate inset (no outer size change)
reps.append((
'ue(t,i*.45,i*.45,.03,0,.4,-l+.18+(s-.18)/2,f).scale.z=(s-.2)/(i*.9);break}case"bathtub"',
'ue(t,i*.45,i*.45,.03,0,.4,-l+.18+(s-.18)/2,f).scale.z=(s-.2)/(i*.9),N(t,.09,.014,.05,0,.44,-l+.18+(s-.18)/2,L("#c7ccd2",.25,.8),!1);break}case"bathtub"'
))
# R8: vanity mirror — top/bottom frame rails (inset, same set)
reps.append((
'f0(e,"mirror",!0)&&N(n,t*.85,.75,.025,0,1.15,-s+.0125,L("#dfe9ef",.02,.9))}',
'f0(e,"mirror",!0)&&N(n,t*.85,.75,.025,0,1.15,-s+.0125,L("#dfe9ef",.02,.9)),N(n,t*.87,.02,.035,0,1.53,-s+.0125,L(we(o,-.2),.5)),N(n,t*.87,.02,.035,0,.77,-s+.0125,L(we(o,-.2),.5))'
))
for old, new in reps:
    c = t.count(old)
    print('CHECK', c, old[:80])
    assert c == 1, old[:160]
    t = t.replace(old, new)
p.write_text(t, encoding='utf-8')
print('OK rebuild3', len(reps))

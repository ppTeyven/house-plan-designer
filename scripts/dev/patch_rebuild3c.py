import pathlib
p = pathlib.Path('assets/template.html')
t = p.read_text(encoding='utf-8')
reps = []
# C1: floorLamp base trim ring
reps.append((
'L("#2b2e33",.35,.7));const p=ue(t,d*(h?.55:.5)',
'L("#2b2e33",.35,.7)),N(t,d*.3,.014,d*.3,0,.007,0,L("#9aa1a8",.3,.8),!1);const p=ue(t,d*(h?.55:.5)'
))
# C2: chandelier ceiling canopy
reps.append((
'ue(t,.02,.02,o*.35,0,o*.65,0,f,8);for(let d=0;d<3;d++){',
'ue(t,.06,.06,.03,0,o*.98,0,f,16),ue(t,.02,.02,o*.35,0,o*.65,0,f,8);for(let d=0;d<3;d++){'
))
# C3: fridge toe-kick (double-door branch)
reps.append((
'for(const f of[-1,1])N(t,.02,.7,.03,f*.04,o*.45,l+.01,L("#9aa1a8",.3,.8));break}N(t,i,o,s,0,0,0,L(a,.3,.4))',
'for(const f of[-1,1])N(t,.02,.7,.03,f*.04,o*.45,l+.01,L("#9aa1a8",.3,.8)),N(t,i-.12,.07,.02,0,.035,l-.03,L(we(a,-.3),.5),!1);break}N(t,i,o,s,0,0,0,L(a,.3,.4))'
))
# C4: fridge toe-kick (single-door branch)
reps.append((
',N(t,.02,.35,.03,r-.06,o*.35,l+.01,L("#9aa1a8",.3,.8));break;case"shoeCabinet"',
',N(t,.02,.35,.03,r-.06,o*.35,l+.01,L("#9aa1a8",.3,.8)),N(t,i-.12,.07,.02,0,.035,l-.03,L(we(a,-.3),.5),!1);break;case"shoeCabinet"'
))
# C5: shower mixer plate
reps.append((
'N(t,.024,g-o,.024,p,o,-l+.03,h);const m=ue',
'N(t,.024,g-o,.024,p,o,-l+.03,h),N(t,.06,.12,.02,p,o*.45,-l+.02,L("#9aa1a8",.3,.7),!1);const m=ue'
))
# C6: sideboard top edge lip
reps.append((
'N(t,i,.01,s*.9,0,.93,-l+s*.45,L(we(a,-.1),.6)),N(t,i,o-1.35,s*.8,0,1.35,-l+s*.4,f);',
'N(t,i,.01,s*.9,0,.93,-l+s*.45,L(we(a,-.1),.6)),N(t,i,o-1.35,s*.8,0,1.35,-l+s*.4,f),N(t,i-.04,.015,.02,0,.915,l+.005,L(we(a,-.2),.6),!1);'
))
for old, new in reps:
    c = t.count(old)
    print('CHECK', c, old[:80])
    assert c == 1, old[:160]
    t = t.replace(old, new)
p.write_text(t, encoding='utf-8')
print('OK rebuild3c', len(reps))

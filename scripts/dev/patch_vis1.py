import pathlib
p = pathlib.Path('assets/template.html')
t = p.read_text(encoding='utf-8')
reps = []
# V1: sofa — seat cushion division seams (dark thin gaps visible from top) + 2 contrasting throw pillows
reps.append((
'const w=ft(t,x-.025,Math.max(.22,o-.58),.16,v,.52,-l+.29,h,.06,{puff:[.006,.006,.025]});w.rotation.x=-.13}if(n.type==="sofa"&&i>1.3)',
'const w=ft(t,x-.025,Math.max(.22,o-.58),.16,v,.52,-l+.29,h,.06,{puff:[.006,.006,.025]});w.rotation.x=-.13;if(y>1){const _g=(x-.015)/y;for(let _k=1;_k<y;_k++)N(t,.012,.1,s-.28,-r+g+_g*_k,.4,.11,L(we(a,-.35),.8),!1)}}if(n.type==="sofa"&&i>1.3)'
))
# V2: sofa throw pillows -> contrasting accent colors (terracotta + slate blue), visible from bird
reps.append((
'if(n.type==="sofa"&&i>1.3)for(const b of[-1,1])ft(t,.42,.4,.09,b*(r-(b<0?g:m)-.3),.52,-l+.42,L(we(a,b<0?-.18:.12),.95),.04,{puff:[.01,.01,.035]}).rotation.set(-.3,b*.25,b*.12);break}case"coffeeTable"',
'if(n.type==="sofa"&&i>1.3)for(const b of[-1,1])ft(t,.42,.4,.09,b*(r-(b<0?g:m)-.3),.52,-l+.42,L(b<0?"#c96f2e":"#3b6ea5",.95),.04,{puff:[.01,.01,.035]}).rotation.set(-.3,b*.25,b*.12);break}case"coffeeTable"'
))
# V3: bed — contrasting runner across foot (visible from top) + pillow piping contrast
reps.append((
'ft(t,i+.06,.03,s*.22,0,.575,l-s*.14,L(a,.95),.012),ft(t,i+.06,.32,.03,0,.29,l+.005,L(a,.95),.012);break}case"nightstand"',
'ft(t,i+.06,.03,s*.22,0,.575,l-s*.14,L(a,.95),.012),ft(t,i+.06,.16,.062,0,.56,l-s*.14,L("#c96f2e",.9),.014),ft(t,i+.06,.32,.03,0,.29,l+.005,L(a,.95),.012);break}case"nightstand"'
))
# V4: diningTable — table runner (terracotta) + 4 placemats, visible from bird
reps.append((
'N(t,i-.18,.07,s-.18,0,o-.115,0,L(we(a,-.3),.55)),la(t,.07,.05,o+.2,.02,"#7aa36a");break;case"chair"',
'N(t,i-.18,.07,s-.18,0,o-.115,0,L(we(a,-.3),.55)),N(t,.44,.006,s-.24,0,o+.028,0,L("#c96f2e",.9),!1),N(t,i*.32,.004,.24,-r+i*.24,o+.028,-l+s*.24,L("#f4f1ea",.9),!1),N(t,i*.32,.004,.24,r-i*.24,o+.028,-l+s*.24,L("#f4f1ea",.9),!1),la(t,.07,.05,o+.2,.02,"#7aa36a");break}case"chair"'
))
for old, new in reps:
    c = t.count(old)
    print('CHECK', c, old[:70])
    assert c == 1, old[:200]
    t = t.replace(old, new)
p.write_text(t, encoding='utf-8')
print('OK vis1', len(reps))

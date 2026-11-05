import pathlib
p = pathlib.Path('assets/template.html')
t = p.read_text(encoding='utf-8')
def rep(old, new, tag):
    c = t.count(old)
    print(tag, c)
    assert c == 1, tag + ' FAIL ' + old[:200]
    return t.replace(old, new)

# 1) sofa seams: seat top = .39+.15=.54 -> strips sit ON TOP
old1 = "w.rotation.x=-.13}for(let _k=1;_k<y;_k++)N(t,.02,.12,s-.26,-r+g+x*_k,.4,.11,L(we(a,-.4),.85),!1);for(let _k=0;_k<y;_k++)N(t,x-.03,.012,.02,-r+g+x*(_k+.5),.475,.11,L(we(a,-.3),.9),!1);if(n.type"
new1 = "w.rotation.x=-.13}for(let _k=1;_k<y;_k++)N(t,.025,.02,s-.24,-r+g+x*_k,.541,.11,L(we(a,-.45),.9),!1);for(let _k=0;_k<y;_k++)N(t,x-.04,.014,.03,-r+g+x*(_k+.5),.541,.11+(s-.25)/2-.015,L(we(a,-.3),.9),!1);if(n.type"
t = rep(old1, new1, 'sofa-top')

# 2) bed runner: duvet top = .5+.08=.58 -> runner above it
old2 = 'ft(t,i+.06,.03,s*.22,0,.575,l-s*.14,L(a,.95),.012),ft(t,i-.1,.025,.5,0,.545,l-s*.32,L("#c96f2e",.92),.008),ft(t,i-.1,.026,.09,0,.545,l-s*.32+.2,L("#f4f1ea",.95),.006),ft(t,i+.06,.32,.03,0,.29,l+.005,L(a,.95),.012);break}case"nightstand"'
new2 = 'ft(t,i+.06,.03,s*.22,0,.575,l-s*.14,L(a,.95),.012),ft(t,i-.12,.02,.55,0,.581,l-s*.34,L("#c96f2e",.95),.008),ft(t,i-.12,.021,.1,0,.581,l-s*.34+.22,L("#f4f1ea",1),.006),ft(t,.5,.022,.3,-r+.45,.581,l-s*.34,L("#3b6ea5",.95),.006),ft(t,i+.06,.32,.03,0,.29,l+.005,L(a,.95),.012);break}case"nightstand"'
t = rep(old2, new2, 'bed-top')

# 3) dining: table top = o -> runner/placemats above o
old3 = 'N(t,i-.18,.07,s-.18,0,o-.115,0,L(we(a,-.3),.55)),N(t,.5,.008,s-.2,0,o-.021,0,L("#c96f2e",.92),!1),N(t,.34,.006,.24,-r+i*.26,o-.02,-l+s*.26,L("#f4f1ea",.95),!1),N(t,.34,.006,.24,r-i*.26,o-.02,-l+s*.26,L("#f4f1ea",.95),!1),N(t,.34,.006,.24,-r+i*.26,o-.02,l-s*.26,L("#e8e2d4",.95),!1),N(t,.34,.006,.24,r-i*.26,o-.02,l-s*.26,L("#e8e2d4",.95),!1),N(t,.16,.05,.16,0,o,0,L("#7aa36a",.95)),ue(t,.11,.04,.11,0,o+.045,0,L("#a8432a",.9));break;case"chair"'
new3 = 'N(t,i-.18,.07,s-.18,0,o-.115,0,L(we(a,-.3),.55)),N(t,.55,.007,s-.2,0,o+.001,0,L("#c96f2e",.95),!1),N(t,.36,.006,.26,-r+i*.27,o+.002,-l+s*.27,L("#f4f1ea",1),!1),N(t,.36,.006,.26,r-i*.27,o+.002,-l+s*.27,L("#f4f1ea",1),!1),N(t,.36,.006,.26,-r+i*.27,o+.002,l-s*.27,L("#e8e2d4",1),!1),N(t,.36,.006,.26,r-i*.27,o+.002,l-s*.27,L("#e8e2d4",1),!1),N(t,.2,.06,.2,0,o+.004,0,L("#7aa36a",1)),ue(t,.13,.05,.13,0,o+.06,0,L("#a8432a",.95)),ue(t,.045,.045,.045,-.05,o+.1,.04,L("#d94f3d",.95)),ue(t,.045,.045,.045,.05,o+.1,-.03,L("#e2a63d",.95)),ue(t,.045,.045,.045,0,o+.1,-.09,L("#5f8f55",.95));break;case"chair"'
t = rep(old3, new3, 'dining-top')

# 4) coffeeTable: top = o-.04+.04 = o -> tray/books/cup above o
old4 = 'break}case"coffeeTable":N(t,i,.04,s,0,o-.04,0,L(a,.35)),N(t,i-.1,.02,s-.1,0,.08,0,L(a,.5)),u(o-.04,.05,.018);break;case"tvCabinet"'
new4 = 'break}case"coffeeTable":N(t,i,.04,s,0,o-.04,0,L(a,.35)),N(t,i-.1,.02,s-.1,0,.08,0,L(a,.5)),N(t,.5,.03,.32,-r+i*.28,o+.001,0,L("#8a5a33",.9),!1),N(t,.34,.035,.24,-r+i*.28,o+.031,0,L("#3b6ea5",.95),!1),N(t,.3,.03,.2,-r+i*.28,o+.066,0,L("#c96f2e",.95),!1),ue(t,.05,.05,.09,r-i*.3,o+.001,.1,L("#f4f1ea",.95)),ue(t,.035,.035,.05,r-i*.3,o+.09,.1,L("#5f8f55",.95));break;case"tvCabinet"'
t = rep(old4, new4, 'coffee-top')

# 5) sofa throw blanket over left arm: arm top = .38+.3=.68 -> blanket above
old5 = 'if(n.type==="sofa"&&i>1.3)for(const b of[-1,1])ft(t,.42,.4,.09,b*(r-(b<0?g:m)-.3),.52,-l+.42,L(b<0?"#c96f2e":"#3b6ea5",.95),.04,{puff:[.01,.01,.035]}).rotation.set(-.3,b*.25,b*.12);break}case"coffeeTable"'
new5 = 'if(n.type==="sofa"&&i>1.3){for(const b of[-1,1])ft(t,.42,.4,.09,b*(r-(b<0?g:m)-.3),.52,-l+.42,L(b<0?"#c96f2e":"#3b6ea5",.95),.04,{puff:[.01,.01,.035]}).rotation.set(-.3,b*.25,b*.12);ft(t,.34,.025,.5,-r+g/2,.681,0,L("#c96f2e",.95),.008);ft(t,.34,.026,.12,-r+g/2,.681,-.18,L("#f4f1ea",1),.005)}break;case"coffeeTable"'
t = rep(old5, new5, 'sofa-blanket')

p.write_text(t, encoding='utf-8')
print('OK vis3')

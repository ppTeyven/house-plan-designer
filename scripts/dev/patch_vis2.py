import pathlib
p = pathlib.Path('assets/template.html')
t = p.read_text(encoding='utf-8')

def rep(old, new, tag):
    c = t.count(old)
    print(tag, 'count', c)
    assert c == 1, tag + ' anchor fail: ' + old[:160]
    return t.replace(old, new)

# --- FIX1: sofa seams: wrong _g + wrong x origin, fix to true cushion boundaries ---
old1 = "w.rotation.x=-.13;if(y>1){const _g=(x-.015)/y;for(let _k=1;_k<y;_k++)N(t,.012,.1,s-.28,-r+g+_g*_k,.4,.11,L(we(a,-.35),.8),!1)}}if(n.type"
new1 = "w.rotation.x=-.13}for(let _k=1;_k<y;_k++)N(t,.02,.12,s-.26,-r+g+x*_k,.4,.11,L(we(a,-.4),.85),!1);for(let _k=0;_k<y;_k++)N(t,x-.03,.012,.02,-r+g+x*(_k+.5),.475,.11,L(we(a,-.3),.9),!1)}if(n.type"
t = rep(old1, new1, 'sofa-seam')

# --- FIX2: bed runner was 16cm tall floating wall; make it flat wide stripe on duvet ---
old2 = 'ft(t,i+.06,.03,s*.22,0,.575,l-s*.14,L(a,.95),.012),ft(t,i+.06,.16,.062,0,.56,l-s*.14,L("#c96f2e",.9),.014),ft(t,i+.06,.32,.03,0,.29,l+.005,L(a,.95),.012);break}case"nightstand"'
new2 = 'ft(t,i+.06,.03,s*.22,0,.575,l-s*.14,L(a,.95),.012),ft(t,i-.1,.025,.5,0,.545,l-s*.32,L("#c96f2e",.92),.008),ft(t,i-.1,.026,.09,0,.545,l-s*.32+.2,L("#f4f1ea",.95),.006),ft(t,i+.06,.32,.03,0,.29,l+.005,L(a,.95),.012);break}case"nightstand"'
t = rep(old2, new2, 'bed-runner')

# --- FIX3: dining runner+placemats were floating 3-5cm above table; drop onto top + enlarge ---
old3 = 'N(t,i-.18,.07,s-.18,0,o-.115,0,L(we(a,-.3),.55)),N(t,.44,.006,s-.24,0,o,0,L("#c96f2e",.9),!1),N(t,.3,.004,.2,-r+i*.25,o+.006,0,L("#f4f1ea",.9),!1),N(t,.3,.004,.2,r-i*.25,o+.006,0,L("#f4f1ea",.9),!1),la(t,.07,.05,o+.2,.02,"#7aa36a");break;case"chair"'
new3 = 'N(t,i-.18,.07,s-.18,0,o-.115,0,L(we(a,-.3),.55)),N(t,.5,.008,s-.2,0,o-.021,0,L("#c96f2e",.92),!1),N(t,.34,.006,.24,-r+i*.26,o-.02,-l+s*.26,L("#f4f1ea",.95),!1),N(t,.34,.006,.24,r-i*.26,o-.02,-l+s*.26,L("#f4f1ea",.95),!1),N(t,.34,.006,.24,-r+i*.26,o-.02,l-s*.26,L("#e8e2d4",.95),!1),N(t,.34,.006,.24,r-i*.26,o-.02,l-s*.26,L("#e8e2d4",.95),!1),N(t,.16,.05,.16,0,o,0,L("#7aa36a",.95)),ue(t,.11,.04,.11,0,o+.045,0,L("#a8432a",.9));break;case"chair"'
t = rep(old3, new3, 'dining-runner')

p.write_text(t, encoding='utf-8')
print('OK vis2')

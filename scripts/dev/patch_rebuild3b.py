import pathlib
p = pathlib.Path('assets/template.html')
t = p.read_text(encoding='utf-8')
reps = []
# B1: bathtub drain cover inset (no outer change)
reps.append((
'ue(t,.015,.015,.15,-r+.12,o,0,L("#c7ccd2",.2,.9));break;case"washer"',
'ue(t,.015,.015,.15,-r+.12,o,0,L("#c7ccd2",.2,.9)),N(t,.05,.006,.05,r-.18,.03,0,L("#9aa1a8",.3,.8),!1);break;case"washer"'
))
# B2: washer control knob dot
reps.append((
'N(t,i-.06,.1,.01,0,o-.14,l,"#dadde0",!1);break}case"sideTable"',
'N(t,i-.06,.1,.01,0,o-.14,l,"#dadde0",!1),N(t,.03,.03,.014,i/2-.07,o*.3,l+.004,L("#2b2e33",.4,.6),!1);break}case"sideTable"'
))
# B3: vanity basin rim ring
reps.append((
'ue(n,Math.min(t/r*.28,.22),Math.min(t/r*.22,.18),.12,f,.82,.02,L("#ffffff",.15)),ue(n,.012,.012,.18,f,.82,-s+.07,L("#c7ccd2",.2,.9))',
'ue(n,Math.min(t/r*.28,.22),Math.min(t/r*.22,.18),.12,f,.82,.02,L("#ffffff",.15)),ue(n,Math.min(t/r*.28,.22)+.014,Math.min(t/r*.22,.18)+.014,.014,f,.812,.02,L("#e7ebee",.2,.7),32),ue(n,.012,.012,.18,f,.82,-s+.07,L("#c7ccd2",.2,.9))'
))
# B4: kitchen island counter edge piping
reps.append((
'N(n,t+.02,.04,i+.02,0,s-.04,0,L("#e9e6e1",.3))',
'N(n,t+.02,.04,i+.02,0,s-.04,0,L("#e9e6e1",.3)),N(n,t+.025,.008,i+.025,0,s-.065,0,L(we(r,-.15),.5),!1)'
))
for old, new in reps:
    c = t.count(old)
    print('CHECK', c, old[:80])
    assert c == 1, old[:160]
    t = t.replace(old, new)
p.write_text(t, encoding='utf-8')
print('OK rebuild3b', len(reps))

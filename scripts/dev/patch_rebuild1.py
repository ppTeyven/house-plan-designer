import pathlib
p = pathlib.Path('assets/template.html')
t = p.read_text(encoding='utf-8')
reps = []
# R1: sofa — arm-top welt cords + base shadow welt (real piping 2-4mm, within same bounds, no size change)
reps.append((
'ft(t,i,.3,s,0,.1,0,f,.04),ft(t,i,o-.1,.22,0,.1,-l+.11,f,.05),g&&ft(t,g,.3,s,-r+g/2,.38,0,f,Math.min(.07,g/2.2)),m&&ft(t,m,.3,s,r-m/2,.38,0,f,Math.min(.07,m/2.2));',
'ft(t,i,.3,s,0,.1,0,f,.04),ft(t,i,o-.1,.22,0,.1,-l+.11,f,.05),g&&ft(t,g,.3,s,-r+g/2,.38,0,f,Math.min(.07,g/2.2)),m&&ft(t,m,.3,s,r-m/2,.38,0,f,Math.min(.07,m/2.2)),N(t,i-.04,.018,.018,0,.115,0,L(we(a,-.25),.7)),g&&N(t,g-.012,.012,s-.06,-r+g/2,.535,0,L(we(a,-.12),.9)),m&&N(t,m-.012,.012,s-.06,r-m/2,.535,0,L(we(a,-.12),.9));'
))
# R2: bed — mattress base welt + blanket fold piping (crown seam, no size change)
reps.append((
'const v=s*.66;return ft(n,i+.02,.08,v,0,g+.14,r-v/2-.02,L("#fbfaf7",.95),.035,{puff:[0,.012,0],wrinkle:.007}),ft(n,i+.06,.03,s*.22,0,g+.215,r-s*.14,L(t.fabric2,.95),.012),!0}',
'const v=s*.66;N(n,i-.06,.014,.014,0,g+.1,r-v/2-.02,L(we(l,-.14),.8));return ft(n,i+.02,.08,v,0,g+.14,r-v/2-.02,L("#fbfaf7",.95),.035,{puff:[0,.012,0],wrinkle:.007}),ft(n,i+.06,.03,s*.22,0,g+.215,r-s*.14,L(t.fabric2,.95),.012),N(n,i+.02,.012,.012,0,g+.245,r-s*.14,L(we(t.fabric2,-.12),.85)),!0'
))
for old, new in reps:
    c = t.count(old)
    print('CHECK', c, old[:90])
    assert c == 1, old[:160]
    t = t.replace(old, new)
p.write_text(t, encoding='utf-8')
print('OK rebuild1', len(reps))

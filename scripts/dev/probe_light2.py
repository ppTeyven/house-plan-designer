import pathlib
p = pathlib.Path('assets/template.html')
t = p.read_text(encoding='utf-8')
cands = [
"Tn=new Lb(16777215,9272424,.9)",
"const i=new _h(16774373,2.4)",
"Oa=new _h(14674175,.4)",
"a.shadow.radius=e?2.5:t?1.8:1.2,a.shadow.blurSamples=e||t?12:8",
"pt.environmentIntensity=c?.16:.3",
"const S = { lock: false, hemi: 0.18, fill: 0.08, env: null, envI: 0.28, exp: 1.0 }",
"const Ai={hemi:1,fill:.1",
"jt.toneMappingExposure=c?1.22:1",
"S.envI = (function(){try{return rf().night?0.16:0.3;}catch(e){return 0.3;}})();",
"S.exp = 1.0;",
]
for c in cands:
    print(repr(c), '=>', t.count(c))

import pathlib
p = pathlib.Path('assets/template.html')
t = p.read_text(encoding='utf-8')
reps = []
reps.append((
"n.color.setRGB(1,.95-v*.33,.88-v*.55),n.intensity=.9+f*3.1}Tn.intensity=c?.1:.22+f*.3",
"n.color.setRGB(1,.93-v*.38,.82-v*.58),n.intensity=.85+f*2.6}Tn.intensity=c?.08:.14+f*.22"))
reps.append((
'Tn.color.set(c?"#5c6b99":"#d9e6ff"),Tn.groundColor.set(c?"#1d2233":"#b9a68a"),Oa.intensity=c?.02:.06;',
'Tn.color.set(c?"#5c6b99":"#cfdcec"),Tn.groundColor.set(c?"#141824":"#8f8478"),Oa.intensity=c?.015:.035;'))
reps.append((
"jt.toneMappingExposure=c?1.3:1,C0.traverse",
"jt.toneMappingExposure=c?1.22:1,C0.traverse"))
reps.append((
"pt.environment=c?null:B5,Ai.hemi",
"pt.environment=c?null:B5,pt.environmentIntensity=c?.22:.45,Ai.hemi"))
reps.append((
"a.shadow.radius=e?3.5:t?2.5:1,a.shadow.blurSamples=e||t?16:8,Yv()}",
"a.shadow.radius=e?3.5:t?2.5:2,a.shadow.blurSamples=e||t?16:12,Yv()}"))
reps.append((
"r.updateGtaoMaterial({radius:o?.55:1.2,distanceExponent:1.4,thickness:o?1.2:3",
"r.updateGtaoMaterial({radius:o?.5:1.6,distanceExponent:1.35,thickness:o?1:2"))
reps.append((
"o?1.15:1,samples:bi.level",
"o?1.15:1.25,samples:bi.level"))
reps.append((
"r.blendIntensity=o?.95:.85,a.addPass(r);",
"r.blendIntensity=o?1:1,a.addPass(r);"))
reps.append((
"o||(c.uniforms.vig.value=0,c.uniforms.warm.value=.02),a.addPass(c);",
"o||(c.uniforms.vig.value=.14,c.uniforms.warm.value=.03),a.addPass(c);"))
reps.append((
"GRADELUTZ={none:{sat:1.03,con:1.04,warm:0,vig:.16,lift:[0,0,0],gain:[1,1,1],sc:.1},",
"GRADELUTZ={none:{sat:1.07,con:1.1,warm:0,vig:.18,lift:[-.008,-.004,.008],gain:[1.01,1,.99],sc:.18},"))
reps.append((
"const S = { lock: false, hemi: 0.34, fill: 0.16, env: null, envI: 0.5, exp: 1.0 };",
"const S = { lock: false, hemi: 0.22, fill: 0.1, env: null, envI: 0.35, exp: 0.95 };"))
reps.append((
"S.hemi = night ? 0.12 : 0.34;",
"S.hemi = night ? 0.1 : 0.22;"))
reps.append((
"S.fill = night ? 0.05 : 0.16;",
"S.fill = night ? 0.04 : 0.1;"))
reps.append((
"S.envI = night ? 0.22 : 0.50;",
"S.envI = night ? 0.2 : 0.35;"))
reps.append((
"S.exp = night ? 1.15 : 1.0;",
"S.exp = night ? 1.1 : 0.95;"))
reps.append((
"var ci = night ? 0.22 : 0.4;",
"var ci = night ? 0.18 : 0.15;"))
for old, new in reps:
    c = t.count(old)
    print('CHECK', c, old[:70])
    assert c == 1, old[:100]
    t = t.replace(old, new)
p.write_text(t, encoding='utf-8')
print('OK patched', len(reps))

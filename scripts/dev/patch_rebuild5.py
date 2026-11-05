import pathlib
p = pathlib.Path('assets/template.html')
t = p.read_text(encoding='utf-8')
reps = []
# S1: wallface merged wall geometry must cast shadows (root cause of "door has no shadow")
reps.append((
'c.receiveShadow=!0,c.userData.role="wallface",c.userData.roles=["wallface"],c.userData.core=!0,F0.add(c)',
'c.receiveShadow=!0,c.castShadow=!0,c.userData.role="wallface",c.userData.roles=["wallface"],c.userData.core=!0,F0.add(c)'
))
# S2: mitre wall caps cast/receive
reps.append((
'd.castShadow=d.receiveShadow=!0,d.userData.roles=["cap","wallface"]',
'd.castShadow=d.receiveShadow=!0,d.userData.roles=["cap","wallface"]'
))
# S3: skirting base mesh must cast shadow
reps.append((
'u.position.set(f.x/1e3,t/2,f.y/1e3),u.rotation.y=Math.atan2(-c.u.y,c.u.x),u.receiveShadow=!0,u.userData.role="skirt",F0.add(u);',
'u.position.set(f.x/1e3,t/2,f.y/1e3),u.rotation.y=Math.atan2(-c.u.y,c.u.x),u.receiveShadow=!0,u.castShadow=!0,u.userData.role="skirt",F0.add(u);'
))
# S4: ceiling panels must cast+receive
reps.append((
'a.position.y=e,a.userData.role="ceil",C0.add(a);const r=new Zt({color:"#f3f1ec",roughness:.95,emissive:"#f3f1ec",emissiveIntensity:.15}),',
'a.position.y=e,a.userData.role="ceil",a.castShadow=!0,a.receiveShadow=!0,C0.add(a);const r=new Zt({color:"#f3f1ec",roughness:.95,emissive:"#f3f1ec",emissiveIntensity:.15}),'
))
reps.append((
'const c=new Me(K7(X7(n.rects)),Y7());c.position.y=i.type==="flat"?e-s:e,c.userData.role="ceil",C0.add(c);return}',
'const c=new Me(K7(X7(n.rects)),Y7());c.position.y=i.type==="flat"?e-s:e,c.userData.role="ceil",c.castShadow=!0,c.receiveShadow=!0,C0.add(c);return}'
))
reps.append((
'u.position.set((c.x+c.w/2)/1e3,e-s/2,(c.y+c.h/2)/1e3),u.userData.role="ceil",',
'u.position.set((c.x+c.w/2)/1e3,e-s/2,(c.y+c.h/2)/1e3),u.userData.role="ceil",u.castShadow=!0,u.receiveShadow=!0,'
))
for old, new in reps:
    c = t.count(old)
    print('CHECK', c, old[:70])
    assert c == 1, old[:200]
    t = t.replace(old, new)
p.write_text(t, encoding='utf-8')
print('OK shadow batch', len(reps))

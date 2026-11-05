import pathlib
p = pathlib.Path('assets/template.html')
t = p.read_text(encoding='utf-8')
old = 'u.userData.role="skirt",F0.add(u)}}}const C9={};'
new = ('u.userData.role="skirt",F0.add(u);'
       'const __skcap=new Me(new ot((l-r)/1e3,.012,.02),i);__skcap.position.set(f.x/1e3,t+.006,f.y/1e3),__skcap.rotation.y=u.rotation.y,'
       '__skcap.castShadow=!0,__skcap.receiveShadow=!0,__skcap.userData.role="skirt",F0.add(__skcap);'
       'const __skrev=new Me(new ot((l-r)/1e3,.014,.008),i);__skrev.position.set(f.x/1e3,.007,f.y/1e3),__skrev.rotation.y=u.rotation.y,'
       '__skrev.castShadow=!0,__skrev.receiveShadow=!0,__skrev.userData.role="skirt",F0.add(__skrev)}}}const C9={};')
print('COUNT', t.count(old))
assert t.count(old) == 1
t = t.replace(old, new)
p.write_text(t, encoding='utf-8')
print('OK skirt profile')

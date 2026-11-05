import pathlib, re
t=pathlib.Path('assets/template.html').read_text(encoding='utf-8')
# 1. sv definition
for m in re.finditer(r'function sv\(.*?\)', t):
    p=m.start()
    print('sv-def-at', p)
    print(t[p:p+800].replace('\n',' | ')[:2000])
    print()
    break
# search const sv / let sv / sv=
for pat in ['const sv=', 'let sv', ' sv=', '.glb', 'furnlib/', 'GLTF', 'gltf', 'parse(']:
    print(pat, t.count(pat))
print()
# kv switch: find switch(n.type) blocks - get sofa 3D builder
p=t.find('switch(n.type){case"airVent"')
print('switch-at', p)
if p>0:
    seg=t[p:p+12000].replace('\n',' | ')
    print(seg[:12000])

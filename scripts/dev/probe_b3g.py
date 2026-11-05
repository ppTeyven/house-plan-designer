import pathlib
t=pathlib.Path('assets/template.html').read_text(encoding='utf-8')
def show(key, L=600):
    p=t.find(key)
    print('===',key,p)
    if p>=0:
        print(t[p:p+L].replace('\n',' | ')[:2000])
        print()
for k in ['userData.role="rail"', '__bl', 'baseboard', 'skirting', 'case"rug"', 'floorMat', 'wallMat', '.receiveShadow=!0', 'castShadow=!0']:
    show(k)
print('counts rail', t.count('userData.role="rail"'), 'receive', t.count('receiveShadow'))

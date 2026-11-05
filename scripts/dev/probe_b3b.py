import pathlib
t=pathlib.Path('assets/template.html').read_text(encoding='utf-8')
def ctx(sub, L=500):
    p=t.find(sub)
    print('FIND',repr(sub[:60]),'->',p)
    if p>=0:
        print(t[p-200:p+L].replace('\n',' | ')[:2000])
        print()
for s in ['t.userData.anim=y', 'pleats:Array.from', 'case"bathtub"', 'f0(e,"mirror",!0)&&N(n,t*.85', 'scale.z=(s-.2)/(i*.9)']:
    ctx(s)

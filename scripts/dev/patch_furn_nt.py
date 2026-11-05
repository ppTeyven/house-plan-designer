import pathlib
p = pathlib.Path('assets/template.html')
t = p.read_text(encoding='utf-8')
def rep(old, new, tag):
    global t
    c = t.count(old)
    print(tag, c)
    assert c == 1, tag + ' FAIL ' + old[:200]
    t = t.replace(old, new)
old = '__g.traverse(__x=>{if(__x.isMesh&&__x.material&&__x.material.name&&__x.material.name.indexOf("U_")===0)__x.material=__furnMat(__x.material.name.slice(2),a);});'
new = '__g.traverse(__x=>{if(__x.isMesh&&__x.material&&__x.material.name&&__x.material.name.indexOf("U_")===0)__x.material=__furnMat(__x.material.name.slice(2),a);});__g.traverse(__x=>{if(__x.userData&&__x.userData.noTheme)__x.traverse(__y=>{if(__y.isMesh)__y.userData.noTheme=!0});});'
rep(old, new, 'furn-nt-propagate')
p.write_text(t, encoding='utf-8')
print('OK furn-nt')

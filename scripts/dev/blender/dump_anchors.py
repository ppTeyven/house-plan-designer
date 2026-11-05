import os, re, io

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
p = os.path.join(ROOT, 'assets', 'template.html')
s = open(p, encoding='utf-8').read()

out = io.StringIO()


def show(label, needle, ctx_before=260, ctx_after=260):
    i = s.find(needle)
    out.write('===== %s =====\n' % label)
    if i < 0:
        out.write('  NOT FOUND\n\n')
        return
    out.write('  count=%d at %d\n' % (s.count(needle), i))
    out.write('  ...%s...\n\n' % s[max(0, i - ctx_before):i + len(needle) + ctx_after].replace('\n', ' | '))


show('v array', 'v=[e,e,h,e,m,y]')
show('j7', 'function j7(n,e){if(!n)return e;const t=ks(n);')
show('UV block', 'if(x||b){const V=P.getAttribute("uv");', 120, 520)
show('window frame i', 'i=L("#5b626c",.5,.3)', 200, 120)
show('column', 's.kind==="column"?(N(o,a,n,r,0,0,0,L("#f1efea",.9))', 100, 420)
show('switch plate', 'L("#fbfbfa",.4),!1),g)', 260, 120)
show('socket hole', 'const m=L("#3a3d42",.8);', 120, 360)
show('downlight mat', 'i=()=>new Zt({color:"#e9e7e2",emissive:"#ffe9c4",emissiveIntensity:.02,roughness:.5});', 80, 120)
show('ARCH_MAT block', 'ceilTrim:__archMat("ceiling_white"', 120, 200)
show('shower rs', 'L("#c8ced4",.3,.7));__rs.rotation.z', 200, 260)
show('shower ie', 'L("#b9bec6",.3,.8));', 200, 260)
show('win handle', 'L("#c7ccd2",.3,.8));be.position.set', 220, 160)
show('sill cp/sh', 'const __cp=new Me(new ot(W+.02,.025,j+.02),i);', 160, 340)

open('_anchors.txt', 'w', encoding='utf-8').write(out.getvalue())
print(out.getvalue())

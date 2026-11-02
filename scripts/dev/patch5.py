# -*- coding: utf-8 -*-
import sys
p = 'assets/template.html'
t = open(p, encoding='utf-8').read()
patches = []
def add(name, old, new):
    patches.append((name, old, new))
NL = '\n'
# P1a 2d->3d: keep zoom & center, canonical k==1
add('P1a',
'if(n==="3d"){'+NL+'const t=M4.getBoundingClientRect();'+NL+'try{ao(L1(Se,t.width,t.height))}catch(_){}',
'if(n==="3d"){'+NL+'const t=M4.getBoundingClientRect();'+NL+'try{const _w=t.width,_h=t.height,_f={s:0,ox:0,oy:0};P1(_f,E.geo.bounds,_w,_h,60);if(isFinite(Se.s)&&Se.s>0&&_f.s>0){const _k=Math.min(4,Math.max(.25,Se.s/_f.s)),_cx=(_w/2-Se.ox)/Se.s,_cy=(_h/2-Se.oy)/Se.s,_s=_f.s*_k;ao(L1({s:_s,ox:_w/2-_cx*_s,oy:_h/2-_cy*_s},_w,_h))}else ao(L1(_f,_w,_h))}catch(_){try{ao(L1(Se,t.width,t.height))}catch(_){}}')
# P1b split->3d: map left-pane Se to full width
add('P1b',
'if(n==="3d"&&e==="split"){'+NL+'const fit={s:0,ox:0,oy:0};'+NL+'try{P1(fit,E.geo.bounds,st.width,st.height,60)}catch(_){}'+NL+'W2.dataset.view=n;E.view=n;'+NL+'try{wi(L1(fit,st.width,st.height),650)}catch(_){}'+NL+'await wait(700);'+NL+'}',
'if(n==="3d"&&e==="split"){'+NL+'const fit={s:0,ox:0,oy:0};'+NL+'try{P1(fit,E.geo.bounds,st.width,st.height,60)}catch(_){}'+NL+'W2.dataset.view=n;E.view=n;'+NL+'try{const _p=M4.getBoundingClientRect(),_g={s:0,ox:0,oy:0};try{P1(_g,E.geo.bounds,Math.max(50,_p.width),Math.max(50,_p.height),60)}catch(_){}let _k=1;try{if(isFinite(Se.s)&&Se.s>0&&_g.s>0)_k=Math.min(4,Math.max(.25,Se.s/_g.s))}catch(_){}const _s=fit.s*_k;let _cx=0,_cy=0;try{if(isFinite(Se.s)&&Se.s>0){_cx=(_p.width/2-Se.ox)/Se.s;_cy=(_p.height/2-Se.oy)/Se.s}}catch(_){}wi(L1({s:_s,ox:st.width/2-_cx*_s,oy:st.height/2-_cy*_s},st.width,st.height),650)}catch(_){try{wi(L1(fit,st.width,st.height),650)}catch(_){}}'+NL+'await wait(700);'+NL+'}')
# P1c smart exit canonical
add('P1c',
'$e()&&Ga(Z.view3d==="tile"?"tile":"all"),wi(Hv(0,0),1100),ts.particles',
'$e()&&Ga(Z.view3d==="tile"?"tile":"all"),(function(){try{const _r=W2.getBoundingClientRect(),_f={s:0,ox:0,oy:0};P1(_f,E.geo.bounds,_r.width,_r.height,60);wi(L1(_f,_r.width,_r.height),1100)}catch(_){try{wi(Hv(0,0),1100)}catch(_){}})(),ts.particles')
# P2a fill light overhead
add('P2a',
'Oa=new _h(14674175,.4),Oa.position.set(20,10,-6),pt.add(Oa)',
'Oa=new _h(14674175,.4),Oa.position.set(-4,28,6),pt.add(Oa)')
# P2b/c trim fill
add('P2b', 'Oa.intensity=c?.04:.14', 'Oa.intensity=c?.04:.10')
add('P2c', 'Oa.intensity=.18', 'Oa.intensity=.12')
# P3a wi ease param
add('P3a', 'function wi(n,e,t){const i=', 'function wi(n,e,t,i){const i=')
add('P3b',
'Bi={t0:performance.now(),dur:e,fromT:Tt.target.clone(),s0:{r:s.radius,p:s.phi,t:s.theta},to:n,dt:o,done:t},Tt.enabled=!1',
'Bi={t0:performance.now(),dur:e,fromT:Tt.target.clone(),s0:{r:s.radius,p:s.phi,t:s.theta},to:n,dt:o,done:t,ease:i},Tt.enabled=!1')
add('P3c',
'const ZL=n=>n<.5?4*n*n*n:1-Math.pow(-2*n+2,3)/2;',
'const ZL=n=>n<.5?4*n*n*n:1-Math.pow(-2*n+2,3)/2;const ZO=n=>1-Math.pow(1-n,3);')
add('P3d',
'const e=Bi,t=x0((n-e.t0)/e.dur,0,1),i=ZL(t),s=e.fromT.clone().lerp(e.to.target,i)',
'const e=Bi,t=x0((n-e.t0)/e.dur,0,1),i=(e.ease||ZL)(t),s=e.fromT.clone().lerp(e.to.target,i)')
# P3e Vp entry ZO
add('P3e',
'try{skyFade(1)}catch(e){}})})}',
'try{skyFade(1)}catch(e){}})})},ZO)}')
# P3f Ns exit ZO
add('P3f',
'n?ao(uo()):wi({...i,r:i.r*.8},1200),Yc()}',
'n?ao(uo()):wi({...i,r:i.r*.8},1200,null,ZO),Yc()}')
# P3g/h black immediate
add('P3g',
'/* \u9e1f\u77b0\u2192\u6f2b\u6e38: \u9ed1\u5c4f\u5728"\u843d\u5730\u524d"\u5c31\u5f00\u59cb(\u98de\u884c\u672b\u5c3e), \u843d\u5730\u77ac\u95f4\u5df2\u5b8c\u6210\u906e\u9ed1, \u91cd\u5efa\u5b8c\u6210\u540e\u5feb\u901f\u6de1\u51fa */',
'/* \u9e1f\u77b0\u2192\u6f2b\u6e38: \u70b9\u51fb\u5373\u906e\u9ed1(450ms\u6e10\u9ed1\u8986\u76d6\u6574\u4e2a\u98de\u884c+\u91cd\u5efa), \u843d\u5730\u91cd\u5efa\u540e\u5feb\u901f\u6de1\u51fa */')
add('P3h',
'function __walkPre(flightMs) {'+NL+'  try {'+NL+'    var f = __fade();'+NL+'    setTimeout(function () {'+NL+'      f.style.transitionDuration = "150ms";'+NL+'      f.style.opacity = .95;'+NL+'    }, Math.max(0, flightMs - 180));'+NL+'  } catch (e) { }'+NL+'}',
'function __walkPre(flightMs) {'+NL+'  try {'+NL+'    var f = __fade();'+NL+'    f.style.transitionDuration = "450ms";'+NL+'    f.style.opacity = .98;'+NL+'  } catch (e) { }'+NL+'}')
fails = []
for name, old, new in patches:
    c = t.count(old)
    if c != 1:
        fails.append((name, c))
        continue
    t = t.replace(old, new)
if fails:
    print('ANCHOR FAIL:')
    for n, c in fails:
        print(' ', n, 'count=', c)
    sys.exit(1)
open(p, 'w', encoding='utf-8').write(t)
print('patched OK:', len(patches))

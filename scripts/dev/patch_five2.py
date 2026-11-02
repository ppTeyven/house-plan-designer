# -*- coding: utf-8 -*-
import sys
p = 'assets/template.html'
t = open(p, encoding='utf-8').read()
orig_len = len(t)
edits = []
def rep(old, new, tag):
    global t
    c = t.count(old)
    print(tag, 'count=', c)
    if c != 1:
        print('SKIP', tag)
        return False
    t = t.replace(old, new)
    edits.append(tag)
    return True

# ---- 1. scale: record std K/C on 2d->3d, reuse on split->3d and smart-exit ----
old1 = 'const _w=t.width,_h=t.height,_f={s:0,ox:0,oy:0};P1(_f,E.geo.bounds,_w,_h,60);if(isFinite(Se.s)&&Se.s>0&&_f.s>0){const _k=Math.min(4,Math.max(.25,Se.s/_f.s)),_cx=(_w/2-Se.ox)/Se.s,_cy=(_h/2-Se.oy)/Se.s,_s=_f.s*_k;ao(L1({s:_s,ox:_w/2-_cx*_s,oy:_h/2-_cy*_s},_w,_h))}else ao(L1(_f,_w,_h))'
new1 = ('const _w=t.width,_h=t.height,_f={s:0,ox:0,oy:0};P1(_f,E.geo.bounds,_w,_h,60);if(isFinite(Se.s)&&Se.s>0&&_f.s>0){const _k=Math.min(4,Math.max(.25,Se.s/_f.s)),_cx=(_w/2-Se.ox)/Se.s,_cy=(_h/2-Se.oy)/Se.s,_s=_f.s*_k;try{window.__stdK=_k;window.__stdC={x:_cx,y:_cy}}catch(_){}ao(L1({s:_s,ox:_w/2-_cx*_s,oy:_h/2-_cy*_s},_w,_h))}else ao(L1(_f,_w,_h))')
rep(old1, new1, 'scale-record-2d3d')

old2 = 'try{const _p=M4.getBoundingClientRect(),_g={s:0,ox:0,oy:0};try{P1(_g,E.geo.bounds,Math.max(50,_p.width),Math.max(50,_p.height),60)}catch(_){}let _k=1;try{if(isFinite(Se.s)&&Se.s>0&&_g.s>0)_k=Math.min(4,Math.max(.25,Se.s/_g.s))}catch(_){}const _s=fit.s*_k;let _cx=0,_cy=0;try{if(isFinite(Se.s)&&Se.s>0){_cx=(_p.width/2-Se.ox)/Se.s;_cy=(_p.height/2-Se.oy)/Se.s}}catch(_){}wi(L1({s:_s,ox:st.width/2-_cx*_s,oy:st.height/2-_cy*_s},st.width,st.height),650)}catch(_){try{wi(L1(fit,st.width,st.height),650)}catch(_){}}'
new2 = ('try{const _p=M4.getBoundingClientRect(),_g={s:0,ox:0,oy:0};try{P1(_g,E.geo.bounds,Math.max(50,_p.width),Math.max(50,_p.height),60)}catch(_){}let _k=1;try{if(window.__stdK>0)_k=window.__stdK;else if(isFinite(Se.s)&&Se.s>0&&_g.s>0)_k=Math.min(4,Math.max(.25,Se.s/_g.s))}catch(_){}const _s=fit.s*_k;let _cx=0,_cy=0;try{if(window.__stdC&&isFinite(window.__stdC.x)){_cx=window.__stdC.x;_cy=window.__stdC.y}else if(isFinite(Se.s)&&Se.s>0){_cx=(_p.width/2-Se.ox)/Se.s;_cy=(_p.height/2-Se.oy)/Se.s}}catch(_){}wi(L1({s:_s,ox:st.width/2-_cx*_s,oy:st.height/2-_cy*_s},st.width,st.height),650)}catch(_){try{wi(L1(fit,st.width,st.height),650)}catch(_){}}')
rep(old2, new2, 'scale-reuse-split3d')

# smart exit (rh false branch) — keep 3d size instead of refit
old3 = '(function(){try{const _r=W2.getBoundingClientRect(),_f={s:0,ox:0,oy:0};P1(_f,E.geo.bounds,_r.width,_r.height,60);wi(L1(_f,_r.width,_r.height),1100)}catch(_){try{wi(Hv(0,0),1100)}catch(_){}}})()'
new3 = ('(function(){try{const _r=W2.getBoundingClientRect(),_f={s:0,ox:0,oy:0};P1(_f,E.geo.bounds,_r.width,_r.height,60);let _k2=1,_cx2=0,_cy2=0,_hasC=!1;try{if(window.__stdK>0)_k2=window.__stdK}catch(_){}try{if(window.__stdC&&isFinite(window.__stdC.x)){_cx2=window.__stdC.x;_cy2=window.__stdC.y;_hasC=!0}}catch(_){}if(_hasC){const _s2=_f.s*_k2;wi(L1({s:_s2,ox:_r.width/2-_cx2*_s2,oy:_r.height/2-_cy2*_s2},_r.width,_r.height),1100)}else wi(L1(_f,_r.width,_r.height),1100)}catch(_){try{wi(Hv(0,0),1100)}catch(_){}}})()')
rep(old3, new3, 'scale-reuse-smart-exit')

# ---- 2. light: Oa overhead + lower, remove Zh permanent lock ----
old4 = 'Oa=new _h(14674175,.4),Oa.position.set(-4,28,6),pt.add(Oa)'
new4 = 'Oa=new _h(14674175,.4),Oa.position.set(0,30,0),pt.add(Oa)'
rep(old4, new4, 'light-Oa-overhead')

old5 = 'Oa.intensity=c?.04:.10;'
new5 = 'Oa.intensity=c?.02:.06;'
rep(old5, new5, 'light-Oa-day')

old6 = 'n.color.set("#fff4e4"),n.intensity=3.1,Tn.intensity=.5,Tn.color.set("#ffffff"),Tn.groundColor.set("#d8d0c4"),Oa.intensity=.12'
new6 = 'n.color.set("#fff4e4"),n.intensity=3.1,Tn.intensity=.5,Tn.color.set("#ffffff"),Tn.groundColor.set("#d8d0c4"),Oa.intensity=.08'
rep(old6, new6, 'light-Oa-flat')

# remove Zh intensity permanent-zero hack (keep sun clamp)
old7 = 'for (var zi = 0; zi < Zh.length; zi++) {\n          if (!Zh[zi].__lk) {\n            Zh[zi].__lk = true;\n            (function (zl) {\n              var rv = zl.intensity;\n              Object.defineProperty(zl, "intensity", { configurable: true, get: function () { return 0; }, set: function () { } });\n            })(Zh[zi]);\n          }\n        }'
if t.count(old7) == 1:
    t = t.replace(old7, 'for (var zi = 0; zi < Zh.length; zi++) { try { if (Zh[zi].__lk) { delete Zh[zi].intensity; Zh[zi].__lk = false; } } catch (e) { } }')
    edits.append('light-unlock-Zh')
    print('light-unlock-Zh count= 1')
else:
    print('light-unlock-Zh count=', t.count(old7), 'SKIP direct, try compact')
    import re
    m = re.search(r'for \(var zi = 0; zi < Zh\.length; zi\+\+\) \{\s*if \(!Zh\[zi\]\.__lk\)', t)
    print('regex found:', bool(m))

# ---- 3. flight: bird->walk ease-in (gradually magnify), keep walk->bird ease-out ----
old8 = '__walkPre(1300);wi({target:i,r:.01,p:s.phi,t:s.theta},1300,()=>{__walkFinish(()=>{re.active=!0,Tt.enabled=!1,C0.visible=!0;try{skyDim()}catch(e){}$e()&&gs(),Yc();try{skyFade(1)}catch(e){}})},__ZOease)'
new8 = '__walkPre(1300);wi({target:i,r:.01,p:s.phi,t:s.theta},1300,()=>{__walkFinish(()=>{re.active=!0,Tt.enabled=!1,C0.visible=!0;try{skyDim()}catch(e){}$e()&&gs(),Yc();try{skyFade(1)}catch(e){}})},function(n){return n*n*n})'
rep(old8, new8, 'flight-easein-walk')

# ---- 4. black earlier: 180ms fast cover, full opaque ----
old9 = '''function __walkPre(flightMs) {
  try {
    var f = __fade();
    f.style.transitionDuration = "450ms";
    f.style.opacity = .98;
  } catch (e) { }
}'''
new9 = '''function __walkPre(flightMs) {
  try {
    var f = __fade();
    f.style.transition = "none";
    f.style.opacity = 0;
    void f.offsetWidth;
    f.style.transition = "opacity 180ms ease";
    f.style.opacity = 1;
  } catch (e) { }
}'''
rep(old9, new9, 'black-early-180')

# ---- 5. smart: per-stage try/catch + VB guard so pins/hello always render ----
old10 = 'function lz(n,e){JB(n,e);'
new10 = 'function lz(n,e){try{JB(n,e)}catch(_err){try{window.__smartErr="JB:"+String((_err&&_err.stack)||_err).slice(0,600)}catch(_){}}'
rep(old10, new10, 'smart-guard-JB')

old11 = 'iz(n),sz(),$B(),qB(),rz(n,e);'
new11 = 'try{iz(n)}catch(_e){try{window.__smartErr="iz:"+String((_e&&_e.stack)||_e).slice(0,600)}catch(_){}}try{sz()}catch(_e){try{window.__smartErr="sz:"+String((_e&&_e.stack)||_e).slice(0,600)}catch(_){}}try{$B()}catch(_e){try{window.__smartErr="$B:"+String((_e&&_e.stack)||_e).slice(0,600)}catch(_){}}try{qB()}catch(_e){try{window.__smartErr="qB:"+String((_e&&_e.stack)||_e).slice(0,600)}catch(_){}}try{rz(n,e)}catch(_e){try{window.__smartErr="rz:"+String((_e&&_e.stack)||_e).slice(0,600)}catch(_){}}'
rep(old11, new11, 'smart-guard-stages')

old12 = 'i!==lt.sig&&(lt.sig=i,lt.devs=VB(),ad.innerHTML=""'
new12 = 'i!==lt.sig&&(lt.sig=i,try{lt.devs=VB()}catch(_e){try{window.__smartErr="VB:"+String((_e&&_e.stack)||_e).slice(0,800)}catch(_){}try{lt.devs=[]}catch(_){}},ad.innerHTML=""'
rep(old12, new12, 'smart-guard-VB')

print('edits:', edits)
print('len', orig_len, '->', len(t))
open(p, 'w', encoding='utf-8').write(t)
print('WROTE')

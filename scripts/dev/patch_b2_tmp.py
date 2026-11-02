t = open('assets/template.html', encoding='utf-8').read()
orig_len = len(t)
def rep(old, new, must=1):
    global t
    c = t.count(old)
    assert c == must, f'anchor count {c} != {must} :: {old[:90]}'
    t = t.replace(old, new)

# A. Ir: split-only-pan + topdown-left-pan
rep('Tt.enableRotate=!n,Tt.screenSpacePanning=n,Tt.mouseButtons.LEFT=n?ha.PAN:ha.ROTATE',
    'Tt.enableRotate=!n&&E.view!=="split",Tt.screenSpacePanning=n||E.view==="split",Tt.mouseButtons.LEFT=(n||E.view==="split"||function(){try{var v=Ze.position.clone().sub(Tt.target);return new qr().setFromVector3(v).phi<.18}catch(e){return!1}()}())?ha.PAN:ha.ROTATE,Tt.mouseButtons.RIGHT=ha.PAN,Tt.touches.ONE=E.view==="split"?sl.PAN:sl.ROTATE,Tt.touches.TWO=sl.DOLLY_PAN')

# B1. wi watchdog
rep('to:n,dt:o,done:t},Tt.enabled=!1}const ZL=',
    'to:n,dt:o,done:t},Tt.enabled=!1,function(b_,d_){setTimeout(function(){try{if(Bi===b_){try{ao(b_.to)}catch(e){}try{b_.done&&b_.done()}catch(e){}Bi=null;Tt.enabled=!re.active;try{Tt.update()}catch(e){}}}catch(e){}},d_+1500)}(Bi,e)}const ZL=')

# B2. JL completion respects split
rep('t>=1&&(Bi=null,Tt.enabled=!re.active,Tt.update(),(a=e.done)==null||a.call(e))',
    't>=1&&(Bi=null,Tt.enabled=!re.active,try{Ir()}catch(_){},Tt.update(),(a=e.done)==null||a.call(e))')

# C. _x freeze during transitioning
rep('function _x(){const n=Y5.getBoundingClientRect();if(!(n.width<2||n.height<2)){if(Se.W){',
    'function _x(){const n=Y5.getBoundingClientRect();if(!(n.width<2||n.height<2)){if(Se.W&&!E.transitioning){')

# D. Ua tail (newline-aware: match actual bytes around stopGlue)
old_tail = 'stopGlue=!0;\ntry{Gh()}catch(_){}\ntry{_x()}catch(_){}\ntry{Je()}catch(_){}\ntry{Zc()}catch(_){}\nE.transitioning=!1;'
assert t.count(old_tail) == 1, f'tail count {t.count(old_tail)}'
new_tail = ('stopGlue=!0;try{Bi=null;Tt.enabled=!re.active;try{Tt.update()}catch(_){}}catch(_){}'
 'try{if(E.view==="split"){var p2=M4.getBoundingClientRect(),p3=b8.getBoundingClientRect();'
 'if(p2.width>10){try{P1(Se,E.geo.bounds,p2.width,p2.height,60)}catch(_){}Se.W=p2.width;Se.H=p2.height;try{Je()}catch(_){}}'
 'if(p3.width>10){try{ao(L1(Se,p3.width,p3.height))}catch(_){}}try{Ir()}catch(_){}try{Zc()}catch(_){}}}catch(_){}'
 '\ntry{Gh()}catch(_){}\ntry{_x()}catch(_){}\ntry{Je()}catch(_){}\ntry{Zc()}catch(_){}\ntry{Ir()}catch(_){}\nE.transitioning=!1;')
rep(old_tail, new_tail)

# E1. Vp refuse split
rep('function Vp(n){if(re.active||Bi)return;',
    'function Vp(n){if(E.view==="split"){try{Te("分屏模式下仅平移对照，不支持漫游")}catch(_){}return}if(re.active||Bi)return;')

# E2. entering split exits walk
rep('}else{\nconst st=W2.getBoundingClientRect();\nif(n==="3d"&&e==="split"){',
    '}else{try{Ns(!0)}catch(_){}const st=W2.getBoundingClientRect();if(n==="3d"&&e==="split"){')

# F1. look btn blue + light closes
rep('he("#lookBtn").onclick=()=>{x8.classList.toggle("open"),kw.classList.remove("open"),vc()}',
    'he("#lookBtn").onclick=()=>{x8.classList.toggle("open"),kw.classList.remove("open"),vc(),he("#lookBtn").classList.toggle("on",x8.classList.contains("open"))}')
rep('he("#lightBtn").addEventListener("click",()=>x8.classList.remove("open"))',
    'he("#lightBtn").addEventListener("click",()=>{x8.classList.remove("open"),he("#lookBtn").classList.remove("on")})')

# F2. smart btn toggle + blue
rep('he("#smartBtn").onclick=()=>rh(!0)',
    'he("#smartBtn").onclick=()=>{var on=!document.body.classList.contains("smart-mode");he("#smartBtn").classList.toggle("on",on);rh(on)}')

# F3. rh keeps smartBtn blue in sync
rep('N0.classList.add("show")}else{lt.on=!1',
    'N0.classList.add("show");try{he("#smartBtn").classList.add("on")}catch(_){}}else{lt.on=!1')
rep('N0.classList.remove("show"),document.body.classList.remove("smart-mode"),od.classList.remove("smart")',
    'N0.classList.remove("show"),document.body.classList.remove("smart-mode"),od.classList.remove("smart");try{he("#smartBtn").classList.remove("on")}catch(_){}')

# F4. CSS blue active + split hides + pano/xr gone
rep('.pane{will-change:auto}',
    '.pane{will-change:auto}\n.btn.glass.on{background:var(--accent);border-color:var(--accent);color:#fff;box-shadow:0 2px 8px #2f6fed4d;font-weight:600}\n.btn.glass.on:hover:not(:disabled){background:#2458c8;border-color:#1f4fb8;color:#fff}\n.stage[data-view="split"] #camSeg [data-cam="fp"],.stage[data-view="split"] #walkCtl,.stage[data-view="split"] .fphint,.stage[data-view="split"] #joy,.stage[data-view="split"] #crosshair{display:none!important}\n#panoBtn,#xr-btn{display:none!important}')

# G. remove panoBtn node
rep('he("#renderBtn").onclick=async()=>{',
    'try{he("#panoBtn")&&he("#panoBtn").remove()}catch(_){}he("#renderBtn").onclick=async()=>{')

# H. split two-way sync: 2D->3D via view event; 3D->2D via controls change
rep('r0("view",n=>{n&&typeof n.x=="number"&&(he("#stCoord").textContent=`X ${Oe(n.x)} · Y ${Oe(n.y)} mm`),he("#stZoom").textContent="缩放 "+Math.round(Se.s/Se.base*100)+"%"})',
    'r0("view",n=>{n&&typeof n.x=="number"&&(he("#stCoord").textContent=`X ${Oe(n.x)} · Y ${Oe(n.y)} mm`),he("#stZoom").textContent="缩放 "+Math.round(Se.s/Se.base*100)+"%"})\nr0("view",()=>{if(E.view==="split"&&!re.active&&!window.__spSync){window.__spSync=!0;try{var r=b8.getBoundingClientRect();if(r.width>10)ao(L1(Se,r.width,r.height))}catch(_){}window.__spSync=!1}})')
rep('Tt=new Av(Ze,O0),Tt.enableDamping=!0,Tt.dampingFactor=.15',
    'Tt=new Av(Ze,O0),Tt.addEventListener("change",function(){if(E.view==="split"&&!re.active&&!Bi&&!E.transitioning&&!window.__spSync){window.__spSync=!0;try{var r=M4.getBoundingClientRect();if(r.width>10){var z=Zv(r.width,r.height);if(isFinite(z.s)&&z.s>0){Se.s=z.s;Se.ox=z.ox;Se.oy=z.oy;Se.W=r.width;Se.H=r.height;try{Je()}catch(e){}}}}catch(e){}window.__spSync=!1}}),Tt.enableDamping=!0,Tt.dampingFactor=.15')

open('assets/template.html', 'w', encoding='utf-8').write(t)
print('OK new_len', len(t), 'delta', len(t) - orig_len)

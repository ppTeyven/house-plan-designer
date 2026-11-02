t = open('assets/template.html', encoding='utf-8').read()
import re
anchors = [
  'Tt.enableRotate=!n,Tt.screenSpacePanning=n,Tt.mouseButtons.LEFT=n?ha.PAN:ha.ROTATE',
  'function JL(n){var a;const e=Bi,t=x0((n-e.t0)/e.dur,0,1)',
  't>=1&&(Bi=null,Tt.enabled=!re.active,Tt.update(),(a=e.done)==null||a.call(e))',
  'function _x(){const n=Y5.getBoundingClientRect();if(!(n.width<2||n.height<2)){if(Se.W){',
  '}catch(_){}stopGlue=!0;try{Gh()}catch(_){}try{_x()}catch(_){}try{Je()}catch(_){}try{Zc()}catch(_){}E.transitioning=!1;try{bt("view")}catch(_){}',
  'function Vp(n){if(re.active||Bi)return;',
  'he("#lookBtn").onclick=()=>{x8.classList.toggle("open"),kw.classList.remove("open"),vc()}',
  'he("#lightBtn").addEventListener("click",()=>x8.classList.remove("open"))',
  'he("#smartBtn").onclick=()=>rh(!0)',
  'N0.classList.add("show")}else{lt.on=!1',
  'N0.classList.remove("show"),document.body.classList.remove("smart-mode"),od.classList.remove("smart")',
  '.pane{will-change:auto}',
]
for a in anchors:
    print(t.count(a), '::', a[:80])
print('SCRIPT_END', repr(t[t.find('</script>')-120:t.find('</script>')+20]))

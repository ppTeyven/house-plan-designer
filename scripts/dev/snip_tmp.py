import subprocess
snips = {
 'B1': 'function(b_,d_){setTimeout(function(){try{if(Bi===b_){try{ao(b_.to)}catch(e){}try{b_.done&&b_.done()}catch(e){}Bi=null;Tt.enabled=!re.active;try{Tt.update()}catch(e){}}}catch(e){}},d_+1500)}(Bi,e)',
 'B1fix': 'function(b_,d_){setTimeout(function(){try{if(Bi===b_){try{ao(b_.to)}catch(e){}try{if(b_.done)b_.done()}catch(e){}Bi=null;Tt.enabled=!re.active;try{Tt.update()}catch(e){}}}catch(e){}},d_+1500)}(Bi,e)',
 'IR': 'Tt.enableRotate=!n&&E.view!=="split",Tt.screenSpacePanning=n||E.view==="split",Tt.mouseButtons.LEFT=(n||E.view==="split"||function(){try{var v=Ze.position.clone().sub(Tt.target);return new qr().setFromVector3(v).phi<.18}catch(e){return!1}()}())?ha.PAN:ha.ROTATE',
 'JL': 't>=1&&(Bi=null,Tt.enabled=!re.active,(function(){try{Ir()}catch(_){}})(),Tt.update(),(a=e.done)==null||a.call(e))',
}
for k,s in snips.items():
    open('/tmp/s.mjs','w').write('var Bi,Tt,Ze,qr,E,n,ha,re,a,e;function Ir(){}function ao(){};'+s+';')
    r = subprocess.run(['node','--check','/tmp/s.mjs'],capture_output=True)
    print(k, r.returncode, r.stderr[-300:] if r.returncode else b'OK')

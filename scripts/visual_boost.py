import pathlib
p = pathlib.Path('assets/template.html')
t = p.read_text(encoding='utf-8')
orig_len = len(t)
reps = []
# 1) 材质微表面: 在 x7 前插入程序化 bump/编织纹理 + __MATFX
old_x7 = 'return!1}const x7=new Map;function vD(n){'
new_x7 = ('return!1}const __BUMP=(()=>{try{const c=document.createElement("canvas");c.width=c.height=128;'
 'const x=c.getContext("2d"),d=x.createImageData(128,128);for(let i=0;i<d.data.length;i+=4){'
 'const v=118+Math.random()*20|0;d.data[i]=d.data[i+1]=d.data[i+2]=v;d.data[i+3]=255}'
 'x.putImageData(d,0,0);const t=new ms(c);t.wrapS=t.wrapT=E0;return t}catch(e){return null}})();'
 'const __WOV=(()=>{try{const c=document.createElement("canvas");c.width=c.height=128;'
 'const x=c.getContext("2d");x.fillStyle="#808080";x.fillRect(0,0,128,128);'
 'x.strokeStyle="rgba(255,255,255,.22)";x.lineWidth=1;'
 'for(let i=0;i<128;i+=3){x.beginPath();x.moveTo(0,i+.5);x.lineTo(128,i+.5);x.stroke();'
 'x.beginPath();x.moveTo(i+.5,0);x.lineTo(i+.5,128);x.stroke()}'
 'const t=new ms(c);t.wrapS=t.wrapT=E0;return t}catch(e){return null}})();'
 'function __MATFX(m,k){try{if(!m||m.userData.__fx)return m;m.userData.__fx=1;'
 'const wood=k==="wood",fab=k==="fabric"||k==="rattan",lea=k==="leather",'
 'met=k==="metal"||k==="brass"||k==="black"||k==="mirror",gla=k==="glass"||k==="frosted",'
 'sto=k==="stone"||k==="concrete"||k==="paint";'
 'if(fab){m.envMapIntensity=.35;if(__WOV){m.bumpMap=__WOV;m.bumpScale=.004}}'
 'else if(lea){m.envMapIntensity=.55;if(__WOV){m.bumpMap=__WOV;m.bumpScale=.0025}}'
 'else if(wood){m.envMapIntensity=.75;if(__BUMP){m.bumpMap=__BUMP;m.bumpScale=.0018}}'
 'else if(met){m.envMapIntensity=1.15}'
 'else if(gla){m.envMapIntensity=1.0}'
 'else if(sto){m.envMapIntensity=.45;if(__BUMP){m.bumpMap=__BUMP;m.bumpScale=.0012}}'
 'else{m.envMapIntensity=.6}'
 '}catch(e){}return m}'
 'const x7=new Map;function vD(n){')
reps.append((old_x7, new_x7))
# 2) vD 创建后挂 __MATFX
old_vd = ('s=new Zt({color:n.color,roughness:e.rough,metalness:e.metal,transparent:t<1,opacity:t,'
 'depthWrite:t>=1,side:t<1?Qt:Hi,...e.emissive?{emissive:n.color,emissiveIntensity:1.2}:{}}),x7.set(i,s)),s}')
new_vd = ('s=new Zt({color:n.color,roughness:e.rough,metalness:e.metal,transparent:t<1,opacity:t,'
 'depthWrite:t>=1,side:t<1?Qt:Hi,...e.emissive?{emissive:n.color,emissiveIntensity:1.2}:{}}),'
 '__MATFX(s,String(y0(n,"mat","paint"))),x7.set(i,s)),s}')
reps.append((old_vd, new_vd))
# 3) L 通用材质: 粗糙挂 bump + envMapIntensity 分层
old_L = 'function L(n,e=.75,t=0,i){const s=n+"|"+e+"|"+t+"|"+(i?JSON.stringify(i):"");return v9.has(s)||v9.set(s,new Zt({color:n,roughness:e,metalness:t,...i||{}})),v9.get(s)}'
new_L = ('function L(n,e=.75,t=0,i){const s=n+"|"+e+"|"+t+"|"+(i?JSON.stringify(i):"");'
 'return v9.has(s)||v9.set(s,new Zt({color:n,roughness:e,metalness:t,...i||{}})),'
 '((m)=>{try{if(!m.userData.__fx&&__BUMP){m.userData.__fx=1;'
 'if(m.metalness>.5)m.envMapIntensity=1.1;else if(m.roughness>=.85){m.envMapIntensity=.4;m.bumpMap=__BUMP;m.bumpScale=.0012}'
 'else{m.envMapIntensity=.6;if(m.roughness>.5){m.bumpMap=__BUMP;m.bumpScale=.001}}}'
 '}catch(e){}return m})(v9.get(s))}')
reps.append((old_L, new_L))
# 4) 灯光: 环境提亮层压暗, 太阳压低角度、阴影收锐
reps.append(('pt.environmentIntensity=c?.22:.45,', 'pt.environmentIntensity=c?.16:.3,'))
reps.append(('const S = { lock: false, hemi: 0.22, fill: 0.1, env: null, envI: 0.35, exp: 0.95 };',
              'const S = { lock: false, hemi: 0.18, fill: 0.08, env: null, envI: 0.28, exp: 1.0 };'))
reps.append(('S.hemi = night ? 0.1 : 0.22;', 'S.hemi = night ? 0.09 : 0.18;'))
reps.append(('S.fill = night ? 0.04 : 0.1;', 'S.fill = night ? 0.035 : 0.08;'))
reps.append(('S.envI = night ? 0.2 : 0.35;', 'S.envI = night ? 0.18 : 0.28;'))
reps.append(('S.exp = night ? 1.1 : 0.95;', 'S.exp = night ? 1.08 : 1.0;'))
reps.append(('Al(i.az,Math.max(3,u),a)', 'Al(i.az,Math.max(8,Math.min(u,42)),a)'))
reps.append(('Tn.intensity=c?.08:.14+f*.22', 'Tn.intensity=c?.06:.1+f*.16'))
reps.append(('Tn.groundColor.set(c?"#141824":"#8f8478")', 'Tn.groundColor.set(c?"#141824":"#6f6a60")'))
reps.append(('Oa.intensity=c?.015:.035;', 'Oa.intensity=c?.012:.028;'))
reps.append(('a.shadow.radius=e?3.5:t?2.5:2,a.shadow.blurSamples=e||t?16:12',
              'a.shadow.radius=e?2.5:t?1.8:1.2,a.shadow.blurSamples=e||t?12:8'))
# 5) 鸟瞰保留一盏室内暖补光, 室内不再死黑
old_ax = 'Tn.intensity=Ai.hemi,Tn.color.copy(Ai.hemiColor),Oa.intensity=Ai.fill,pt.environment=Ai.env;return}'
new_ax = ('Tn.intensity=Ai.hemi,Tn.color.copy(Ai.hemiColor),Oa.intensity=Ai.fill,pt.environment=Ai.env;'
 'try{NL();const _c=Lr();su[0].position.copy(_c);su[0].position.y+=3.4;su[0].color.set("#ffe2bd");'
 'su[0].intensity=.55;su[0].distance=16;su[0].decay=1.7;su[0].castShadow=!1;su[0].shadow.needsUpdate=!0;'
 'for(let _k=1;_k<su.length;_k++){su[_k].intensity=0}}catch(e){}return}')
reps.append((old_ax, new_ax))
# 6) 背景/雾/地面压暗一点, 托住家具对比
reps.append(('pt.background=new Be("#e4e9ef"),pt.fog=new K4("#e4e9ef",45,100)',
              'pt.background=new Be("#dfe5ec"),pt.fog=new K4("#dfe5ec",60,140)'))
reps.append(('color:"#d5dbe2",roughness:1', 'color:"#c6ccd4",roughness:1'))
# 7) 曝光回到 1.0, 对比更实
reps.append(('jt.toneMappingExposure=1.05', 'jt.toneMappingExposure=1.0'))
miss = []
for a, b in reps:
    if a not in t:
        miss.append(a[:70])
    else:
        t = t.replace(a, b)
p.write_text(t, encoding='utf-8')
print('miss:', miss)
print('len', orig_len, '->', len(t))

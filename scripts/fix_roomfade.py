import pathlib
p = pathlib.Path('assets/template.html').read_text(encoding='utf-8')
orig_len = len(p)
miss = []

# 1) Zh 窗光: 直接赋值改平滑目标(函数调用时 __setLT 已定义,运行时解析)
old_zh = 'h.intensity=u*(1.5+5.5*i)}),a.length>0}'
new_zh = 'h.intensity=u*(1.5+5.5*i)}),a.length>0}'
# NOTE: OL() runs inside ax(); we smooth inside fade tick by tracking Zh separately.
# Instead of touching OL line (used once), we wrap: record targets after OL call in ax patch below.

# 2) ax: 灯跟开关走(不再按人在哪个屋硬灭别屋灯) + 全部走平滑 + su 位置平滑
old_all = 'function ax(){if(!m0)return;const n=zL();for(const c of n)c.light.intensity=c.base*c.lv;'
new_all = ('function ax(){if(!m0)return;const n=zL();for(const c of n)__setLT(c.light,c.base*c.lv);')
if old_all not in p:
    miss.append('ax-all')
else:
    p = p.replace(old_all, new_all)

# 灭灯行: 只灭找不到房间的野灯,别屋的灯保持开关状态(跟人进没进没关系)
old_cull = 'for(const c of n)(!c.r||!t.includes(c.r))&&(c.light.intensity=0);'
new_cull = 'for(const c of n)(!c.r)&&__setLT(c.light,0);'
if old_cull not in p:
    miss.append('ax-cull')
else:
    p = p.replace(old_cull, new_cull)

# su 影子池: 强度保持原逻辑(v3 行走锁定期已自带平滑),位置改为记目标由 tick 插值
old_su = ('.slice(0,su.length).forEach((c,u)=>{const f=su[u];f.position.copy(c.pos),'
          'f.color.copy(c.light.color),f.intensity=c.base*c.lv,')
new_su = ('.slice(0,su.length).forEach((c,u)=>{const f=su[u];'
          'if(f.userData.__pt)f.userData.__pt.copy(c.pos);else{f.userData.__pt=c.pos.clone();f.position.copy(c.pos)}'
          ',f.color.copy(c.light.color),f.intensity=c.base*c.lv,')
if old_su not in p:
    miss.append('ax-su')
else:
    p = p.replace(old_su, new_su)

# 3) 在 ax 定义尾部追加淡入淡出系统,并注册到主循环 $d
anchor = 'f.shadow.needsUpdate=!0})}function q5(n){'
fade = ('f.shadow.needsUpdate=!0})}'
        'const __LT=new Map();'
        'function __setLT(l,t){try{if(!l)return;let e=__LT.get(l);'
        'if(!e){e={cur:l.intensity,tgt:t};__LT.set(l,e);}e.tgt=t;}catch(_){}}'
        'try{$d.add((dt)=>{try{const k=Math.min(1,(dt||.016)*4.5);let dead=null;'
        'for(const[l,e]of __LT){'
        'if(!l.parent){(dead||(dead=[])).push(l);continue;}'
        'const d=e.tgt-e.cur;'
        'if(Math.abs(d)<.015){if(l.intensity!==e.tgt)l.intensity=e.tgt;e.cur=e.tgt;}'
        'else{e.cur+=d*k;l.intensity=e.cur;}}'
        'if(dead)for(const l of dead)__LT.delete(l);'
        'for(const f of su){const q=f.userData.__pt;'
        'if(q&&f.parent){f.position.lerp(q,Math.min(1,(dt||.016)*5));'
        'if(f.position.distanceToSquared(q)<1e-8)f.position.copy(q);}}'
        '}catch(_){}});}catch(_){}'
        '}function q5(n){')
if anchor not in p:
    miss.append('ax-anchor')
else:
    p = p.replace(anchor, fade)

p2 = p
p_path = pathlib.Path('assets/template.html')
p_path.write_text(p2, encoding='utf-8')
print('miss:', miss)
print('len', orig_len, '->', len(p2))

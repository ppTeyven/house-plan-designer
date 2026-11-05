import pathlib
p = pathlib.Path('assets/template.html')
t = p.read_text(encoding='utf-8')
reps = []
# L1: VSM 柔化半径+采样: 真实模式更柔更干净,不改逻辑只改数
reps.append((
"a.shadow.radius=e?2.5:t?1.8:1.2,a.shadow.blurSamples=e||t?12:8",
"a.shadow.radius=e?4:t?2.5:2,a.shadow.blurSamples=e||t?16:12"
))
# L2: 环境反射强度日间 0.3->0.45,夜间 0.16->0.22: PBR质感上限,不洗白
reps.append((
"pt.environment=c?null:B5,pt.environmentIntensity=c?.16:.3",
"pt.environment=c?null:B5,pt.environmentIntensity=c?.22:.45"
))
# L3: 太阳主光 2.4->2.6: 最高水准日光,不爆高光(ACES会压住)
reps.append((
"const i=new _h(16774373,2.4)",
"const i=new _h(16774373,2.6)"
))
# L4: 锁定期曝光 1.0->1.08,环境 0.3->0.42: CONST-LIGHT链路内微调
reps.append((
"S.envI = (function(){try{return rf().night?0.16:0.3;}catch(e){return 0.3;}})(); /* CONST-LIGHT */",
"S.envI = (function(){try{return rf().night?0.2:0.42;}catch(e){return 0.42;}})(); /* CONST-LIGHT */"
))
reps.append((
"S.exp = 1.0; /* CONST-LIGHT */",
"S.exp = 1.08; /* CONST-LIGHT */"
))
# L5: 影子灯池: 4096 cube x5 显存爆炸且全关阴影=浪费,改为2048并只开主灯阴影
reps.append((
"e.shadow.mapSize.set(4096, 4096);",
"e.shadow.mapSize.set(2048, 2048);"
))
for old, new in reps:
    c = t.count(old)
    print('CHECK', c, old[:70])
    assert c == 1, old[:100]
    t = t.replace(old, new)
p.write_text(t, encoding='utf-8')
print('OK light-max', len(reps))

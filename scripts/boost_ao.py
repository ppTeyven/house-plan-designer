import pathlib
p = pathlib.Path('assets/template.html')
t = p.read_text(encoding='utf-8')
reps = [
  ("radius:o?.5:1.6,distanceExponent:1.35,thickness:o?1:2,scale:o?1.15:1.25", "radius:o?.6:1.7,distanceExponent:1.3,thickness:o?1:2,scale:o?1.4:1.6"),
  ("r.blendIntensity=o?1:1,a.addPass(r);", "r.blendIntensity=o?1.2:1.3,a.addPass(r);"),
  ("eh.ao.updateGtaoMaterial({ radius: 0.8, distanceExponent: 1.4, thickness: 1.4, scale: 1.05, samples: 16 });", "eh.ao.updateGtaoMaterial({ radius: 1.7, distanceExponent: 1.3, thickness: 2, scale: 1.6, samples: 24 });"),
  ("eh.ao.blendIntensity = 0.85;", "eh.ao.blendIntensity = 1.3;"),
  ("eh.ao.updateGtaoMaterial(walk ? { radius: .55, distanceExponent: 1.4, thickness: 1.2, scale: 1.15, samples: smp } : { radius: 1.2, distanceExponent: 1.4, thickness: 3, scale: 1, samples: smp });", "eh.ao.updateGtaoMaterial(walk ? { radius: .6, distanceExponent: 1.3, thickness: 1.2, scale: 1.4, samples: smp } : { radius: 1.7, distanceExponent: 1.3, thickness: 2, scale: 1.6, samples: smp });"),
  ("eh.ao.updatePdMaterial({ lumaPhi: 10, depthPhi: 2, normalPhi: 3, radius: walk ? 6 : 4, rings: 2, samples: 16 });", "eh.ao.updatePdMaterial({ lumaPhi: 10, depthPhi: 2, normalPhi: 3, radius: walk ? 5 : 3, rings: 2, samples: 16 });"),
  ("eh.ao.blendIntensity = walk ? .9 : .75;", "eh.ao.blendIntensity = walk ? 1.2 : 1.3;"),
]
miss=[]
for a,b in reps:
    if a not in t:
        miss.append(a[:60])
    t=t.replace(a,b)
p.write_text(t, encoding='utf-8')
print('miss:', miss)
print('done')

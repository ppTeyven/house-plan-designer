import pathlib
t=pathlib.Path('assets/template.html').read_text(encoding='utf-8')
keys={
 'sofa-piping':'N(t,i-.04,.018,.018',
 'bed-piping':'N(n,i-.06,.014,.014',
 'table-apron':'N(t,i-.18,.07' if t.count('N(t,i-.18,.07') else 'o-h-.09',
 'wardrobe-groove':'N(t,i-.06,.014,.014,0,.44' if False else 'userData',
 'curtain-bar':'N(t,r*2,.025,.02',
 'toilet-plate':'N(t,.09,.014,.05,0,.44',
 'mirror-rails':'N(n,t*.87,.02,.035',
 'tub-drain':'N(t,.05,.006,.05,r-.18',
 'washer-knob':'N(t,.03,.03,.014,i/2-.07',
 'basin-rim':'ue(n,Math.min(t/r*.28,.22)+.014',
 'island-lip':'N(n,t+.025,.008,i+.025',
 'lamp-base':'N(t,d*.3,.014,d*.3',
 'chandelier-canopy':'ue(t,.06,.06,.03,0,o*.98',
 'fridge-kick':'N(t,i-.12,.07,.02,0,.035',
 'shower-plate':'N(t,.06,.12,.02,p,o*.45',
 'sideboard-lip':'N(t,i-.04,.015,.02,0,.915',
}
ok=True
for k,v in keys.items():
    c=t.count(v)
    print(k,c)
    if c<1: ok=False
print('ALL_OK' if ok else 'MISSING', len(t))

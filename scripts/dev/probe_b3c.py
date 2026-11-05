import pathlib
t=pathlib.Path('assets/template.html').read_text(encoding='utf-8')
print('curtain-bar',t.count('N(t,r*2,.025,.02'))
print('toilet-plate',t.count('N(t,.09,.014,.05,0,.44'))
print('mirror-rails',t.count('N(n,t*.87,.02,.035'))
for k in ['case"floorLamp"', 'case"chandelier"', 'case"ceilingLamp"', 'case"wallLamp"', 'case"refrigerator"', 'case"rangeHood"', 'case"gasStove"', 'case"microwave"', 'case"oven"', 'case"tv"', 'case"airConditioner"', 'case"waterHeater"', 'case"washBasin"', 'case"toilet"', 'case"sink"', 'case"faucet"', 'roughness', 'aoMap', 'normalScale']:
    print(k, t.count(k))
print('len', len(t))

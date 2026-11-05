import pathlib,re
t=pathlib.Path('assets/template.html').read_text(encoding='utf-8')
def show(name, pat):
    ms=list(re.finditer(pat,t))
    print('===',name,'count',len(ms))
    for m in ms[:6]:
        s=max(0,m.start()-220); e=min(len(t),m.end()+220)
        print(t[s:e].replace('\n',' | ')[:2200]); print('---POS',m.start())
    print()
show('tonemapping', r'toneMapping|ACES|exposure|outputColorSpace')
show('hemi-ambient', r' new (HemisphereLight|AmbientLight)[^;]*;')
show('dir-sun', r'new (_h|DirectionalLight)[^;]*;')
show('shadow-cfg', r'\.shadow\.(mapSize|bias|normalBias|radius|blurSamples|camera)[^;]*;?')
show('env-intensity', r'environmentIntensity|envI|envMapIntensity')
show('point-pool', r'PointLight[^;]{0,120}')
show('furniture-builders', r'function (Y[A-Za-z0-9$_]{1,3}|[A-Za-z0-9$_]{2,4}床|build[A-Za-z]+|make[A-Za-z]+)')

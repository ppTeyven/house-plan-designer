import pathlib, re
p = pathlib.Path('assets/template.html')
t = p.read_text(encoding='utf-8')
def show(pat, ctx=400, limit=5):
    print('='*20, pat)
    for m in list(re.finditer(pat, t))[:limit]:
        s=max(0,m.start()-ctx); e=min(len(t),m.end()+ctx)
        print(t[s:e].replace('\n',' | ')[:1500])
        print('---pos', m.start())
    print()
# renderer / tone mapping / shadows
show(r'toneMapping', 300, 8)
show(r'shadowMap\.(type|enabled)', 300, 10)
show(r'shadow\.mapSize', 300, 10)
show(r'shadow\.radius|shadow\.blurSamples|shadow\.bias', 300, 10)
show(r'environmentIntensity|environment\b', 300, 10)
show(r'HemisphereLight|AmbientLight|DirectionalLight|PointLight|SpotLight|RectAreaLight', 200, 12)
show(r'new (MeshStandardMaterial|MeshPhysicalMaterial)', 300, 12)
show(r'roughness:\s*[\d\.]+|metalness:\s*[\d\.]+', 200, 15)
show(r'normalMap|roughnessMap|aoMap\b', 200, 10)
show(r'RoomEnvironment|PMREMGenerator', 300, 6)

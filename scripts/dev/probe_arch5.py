import pathlib,re
t=pathlib.Path('assets/template.html').read_text(encoding='utf-8')
for kw in ['userData.role="wall"','role:"wall"','"wall",','wainscot','baseboard','molding','crown','__wallTrim','plinthTrim']:
    print(kw, t.count(kw))
for m in re.finditer(r'userData\.role="([a-zA-Z]+)"', t):
    pass
print(sorted(set(re.findall(r'userData\.role="([a-zA-Z]+)"', t))))
print(sorted(set(re.findall(r'userData\.mats=\{([^}]*)\}', t)))[:10])

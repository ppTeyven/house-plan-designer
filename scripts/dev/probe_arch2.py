import pathlib,re
t=pathlib.Path('assets/template.html').read_text(encoding='utf-8')
# find wall mesh builders in 3D
for m in re.finditer(r'function ([A-Za-z_$][\w$]*)\(', t):
    pass
names=[m.group(1) for m in re.finditer(r'function ([A-Za-z_$][\w$]*)\(', t)]
print('funcs', len(names))
# look for keywords
for kw in ['wainscot','panelWall','wallMesh','wallGroup','skirt','trim','crownMolding','plinth']:
    print(kw, t.count(kw))
# find 3D wall building: search "墙" near mesh creation
idxs=[m.start() for m in re.finditer(r'side:Qt\)', t)]
print('Qt count', len(idxs))
p=t.find('wallPaint')
print('wallPaint',p)
# print function names containing 'Wall' or 'wall'
print([n for n in names if 'all' in n.lower() or 'loor' in n.lower()][:60])

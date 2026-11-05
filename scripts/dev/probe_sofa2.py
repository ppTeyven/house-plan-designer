import pathlib
t=pathlib.Path('assets/template.html').read_text(encoding='utf-8')
p=t.find('const y=n.type!="sofa"?1')
print(repr(t[p:p+1200]))

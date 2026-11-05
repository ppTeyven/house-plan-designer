import pathlib
t=pathlib.Path('assets/template.html').read_text(encoding='utf-8')
p=t.find('w.rotation.x=-.13;if(y>1)')
print(repr(t[p-200:p+400]))

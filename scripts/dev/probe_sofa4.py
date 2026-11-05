import pathlib
t=pathlib.Path('assets/template.html').read_text(encoding='utf-8')
p=t.find('w.rotation.x=-.13}')
print(repr(t[p-500:p+800])[:3000])

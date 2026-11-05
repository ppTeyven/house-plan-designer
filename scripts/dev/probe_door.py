import pathlib
t=pathlib.Path('assets/template.html').read_text(encoding='utf-8')
i=t.find('k.type==="door"||k.type==="double"')
print(repr(t[max(0,i-800):i+2800])[:5000])

import pathlib
t=pathlib.Path('assets/template.html').read_text(encoding='utf-8')
p=t.find('case"diningTable":N(t,i,.05')
print(repr(t[p:p+900]))

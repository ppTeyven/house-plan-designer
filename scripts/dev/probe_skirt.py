import pathlib
t=pathlib.Path('assets/template.html').read_text(encoding='utf-8')
p=t.find('userData.role="skirt"')
print(repr(t[p-700:p+120]))

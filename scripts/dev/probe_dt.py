import pathlib
t=pathlib.Path('assets/template.html').read_text(encoding='utf-8')
p=t.find('case"diningTable"')
print(t[p:p+900].replace('\n',' | ')[:3000])

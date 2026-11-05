import pathlib,re
t=pathlib.Path('assets/template.html').read_text(encoding='utf-8')
cases=sorted(set(re.findall(r'case"([a-zA-Z0-9_]+)"',t)))
print(len(cases))
for c in cases:
    print(c)

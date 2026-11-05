import pathlib,re
t=pathlib.Path('assets/template.html').read_text(encoding='utf-8')
# list all furniture case labels
cases=sorted(set(re.findall(r'case"([a-zA-Z0-9_]+)"',t)))
print('cases',len(cases))
print(cases[:200])
print('---kv---')
i=t.find('function kv(')
print(repr(t[i:i+2500])[:3000])

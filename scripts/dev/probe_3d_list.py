import pathlib,re
t=pathlib.Path('assets/template.html').read_text(encoding='utf-8')
p=t.find('function kv(')
print('kv at',p)
q=t.find('const __BUMP=')
print('bump at',q)
seg=t[p:q] if q>p else t[p:p+200000]
print('seglen',len(seg))
cases=re.findall(r'case"([a-zA-Z0-9_]+)"',seg)
print('cases',len(cases))
print(','.join(cases))

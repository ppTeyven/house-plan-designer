import pathlib
t=pathlib.Path('assets/template.html').read_text(encoding='utf-8')
p=t.find('case"bed":{const f=L(')
seg=t[p:p+6000]
print(seg)

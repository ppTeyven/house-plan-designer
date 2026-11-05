import pathlib
t=pathlib.Path('assets/template.html').read_text(encoding='utf-8')
key='N(t,i-.18,.07,s-.18'
p=t.find(key)
print('pos',p)
print(repr(t[p-300:p+300]))

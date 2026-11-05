import pathlib
t = pathlib.Path('assets/template.html').read_text(encoding='utf-8')
i = t.find('case"coffeeTable":N(t,i,.04')
print('idx', i)
print(repr(t[i:i+400]))
print('count full', t.count('u(o-.04,.05,.018)'))
j = t.find('u(o-.04,.05,.018)')
print(repr(t[j-200:j+200]))

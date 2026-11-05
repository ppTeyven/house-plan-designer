import pathlib
p = pathlib.Path('assets/template.html')
t = p.read_text(encoding='utf-8')
old = '.005)}break;case"coffeeTable"'
new = '.005)}break}case"coffeeTable"'
print('count', t.count(old))
assert t.count(old) == 1
t = t.replace(old, new)
p.write_text(t, encoding='utf-8')
print('fixed blanket brace')

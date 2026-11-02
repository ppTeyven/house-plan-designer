import pathlib
p = pathlib.Path('assets/template.html')
t = p.read_text(encoding='utf-8')
old = '.overlay{position:absolute;display:flex;gap:6px;z-index:2}'
new = '.overlay{position:absolute;display:flex;gap:6px;z-index:2;pointer-events:none;max-width:calc(100% - 24px);flex-wrap:wrap}.overlay button,.overlay input,.overlay select,.overlay .seg,.overlay .glass{pointer-events:auto}'
assert t.count(old) == 1, t.count(old)
t = t.replace(old, new)
p.write_text(t, encoding='utf-8')
print('OK overlay click-through')

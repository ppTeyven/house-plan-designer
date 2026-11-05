import pathlib, re
t=pathlib.Path('assets/template.html').read_text(encoding='utf-8')
for m in re.finditer(r'kv\(', t):
    p=m.start()
    print('---', p)
    print(t[p-400:p+400].replace('\n',' | ')[:1000])
print('done')

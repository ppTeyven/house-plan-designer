import pathlib, re
t=pathlib.Path('assets/template.html').read_text(encoding='utf-8')
# find WebGLRenderer occurrences context
for m in re.finditer(r'WebGLRenderer|THREE\.Scene|new [A-Z][a-zA-Z0-9]*\(renderer|function Je', t):
    p=m.start()
    print('---', m.group(0), p)
    print(t[p-200:p+400].replace('\n',' | ')[:900])
    if p>900000:
        break
print('done')
# find syncFurniture-ish: search kv( usage
print('kv( count', t.count('kv('))
print('syncFurn count', t.count('syncFurn'))
# find S3 assignment
for m in re.finditer(r'S3\s*=\s*\{|S3\.[a-zA-Z]+\s*=', t):
    p=m.start()
    print('S3:', m.group(0), p)
    if p>800000 and p<1100000:
        print(t[p-100:p+300].replace('\n',' | ')[:600])
print('done2')

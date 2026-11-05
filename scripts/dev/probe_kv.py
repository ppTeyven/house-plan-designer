import pathlib,re
t=pathlib.Path('assets/template.html').read_text(encoding='utf-8')
i=t.find('function kv(')
print('kv pos',i)
print(t[i:i+6000].replace('\n',' | ')[:7000])
print()
print('---LEN',len(t))
# find sofa case in kv
for key in ['case"sofa"', 'case"bed"', 'case"cabinet"', 'case"wardrobe"', 'case"diningTable"', 'case"desk"', 'case"tvCabinet"']:
    p=t.find(key)
    print(key, p)

import pathlib,re
t=pathlib.Path('assets/template.html').read_text(encoding='utf-8')
kv=t.find('function kv(')
# find 3D sofa/cabinet/table cases AFTER kv
for key in ['case"sofa"', 'case"armchair"', 'case"diningTable"', 'case"coffeeTable"', 'case"cabinet"', 'case"tvCabinet"', 'case"desk"', 'case"chair"', 'case"bookshelf"']:
    # find all occurrences, print whether before/after kv and snippet
    occ=[m.start() for m in re.finditer(re.escape(key),t)]
    print(key, occ[:6])
print('kv',kv)
# dump kv 3D switch around sofa if exists after kv
seg=t[kv:kv+120000]
for key in ['case"sofa"', 'case"diningTable"', 'case"cabinet"']:
    p=seg.find(key)
    print('--- in-kv',key,p)
    if p>=0:
        print(seg[p:p+2500].replace('\n',' | ')[:2800])

import pathlib,re
for fn in ['assets/template.html','assets/template.bak_rebuild0']:
    t=pathlib.Path(fn).read_text(encoding='utf-8')
    idxs=[m.start() for m in re.finditer(r'_cached',t)]
    print(fn,'count',len(idxs))
    for p in idxs[:6]:
        print('   ',repr(t[p-200:p+200]))

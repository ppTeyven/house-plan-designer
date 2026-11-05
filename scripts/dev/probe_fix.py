import pathlib
t=pathlib.Path('assets/template.html').read_text(encoding='utf-8')
for k in ['N(t,.02,.35', 'case"shoeCabinet"', 'o*.35,l+.01']:
    p=t.find(k)
    print(k,p)
    if p>0:
        print(t[p-200:p+200].replace('\n',' | ')[:1000])
        print()

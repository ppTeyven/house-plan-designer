import pathlib
t=pathlib.Path('assets/template.html').read_text(encoding='utf-8')
for key in ['sofa-seam','_k<y','_k=0;_k<y','rotation.x=-.13}for','w.rotation.x=-.13']:
    p=t.find(key if '}' in key or '.' in key else key)
    print(key, p)
    if p>=0:
        print(repr(t[p-200:p+600])[:2000])
        print('---')

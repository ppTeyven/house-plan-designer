import pathlib
src = pathlib.Path('assets/template.html').read_text(encoding='utf-8')
anchor = 'pt=new za,'
assert src.count(anchor) == 1, src.count(anchor)
src = src.replace(anchor, 'pt=new za,window.__SCENE=pt,')
pathlib.Path('assets/verify_tmp.html').write_text(src, encoding='utf-8')
print('wrote verify_tmp.html')

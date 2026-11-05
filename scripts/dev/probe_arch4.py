import pathlib
t=pathlib.Path('assets/template.html').read_text(encoding='utf-8')
for p in [1507797,1131210,849728]:
    print('=== POS',p,'===')
    print(t[p:p+2200].replace('\n',' | ')[:2400])
    print()

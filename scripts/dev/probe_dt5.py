import pathlib
t = pathlib.Path('assets/template.html').read_text(encoding='utf-8')
i = t.find('case"diningTable"')
# kv version is second occurrence - find all
idxs=[]
s=0
while True:
    j=t.find('case"diningTable"',s)
    if j<0: break
    idxs.append(j); s=j+1
print(idxs)
for j in idxs:
    print('==== @',j)
    print(repr(t[j-0:j+1200]))

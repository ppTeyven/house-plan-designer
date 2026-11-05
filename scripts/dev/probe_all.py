import pathlib
t=pathlib.Path('assets/template.html').read_text(encoding='utf-8')
def show(key, pre=200, post=900):
    i=t.find(key)
    print('===',key, i, 'count', t.count(key))
    if i>=0:
        print(t[i-pre:i+post].replace('\n',' ')[:1400])
        print()
for k in ['w.rotation.x=-.13', 'case"bed"', 'case"diningTable"', 'case"chair"', 'case"coffeeTable"', 'case"sofa"', 'function kv(n,e){']:
    show(k)

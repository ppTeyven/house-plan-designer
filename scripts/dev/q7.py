t = open('assets/template.html', encoding='utf-8').read()
def seg(a, n=2500):
    i = t.find(a)
    print('### '+a+' idx='+str(i))
    print(t[i:i+n].replace('\n',' ')[:n])
    print()
for a in ['Hp=', 'const Wp', 'Xc=', 'function Gm(', 'function Wi(', 'function en(', 'function $e(', 'function Vi(', 'function Lr(', 'function P1(']:
    try: seg(a, 1600)
    except Exception as e: print(a, e)

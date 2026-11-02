t = open('assets/template.html', encoding='utf-8').read()
import re
def show(name, pat, pre=200, ctx=1000):
    i = t.find(pat)
    print('===', name, 'idx', i, 'count', t.count(pat))
    if i < 0:
        print('NOT FOUND'); print(); return
    print(t[max(0,i-pre):i+ctx].replace('\n',' ')[:2400]); print()
show('Xc', 'Xc', 0, 0)
# find Xc definition: const Xc= or let Xc or Xc:
for m in re.finditer(r'.{0,60}Xc[=:]', t)[:0] if False else []:
    pass
idxs = [m.start() for m in re.finditer(r'Xc', t)][:30]
print('Xc occurrences:', len(list(re.finditer(r'Xc', t))))
# print contexts of first few distinct
seen=set()
for m in re.finditer(r'Xc', t):
    s=max(0,m.start()-80); seg=t[s:m.start()+120].replace('\n',' ')
    key=seg[40:120]
    if key in seen: continue
    seen.add(key)
    print(repr(seg)[:300])
    if len(seen)>25: break
print()
show('en-def', 'function en(', 0, 600)
show('Ye-def', 'function Ye(', 0, 500)
show('Hp-def', 'function Hp(', 0, 500)
show('Wp-def', 'function Wp(', 0, 500)
show('Yc-def', 'function Yc(', 0, 600)
show('nI-def', 'function nI(', 0, 600)
show('KB-def', 'function KB(', 0, 800)
show('x4-def', 'function x4(', 0, 800)
show('rd-def', 'function rd(', 0, 800)
show('Qc-def', 'function Qc(', 0, 600)
show('bw-assign', 'bw=', 100, 300)

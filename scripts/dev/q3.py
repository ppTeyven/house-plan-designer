t = open('assets/template.html', encoding='utf-8').read()
import re
pats = ['async function rh','function bw(','__fade','modeFade','smart-mode','lt=','qR','Oa=new']
for p in pats:
    idxs = [m.start() for m in re.finditer(re.escape(p), t)][:5]
    print(p, '->', idxs)
print('len', len(t))

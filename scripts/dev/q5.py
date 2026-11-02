t = open('assets/template.html', encoding='utf-8').read()
import re
def dump(name, pat, pre=200, ctx=3000):
    i = t.find(pat)
    print('===', name, i)
    if i < 0:
        print('NOT FOUND'); return
    s = t[max(0,i-pre):i+ctx].replace('\n',' ')
    print(s[:2800]); print()
dump('Hp/Wp', 'function Hp(', 0, 1200)
dump('Wp2', 'function Wp(', 0, 1200)
dump('Hp2', 'const Hp=', 0, 800)
dump('Bv_qR', 'Zh.push', 600, 600)
dump('ja_full', 'function ja(', 0, 2600)
dump('KB', 'function KB(', 0, 1200)
dump('Qc', 'function Qc(', 0, 1200)
dump('zB_full', 'function zB(', 0, 3600)
dump('bw_assign', 'bw=', 100, 400)
dump('smartBtn', 'smartBtn', 200, 800)

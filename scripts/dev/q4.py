t = open('assets/template.html', encoding='utf-8').read()
import re
def dump(pat, pre=300, ctx=5000, tag=''):
    i = t.find(pat)
    print(tag or pat, 'idx', i)
    if i < 0: return
    open('scripts/dev/dump_%s.txt' % re.sub(r'[^a-z0-9]+','_', (tag or pat).lower())[:40], 'w', encoding='utf-8').write(t[max(0,i-pre):i+ctx])
    print(t[max(0,i-pre):i+ctx].replace('\n',' ')[:2600])
    print()
dump('async function rh', 0, 5200, 'rh')
dump('function __fade', 0, 900, 'fade')
dump('modeFade', 800, 900, 'modefade_css')
dump('let lt=', 0, 600, 'lt_def')
dump('N0=', 200, 600, 'N0_def')
dump('function xw(', 0, 2600, 'xw_x4')

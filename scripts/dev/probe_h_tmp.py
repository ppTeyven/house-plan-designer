t = open('assets/template.html', encoding='utf-8').read()
import re
def dump(name, pat, length=2600):
    i = t.find(pat)
    print('===', name, 'idx', i)
    if i < 0:
        print('NOT FOUND'); print(); return
    print(t[i:i+length].replace('\n',' ')[:length]); print()
dump('dx', 'function dx(n){', 2600)
dump('JL', 'function JL(n){', 1400)
dump('Uv-reg', 'function Uv(n){', 300)
# hn variants
for pat in ['hn=', 'hn =', 'hn(', 'const hn', 'let hn', 'hn:']:
    c = t.count(pat)
    if c: print(pat, 'count', c)
print()
i = t.find('sceneRefs')
print('sceneRefs ctx:', t[max(0,i-600):i+600].replace('\n',' ')[:1400])

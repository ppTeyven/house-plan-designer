t = open('assets/template.html', encoding='utf-8').read()
import re
def show(name, pat, pre=200, ctx=1600):
    i = t.find(pat)
    print('===', name, 'idx', i, 'count', t.count(pat))
    if i < 0:
        print('NOT FOUND'); print(); return
    print(t[max(0,i-pre):i+ctx].replace('\n',' ')[:3000]); print()
print('--- all .enabled= writers ---')
for m in re.finditer(r'\.enabled\s*=\s*[^,;]{1,30}', t):
    s=max(0,m.start()-140)
    print(repr(t[s:m.end()+40].replace('\n',' '))[:380])
print()
show('rd-full', 'function rd(', 0, 900)
show('vw-def', 'function vw(', 0, 700)
show('hn-def', 'function hn(', 0, 700)
show('Xd-def', 'function Xd(', 0, 600)
show('c3d-pointerdown', 'setPointerCapture(n.pointerId)', 0, 0)

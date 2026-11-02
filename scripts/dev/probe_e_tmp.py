t = open('assets/template.html', encoding='utf-8').read()
import re
def show(name, pat, pre=200, ctx=1000):
    i = t.find(pat)
    print('===', name, 'idx', i, 'count', t.count(pat))
    if i < 0:
        print('NOT FOUND'); print(); return
    print(t[max(0,i-pre):i+ctx].replace('\n',' ')[:2400]); print()
# who writes Tt.enabled ?
print('--- Tt.enabled writers ---')
for m in re.finditer(r'Tt\.enabled\s*=\s*[^,;]+', t):
    s=max(0,m.start()-160)
    print(repr(t[s:m.end()+80].replace('\n',' '))[:340])
print()
show('hn-def', 'function hn(', 0, 900)
show('Yc-def2', 'Yc=', 0, 600)
show('walkCtl-show', 'walkCtl', 200, 700)
show('fphint-show', 'fphint', 200, 500)
show('pano-open', 'function openPano', 0, 800)
show('xr-css', '#xr-btn', 200, 600)
show('camReset', 'camReset', 200, 400)
show('controls-enable', 'controls.enabled', 200, 400)
show('autoRotate', 'autoRotate', 200, 400)

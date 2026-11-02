t = open('assets/template.html', encoding='utf-8').read()
import re
def show(tag, pat, pre=200, ln=2000):
    i = t.find(pat)
    print('###', tag, 'idx=', i)
    if i < 0:
        print('NOT FOUND'); print(); return
    print(t[max(0,i-pre):i+ln].replace('\n',' ')[:2800]); print()
show('sm-pins-css', '.sm-pins', 0, 1600)
show('sm-pin-btn', 'sm-pin', 0, 900)
show('tz-def', 'function tz(', 0, 2200)
show('QB-def', 'function QB(', 0, 600)
show('ad-click', 'ad.addEventListener', 0, 600)
show('pins-onclick', 'smPins', 0, 600)
show('rz-def', 'function rz(', 0, 1600)
show('qB-def', 'function qB(', 0, 1600)
show('B-def', 'function $B(', 0, 1600)
show('iz-def', 'function iz(', 0, 1200)
show('sz-def', 'function sz(', 0, 1200)

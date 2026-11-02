t = open('assets/template.html', encoding='utf-8').read()
import re
def ctx(pat, pre=400, ln=2500):
    i = t.find(pat)
    print('===', pat, i)
    if i<0: return
    print(t[max(0,i-pre):i+ln].replace('\n',' ')[:3200])
    print()
ctx('zB({', 200, 2500)
ctx('zB(', 200, 1500)
ctx('1932588', 0, 0)
i=1932588
print(t[i-600:i+1500].replace('\n',' ')[:2200]); print()
ctx('"3d"', 300, 800)
ctx('smartBtn', 500, 1200)
ctx('id="smartBtn"', 0, 600)
ctx('he("#smartBtn")', 300, 800)
ctx('function Hv(', 0, 900)
ctx('function uo(', 0, 900)
ctx('function of(', 0, 900)
ctx('let Oa', 0, 400)
ctx('qR(', 400, 900)

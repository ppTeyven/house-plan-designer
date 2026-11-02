t = open('assets/template.html', encoding='utf-8').read()
def show(tag, idx, pre=300, ln=2200):
    print('###', tag, 'idx=', idx)
    if idx is None or idx < 0:
        print('NOT FOUND'); print(); return
    print(t[max(0,idx-pre):idx+ln].replace('\n',' ')[:3000]); print()
import re
show('hn-def', 1394098, 0, 900)
show('FB-def', t.find('function FB('), 0, 1500)
show('_w-def', t.find('function _w('), 0, 1500)
show('Qc-def', t.find('function Qc('), 0, 2500)
show('H1-def', 1906340, 0, 600)
show('KB-def', t.find('function KB('), 0, 2600)
show('lz-def', t.find('function lz('), 0, 2000)
show('smart-css', t.find('.smart-ui{'), 0, 2600)
show('smpins-css', t.find('.sm-pins'), 0, 900)
show('smcard-css', t.find('.sm-card'), 0, 900)

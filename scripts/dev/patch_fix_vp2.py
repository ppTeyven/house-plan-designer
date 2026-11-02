# -*- coding: utf-8 -*-
import sys
p = 'assets/template.html'
t = open(p, encoding='utf-8').read()
start = t.find('wi({target:i,r:.01')
marker = '__ZOease)}function Ns'
mi = t.find(marker)
print('start', start, 'marker', mi)
if start < 0 or mi < 0:
    sys.exit(1)
C = 're.active=!0,Tt.enabled=!1,C0.visible=!0;try{skyDim()}catch(e){}$e()&&gs(),Yc();try{skyFade(1)}catch(e){}'
inner = '()=>{' + C + '}'
wffin = '__walkFinish(' + inner + ')'
outer = '()=>{' + wffin + '}'
new_wi = 'wi({target:i,r:.01,p:s.phi,t:s.theta},1300,' + outer + ',__ZOease)'
end = mi + len('__ZOease)')
old_seg = t[start:end]
print('OLD seg tail:', repr(old_seg[-60:]))
t = t[:start] + new_wi + t[end:]
print('NEW seg tail:', repr(t[start:start+len(new_wi)][-60:]))
open(p, 'w', encoding='utf-8').write(t)
print('vp fix OK, new_wi len', len(new_wi))

# -*- coding: utf-8 -*-
import sys
p = 'assets/template.html'
t = open(p, encoding='utf-8').read()
old = ('m0=!0,window.__bvStage="m0",window.__bvErr="",'
       'try{gs()}catch(e){window.__bvErr+="gs:"+String((e&&e.stack)||e).slice(0,1200)},'
       'window.__bvStage="gs",'
       'try{Is()}catch(e){window.__bvErr+="|Is:"+String((e&&e.stack)||e).slice(0,1200)},'
       'window.__bvStage="Is",'
       'try{ao(uo())}catch(e){window.__bvErr+="|ao:"+String((e&&e.stack)||e).slice(0,1200)},'
       'window.__bvStage="ao",window._fpsMon={f:0,t:performance.now(),fps:0}')
new = ('m0=!0;window.__bvStage="m0";window.__bvErr="";'
       '(function(){try{gs()}catch(e){window.__bvErr+="gs:"+String((e&&e.stack)||e).slice(0,1200)}})();'
       'window.__bvStage="gs";'
       '(function(){try{Is()}catch(e){window.__bvErr+="|Is:"+String((e&&e.stack)||e).slice(0,1200)}})();'
       'window.__bvStage="Is";'
       '(function(){try{ao(uo())}catch(e){window.__bvErr+="|ao:"+String((e&&e.stack)||e).slice(0,1200)}})();'
       'window.__bvStage="ao";window._fpsMon={f:0,t:performance.now(),fps:0}')
c = t.count(old)
print('count', c)
if c != 1:
    sys.exit(1)
t = t.replace(old, new)
open(p, 'w', encoding='utf-8').write(t)
print('diagfix OK')

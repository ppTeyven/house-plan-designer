# -*- coding: utf-8 -*-
import sys
p = 'assets/template.html'
t = open(p, encoding='utf-8').read()
patches = []
NL = '\n'
# Fix A: Aw must not throw when #loading3d div is missing (it is missing in current file)
old_aw = 'Bv(he("#c3d"),b8),he("#loading3d").style.display="none",fu=!1)}'
new_aw = 'Bv(he("#c3d"),b8),he("#loading3d")&&(he("#loading3d").style.display="none"),fu=!1)}'
patches.append(('Aw_guard', old_aw, new_aw))
# Debug B: stage markers around Bv tail so we can see which sub-step throws
old_bv = 'm0=!0,gs(),Is(),ao(uo()),window._fpsMon={f:0,t:performance.now(),fps:0}'
new_bv = ('m0=!0,window.__bvStage="m0",window.__bvErr="",'
          'try{gs()}catch(e){window.__bvErr+="gs:"+String((e&&e.stack)||e).slice(0,1200)},'
          'window.__bvStage="gs",'
          'try{Is()}catch(e){window.__bvErr+="|Is:"+String((e&&e.stack)||e).slice(0,1200)},'
          'window.__bvStage="Is",'
          'try{ao(uo())}catch(e){window.__bvErr+="|ao:"+String((e&&e.stack)||e).slice(0,1200)},'
          'window.__bvStage="ao",window._fpsMon={f:0,t:performance.now(),fps:0}')
patches.append(('Bv_stage', old_bv, new_bv))
fails = []
for name, old, new in patches:
    c = t.count(old)
    if c != 1:
        fails.append((name, c))
        continue
    t = t.replace(old, new)
if fails:
    print('ANCHOR FAIL:', fails)
    sys.exit(1)
open(p, 'w', encoding='utf-8').write(t)
print('patched OK:', len(patches))

# -*- coding: utf-8 -*-
cur = open('assets/template.html', encoding='utf-8').read()
bak = open('assets/template.backup.html', encoding='utf-8').read()
print('cur len', len(cur), 'bak len', len(bak))
for pat in ['loading3d', '_fpsMon', 'function Bv(', 'Oa.position.set', '__ZOease', 'function wi(n,e,t,f)']:
    import re
    print(pat, 'cur=', cur.count(pat), 'bak=', bak.count(pat))
# find first diff chunk
import difflib
sm = difflib.SequenceMatcher(None, bak[:2000000], cur[:2000000], autojunk=False)
for tag,i1,i2,j1,j2 in sm.get_opcodes()[:40]:
    if tag!='equal':
        print(tag, 'bak[%d:%d] cur[%d:%d]'%(i1,i2,j1,j2))
        print('BAK:', repr(bak[i1:i1+400])[:600])
        print('CUR:', repr(cur[j1:j1+400])[:600])
        print()
        if j1>50000:
            break

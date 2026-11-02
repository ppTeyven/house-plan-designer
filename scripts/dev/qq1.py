import re
t = open('assets/template.html', encoding='utf-8').read()
def get(a, b=None):
    i = t.find(a)
    if i < 0:
        print(a, 'NOT FOUND'); return
    if b is None:
        print(a, 'idx', i, 'len-remaining', len(t)-i)
        print(t[i:i+6000].replace('\n',' ')[:6000])
    else:
        j = t.find(b, i)
        print(a, 'idx', i, 'end', j, 'span', (j-i) if j>0 else -1)
        if j>0:
            print(t[i:j+len(b)].replace('\n',' ')[:8000])
    print('\n---\n')
# 1. Ua full: from async function Ua to next "window.addEventListener(\"keydown\""
get('async function Ua(n){/*__viewTransV2*/', 'window.addEventListener("keydown"')
# 2. Vp full
get('function Vp(', 'function Ns(')

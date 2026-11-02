# -*- coding: utf-8 -*-
cur = open('assets/template.html', encoding='utf-8').read()
bak = open('assets/template.backup.html', encoding='utf-8').read()
for name, t in [('CUR',cur),('BAK',bak)]:
    i = t.find('loading3d')
    print(name, 'count', t.count('loading3d'))
    while i>=0 and i< len(t):
        print(name, repr(t[max(0,i-200):i+300])[:500])
        print('---')
        i = t.find('loading3d', i+1)
        if i>1500000:
            break
print('---DIV check---')
for name, t in [('CUR',cur),('BAK',bak)]:
    j = t.find('<div class="loading3d"')
    print(name, 'div idx', j)
    if j>=0:
        print(repr(t[j-200:j+300])[:600])

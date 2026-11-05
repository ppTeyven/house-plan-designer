import os, re, glob

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
TEX = os.path.join(ROOT, 'assets', 'furnlib', 'tex')

files = os.listdir(TEX)
sets = {}
for f in files:
    if not f.endswith('.jpg'):
        continue
    base = f[:-4]
    for ch in ('col', 'nor', 'rough', 'ao', 'disp'):
        if base.endswith('_' + ch):
            sets.setdefault(base[:-(len(ch) + 1)], set()).add(ch)

print('%-34s %s' % ('texture set', 'channels'))
missing = []
for k in sorted(sets):
    have = sets[k]
    need = {'col', 'nor', 'rough', 'ao'}
    miss = need - have
    flag = '' if not miss else '   <== MISSING: ' + ','.join(sorted(miss))
    print('%-34s %s%s' % (k, ','.join(sorted(have)), flag))
    if miss:
        missing.append((k, sorted(miss)))

print()
print('sets missing AO:', [m[0] for m in missing if m[1] == ['ao']])
print('total sets:', len(sets))

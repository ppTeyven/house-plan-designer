import os
import re

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
p = os.path.join(ROOT, 'assets', 'template.html')
s = open(p, encoding='utf-8').read()

for needle in ['L("#e8e4dc"', '"#222"', '"#8a6a4d"', 'L("#bcd8ea"', '_s=()=>']:
    print('===== %s ===== count=%d' % (needle, s.count(needle)))
    for m in re.finditer(re.escape(needle), s):
        i = m.start()
        print('  %d  ...%s...' % (i, s[max(0, i - 220):i + 200].replace('\n', ' | ')))
    print()

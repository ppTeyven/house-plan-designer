import re, sys, os
s = open(r'assets/template.html', encoding='utf-8').read()
pat = re.compile(r'''["']([a-zA-Z0-9_\-]+/[a-zA-Z0-9_\-./]*\.(?:json|glb|jpg|png|hdr|ktx2|bin))["']''')
paths = sorted(set(pat.findall(s)))
for p in paths:
    print(p)
print('TOTAL', len(paths))

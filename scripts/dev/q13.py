t = open('assets/template.html', encoding='utf-8').read()
import re
# 1. hn definition?
for pat in ['hn=', 'hn =', 'const hn', 'let hn', 'var hn', ' hn=', '(hn=', ',hn=', ';hn=']:
    print(repr(pat), '->', [m.start() for m in re.finditer(re.escape(pat), t)][:6])
print()
for pat in ['FB=', 'function FB', '_w=', 'function _w', 'H1=', 'H1 =', 'Zr=', 'function Zr', 'W5=', 'function W5', 'Qc=', 'function Qc']:
    print(repr(pat), '->', [m.start() for m in re.finditer(re.escape(pat), t)][:4])
print()
# hn call sites
print('hn( calls ->', [m.start() for m in re.finditer(r'hn\(\)', t)][:20])
print()
# Nu/Ou positioning
for m in re.finditer(r'Nu\.position[^,;]*[,;]', t):
    s = m.start(); print('Nu:', t[max(0,s-120):s+200].replace('\n',' ')[:330])
for m in re.finditer(r'Ou\.position[^,;]*[,;]', t):
    s = m.start(); print('Ou:', t[max(0,s-120):s+200].replace('\n',' ')[:330])

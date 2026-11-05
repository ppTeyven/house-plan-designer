import os

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
p = os.path.join(ROOT, 'assets', 'template.html')
s = open(p, encoding='utf-8').read()

for label, needle, back, fwd in [
    ('slider-door frame', 'const W=new ht,B=new Me(new ot(O,G-.01,.04),s);', 40, 200),
    ('garage door', 'k.type==="garage"', 40, 700),
    ('bay sill', 'u/2+.03),L("#ece8e1",.3));', 260, 120),
    ('bay side', 'new ot(O+.12,Y,B),L("#e8e4dc",.5));', 260, 120),
]:
    i = s.find(needle)
    print('===== %s =====  count=%d at %d' % (label, s.count(needle), i))
    if i >= 0:
        print(repr(s[max(0, i - back):i + len(needle) + fwd]))
    print()

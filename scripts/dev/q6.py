t = open('assets/template.html', encoding='utf-8').read()
import re
for pat in ['Hp=', 'Wp=', 'function Hp', 'function Wp', 'const Hp', 'const Wp', 'Xc=', 'function Xc', 'Gm=', 'function Gm', 'function Wi(', 'function en(', 'function $e(', 'function Vi(', 'function Lr(', 'function P1(', 'function Je(', 'function Zc(', 'function Gh(', 'function Ns(', 'smartBtn', 'smExit', 'smPins', 'smCard', '.smart-ui']:
    idxs = [m.start() for m in re.finditer(re.escape(pat), t)][:3]
    print(pat, '->', idxs)

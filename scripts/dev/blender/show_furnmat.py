import os

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
p = os.path.join(ROOT, 'assets', 'template.html')
s = open(p, encoding='utf-8').read()

i = s.find('m.name="F_"+role;')
print('anchor at', i)
print(s[max(0, i - 700):i + 1000])

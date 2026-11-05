import os, re, sys, io

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
p = os.path.join(ROOT, 'assets', 'template.html')
s = open(p, encoding='utf-8').read()

i = s.find('function sx(){')
# find next top-level "function " after i
j = s.find('\nfunction ', i + 20)
if j < 0:
    j = i + 40000
body = s[i:j]
print('sx spans', i, j, 'len', j - i)

out = io.StringIO()
out.write('--- L( color materials in sx ---\n')
for m in re.finditer(r'L\(\s*"#[0-9a-fA-F]{3,6}"[^)]{0,80}\)', body):
    out.write('  %6d  %s\n' % (m.start(), m.group(0)))

out.write('\n--- new Zt( in sx ---\n')
for m in re.finditer(r'new Zt\(\{[^}]{0,160}\}', body):
    out.write('  %6d  %s\n' % (m.start(), m.group(0)[:150]))

out.write('\n--- __ARCH_MAT uses in sx ---\n')
for m in re.finditer(r'__ARCH_MAT\.\w+', body):
    out.write('  %6d  %s\n' % (m.start(), m.group(0)))

open('_audit_sx.txt', 'w', encoding='utf-8').write(out.getvalue())
print(out.getvalue()[:6000])

import os, re, io

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
p = os.path.join(ROOT, 'assets', 'template.html')
s = open(p, encoding='utf-8').read()

SX = s.find('function sx(){')
out = io.StringIO()

TARGETS = [
    '#f3f1ec', '#3a3f47', '#9aa3ad', '#e8590c', '#5b626c', '#c9a57c', '#474c55',
    '#ece8e1', '#e8e4dc', '#c7ccd2', '#c8ced4', '#b9bec6', '#9aa1a8',
    '#d9dcdf', '#b9bec4', '#cfd3d7', '#d9bf9c', '#8f969f', '#d9d4cb',
    '#cfe2ee', '#f1efea', '#ebe8e2', '#aeb6bd', '#6b4a32', '#e8a700',
    '#f1f1ef', '#2b2e33', '#c9a46a', '#fbfbfa', '#d9d9d6', '#f4f4f2',
    '#3a3d42', '#f7f7f5', '#9aa1a8', '#1f2226', '#d6dadf', '#dfe4e9',
    '#6f6a64', '#f2f2f0', '#ffffff', '#1c7ed6', '#d9480f', '#e03131',
]

# find all L("...") occurrences inside sx body (up to ~1955000 which is end of sx)
END = 1955000
for m in re.finditer(r'L\(\s*"#[0-9a-fA-F]{3,6}"', s[SX:END]):
    off = SX + m.start()
    hexv = m.group(0)[3:-1]
    if hexv not in TARGETS:
        continue
    # find end of the L( call
    depth = 0
    k = off
    while k < len(s):
        if s[k] == '(':
            depth += 1
        elif s[k] == ')':
            depth -= 1
            if depth == 0:
                break
        k += 1
    call = s[off:k + 1]
    out.write('--- %d  %s\n' % (off, call))
    out.write('    ctx: ...%s...\n' % s[max(0, off - 190):off].replace('\n', ' | '))
    out.write('\n')

open('_audit_L.txt', 'w', encoding='utf-8').write(out.getvalue())
print('lines', out.getvalue().count('\n'))

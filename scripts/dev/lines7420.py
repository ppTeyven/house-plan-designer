import pathlib, re
t = pathlib.Path('assets/template.html').read_text(encoding='utf-8')
ms = list(re.finditer(r'<script(?P<attrs>[^>]*)>(?P<code>.*?)</script>', t, re.S))
blocks = [(len(x.group('code')), x.group('code')) for x in ms if len(x.group('code').strip()) > 100]
blocks.sort(key=lambda x: x[0])
code = blocks[-1][1]
lines = code.splitlines()
print('total lines', len(lines))
for i in range(7410, 7430):
    if 0 <= i < len(lines):
        print(i+1, repr(lines[i][:600]))
pathlib.Path('scripts/dev/tmp_code.mjs').write_text(code, encoding='utf-8')
print('wrote tmp')

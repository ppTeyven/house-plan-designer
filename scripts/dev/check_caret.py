import pathlib, re, subprocess, tempfile, os
t = pathlib.Path('assets/template.html').read_text(encoding='utf-8')
ms = list(re.finditer(r'<script(?P<attrs>[^>]*)>(?P<code>.*?)</script>', t, re.S))
blocks = [(len(x.group('code')), x.group('code')) for x in ms if len(x.group('code').strip()) > 100]
blocks.sort(key=lambda x: x[0])
code = blocks[-1][1]
fd, fp = tempfile.mkstemp(suffix='.mjs')
os.write(fd, code.encode('utf-8')); os.close(fd)
r = subprocess.run(['node', '--check', fp], capture_output=True)
err = r.stderr.decode('utf-8', errors='replace')
print('rc', r.returncode)
lines = err.splitlines()
print('nlines', len(lines))
for i, ln in enumerate(lines):
    s = ln.strip()
    if s.startswith('^') or 'SyntaxError' in ln or 'tmp' in ln and '.mjs' in ln:
        print(i, repr(ln[:300]))
# print caret context: find line with only ^^^ and spaces
for i, ln in enumerate(lines):
    st = ln.strip()
    if st and set(st) <= set('^ ') and '^' in st:
        print('CARET at', i, 'col~', ln.index('^'))
        for j in range(max(0,i-3), min(len(lines), i+4)):
            print(j, repr(lines[j][:200]))
os.unlink(fp)

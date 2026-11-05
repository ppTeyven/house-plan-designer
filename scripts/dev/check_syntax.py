import pathlib, re, subprocess, tempfile, os
p = pathlib.Path('assets/template.html')
t = p.read_text(encoding='utf-8')
# find all <script ...>...</script> blocks, pick the largest (main bundle)
blocks = []
for m in re.finditer(r'<script(?P<attrs>[^>]*)>(?P<code>.*?)</script>', t, re.S):
    attrs = m.group('attrs')
    code = m.group('code')
    if len(code.strip()) < 100:
        continue
    blocks.append((len(code), attrs[:120], code))
print('blocks', len(blocks), [b[0] for b in blocks])
print('attrs', [b[1] for b in blocks])
# check largest block
blocks.sort(key=lambda x: x[0])
code = blocks[-1][2]
print('main len', len(code))
fd, fn = tempfile.mkstemp(suffix='.mjs')
os.write(fd, code.encode('utf-8'))
os.close(fd)
r = subprocess.run(['node', '--check', fn], capture_output=True, text=True)
print('node --check exit', r.returncode)
print('stdout', (r.stdout or '')[:2000])
print('stderr', (r.stderr or '')[:3000])
os.unlink(fn)

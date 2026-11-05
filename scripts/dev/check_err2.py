import pathlib, re, subprocess, tempfile, os
for fn in ['assets/template.bak_rebuild0', 'assets/template.html']:
    t = pathlib.Path(fn).read_text(encoding='utf-8')
    ms = list(re.finditer(r'<script(?P<attrs>[^>]*)>(?P<code>.*?)</script>', t, re.S))
    blocks = [(len(x.group('code')), x.group('code')) for x in ms if len(x.group('code').strip()) > 100]
    blocks.sort(key=lambda x: x[0])
    code = blocks[-1][1]
    fd, fp = tempfile.mkstemp(suffix='.mjs')
    os.write(fd, code.encode('utf-8')); os.close(fd)
    r = subprocess.run(['node', '--check', fp], capture_output=True)
    err = r.stderr.decode('utf-8', errors='replace')
    lines = err.strip().splitlines()
    print('####', fn, 'rc', r.returncode)
    for ln in lines[:3]:
        print('HEAD:', ln[:400])
    for ln in lines[-6:]:
        print('TAIL:', ln[:400])
    os.unlink(fp)

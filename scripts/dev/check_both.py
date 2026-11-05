import pathlib, re, subprocess, tempfile, os
def getcode(text):
    ms = list(re.finditer(r'<script(?P<attrs>[^>]*)>(?P<code>.*?)</script>', text, re.S))
    blocks = [(len(x.group('code')), x.group('code')) for x in ms if len(x.group('code').strip()) > 100]
    blocks.sort(key=lambda x: x[0])
    return blocks[-1][1]
def check(code, label):
    fd, fp = tempfile.mkstemp(suffix='.mjs')
    os.write(fd, code.encode('utf-8')); os.close(fd)
    r = subprocess.run(['node', '--check', fp], capture_output=True)
    err = r.stderr.decode('utf-8', errors='replace')
    print('####', label, 'rc', r.returncode, 'len', len(code))
    i = err.find('SyntaxError')
    print(err[max(0,i-1500):i+500][:2500])
    os.unlink(fp)
import subprocess as sp
head = sp.run(['git', 'show', 'HEAD:assets/template.html'], capture_output=True).stdout.decode('utf-8')
check(getcode(head), 'HEAD-version')
cur = pathlib.Path('assets/template.html').read_text(encoding='utf-8')
check(getcode(cur), 'WORKTREE-version')

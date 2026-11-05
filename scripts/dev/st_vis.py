import pathlib, re, subprocess, tempfile, os
def getcode(text):
    ms = list(re.finditer(r'<script(?P<attrs>[^>]*)>(?P<code>.*?)</script>', text, re.S))
    blocks = [(len(x.group('code')), x.group('code')) for x in ms if len(x.group('code').strip()) > 100]
    blocks.sort(key=lambda x: x[0])
    return blocks[-1][1]
def check(code):
    fd, fp = tempfile.mkstemp(suffix='.mjs')
    os.write(fd, code.encode('utf-8')); os.close(fp)
    r = subprocess.run(['node','--check',fp], capture_output=True)
    err = r.stderr.decode('utf-8',errors='replace')
    os.unlink(fp)
    if r.returncode:
        i=err.find('SyntaxError')
        return False, err[max(0,i-500):i+200][:1000]
    return True, ''
head = subprocess.run(['git','show','HEAD:assets/template.html'], capture_output=True).stdout.decode('utf-8')
ok,msg = check(getcode(head))
print('HEAD', ok, msg[:200])
# current worktree info
cur = pathlib.Path('assets/template.html').read_text(encoding='utf-8')
print('cur len', len(cur), 'head len', len(head))

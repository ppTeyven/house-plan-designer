import pathlib,re,subprocess,tempfile,os
def check(fn):
    t=pathlib.Path(fn).read_text(encoding='utf-8')
    ms=list(re.finditer(r'<script(?P<attrs>[^>]*)>(?P<code>.*?)</script>',t,re.S))
    blocks=[(len(x.group('code')),x.group('code')) for x in ms if len(x.group('code').strip())>100]
    blocks.sort(key=lambda x:x[0])
    code=blocks[-1][1]
    fd,fp=tempfile.mkstemp(suffix='.mjs')
    os.write(fd,code.encode('utf-8')); os.close(fd)
    r=subprocess.run(['node','--check',fp],capture_output=True)
    out=r.stdout.decode('utf-8',errors='replace')
    err=r.stderr.decode('utf-8',errors='replace')
    print(fn,'exit',r.returncode,'codelen',len(code))
    print('ERR_HEAD:',err[:3000])
    os.unlink(fp)
check('assets/template.bak_rebuild0')
check('assets/template.html')

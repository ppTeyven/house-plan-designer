import pathlib,re,subprocess,tempfile,os
t=pathlib.Path('assets/template.html').read_text(encoding='utf-8')
ms=list(re.finditer(r'<script(?P<attrs>[^>]*)>(?P<code>.*?)</script>',t,re.S))
blocks=[(len(x.group('code')),x.group('code')) for x in ms if len(x.group('code').strip())>100]
blocks.sort(key=lambda x:x[0])
code=blocks[-1][1]
fd,fp=tempfile.mkstemp(suffix='.mjs')
os.write(fd,code.encode('utf-8')); os.close(fd)
r=subprocess.run(['node','--check',fp],capture_output=True)
err=r.stderr.decode('utf-8',errors='replace')
print('exit',r.returncode)
lines=err.splitlines()
print('NUMLINES',len(lines))
for ln in lines[-12:]:
    print(ln[:600])
os.unlink(fp)
# show patched regions
for key in ['N(t,i-.04,.018,.018', 'N(n,i-.06,.014,.014']:
    p=t.find(key)
    print('REGION',key,p)
    if p>0:
        print(t[p-300:p+400].replace('\n',' | ')[:900])

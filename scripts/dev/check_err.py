import pathlib,re,subprocess,tempfile,os
t=pathlib.Path('assets/template.html').read_text(encoding='utf-8')
m=list(re.finditer(r'<script(?P<attrs>[^>]*)>(?P<code>.*?)</script>',t,re.S))
blocks=[(len(x.group('code')),x.group('code')) for x in m if len(x.group('code').strip())>100]
blocks.sort(key=lambda x:x[0])
code=blocks[-1][1]
fd,fn=tempfile.mkstemp(suffix='.mjs')
os.write(fd,code.encode('utf-8')); os.close(fd)
r=subprocess.run(['node','--check',fn],capture_output=True)
out=r.stdout.decode('utf-8',errors='replace')
err=r.stderr.decode('utf-8',errors='replace')
print('exit',r.returncode)
print('ERR_TAIL:',err[-4000:])
print('OUT_TAIL:',out[-2000:])
os.unlink(fn)

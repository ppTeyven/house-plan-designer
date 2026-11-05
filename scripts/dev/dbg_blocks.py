import pathlib,re,subprocess,tempfile,os
for fn in ['assets/template.html','assets/template.bak_rebuild0']:
    t=pathlib.Path(fn).read_text(encoding='utf-8')
    ms=list(re.finditer(r'<script(?P<attrs>[^>]*)>(?P<code>.*?)</script>',t,re.S))
    blocks=[(len(x.group('code')),x.group('attrs')[:80]) for x in ms if len(x.group('code').strip())>100]
    print(fn,'nblocks',len(blocks),[b[0] for b in blocks], [b[1] for b in blocks])
print('---current tail---')
t=pathlib.Path('assets/template.html').read_text(encoding='utf-8')
print(repr(t[-600:]))

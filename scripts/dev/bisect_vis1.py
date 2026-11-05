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
    if r.returncode:
        i = err.find('SyntaxError')
        print('CTX:', repr(err[max(0,i-600):i+200]))
    os.unlink(fp)

head = subprocess.run(['git', 'show', 'HEAD:assets/template.html'], capture_output=True).stdout.decode('utf-8')
check(getcode(head), 'HEAD-clean')

reps = [
 ('const w=ft(t,x-.025,Math.max(.22,o-.58),.16,v,.52,-l+.29,h,.06,{puff:[.006,.006,.025]});w.rotation.x=-.13}if(n.type==="sofa"&&i>1.3)',
  'const w=ft(t,x-.025,Math.max(.22,o-.58),.16,v,.52,-l+.29,h,.06,{puff:[.006,.006,.025]});w.rotation.x=-.13;if(y>1){const _g=(x-.015)/y;for(let _k=1;_k<y;_k++)N(t,.012,.1,s-.28,-r+g+_g*_k,.4,.11,L(we(a,-.35),.8),!1)}}if(n.type==="sofa"&&i>1.3)'),
 ('if(n.type==="sofa"&&i>1.3)for(const b of[-1,1])ft(t,.42,.4,.09,b*(r-(b<0?g:m)-.3),.52,-l+.42,L(we(a,b<0?-.18:.12),.95),.04,{puff:[.01,.01,.035]}).rotation.set(-.3,b*.25,b*.12);break}case"coffeeTable"',
  'if(n.type==="sofa"&&i>1.3)for(const b of[-1,1])ft(t,.42,.4,.09,b*(r-(b<0?g:m)-.3),.52,-l+.42,L(b<0?"#c96f2e":"#3b6ea5",.95),.04,{puff:[.01,.01,.035]}).rotation.set(-.3,b*.25,b*.12);break}case"coffeeTable"'),
 ('ft(t,i+.06,.03,s*.22,0,.575,l-s*.14,L(a,.95),.012),ft(t,i+.06,.32,.03,0,.29,l+.005,L(a,.95),.012);break}case"nightstand"',
  'ft(t,i+.06,.03,s*.22,0,.575,l-s*.14,L(a,.95),.012),ft(t,i+.06,.16,.062,0,.56,l-s*.14,L("#c96f2e",.9),.014),ft(t,i+.06,.32,.03,0,.29,l+.005,L(a,.95),.012);break}case"nightstand"'),
 ('N(t,i-.18,.07,s-.18,0,o-.115,0,L(we(a,-.3),.55)),la(t,.07,.05,o+.2,.02,"#7aa36a");break;case"chair"',
  'N(t,i-.18,.07,s-.18,0,o-.115,0,L(we(a,-.3),.55)),N(t,.44,.006,s-.24,0,o+.028,0,L("#c96f2e",.9),!1),N(t,i*.32,.004,.24,-r+i*.24,o+.028,-l+s*.24,L("#f4f1ea",.9),!1),N(t,i*.32,.004,.24,r-i*.24,o+.028,-l+s*.24,L("#f4f1ea",.9),!1),la(t,.07,.05,o+.2,.02,"#7aa36a");break}case"chair"'),
]
t = head
for k, (old, new) in enumerate(reps):
    c = t.count(old)
    print(f'--- rep{k+1} count in accum: {c}')
    assert c == 1, f'rep{k+1} anchor fail'
    t = t.replace(old, new)
    check(getcode(t), f'after-rep{k+1}')
pathlib.Path('scripts/dev/_vis1ok.html').write_text(t, encoding='utf-8')
print('wrote _vis1ok.html len', len(t))

import pathlib, re, subprocess, tempfile, os
p = pathlib.Path('assets/template.html')
t = p.read_text(encoding='utf-8')
pairs = [
 ("w.rotation.x=-.13}for(let _k=1;_k<y;_k++)N(t,.025,.02,s-.24,-r+g+x*_k,.541,.11,L(we(a,-.45),.9),!1);for(let _k=0;_k<y;_k++)N(t,x-.04,.014,.03,-r+g+x*(_k+.5),.541,.11+(s-.25)/2-.015,L(we(a,-.3),.9),!1);if(n.type",
  "w.rotation.x=-.13}for(let _k=1;_k<y;_k++)N(t,.02,.12,s-.26,-r+g+x*_k,.4,.11,L(we(a,-.4),.85),!1);for(let _k=0;_k<y;_k++)N(t,x-.03,.012,.02,-r+g+x*(_k+.5),.475,.11,L(we(a,-.3),.9),!1);if(n.type"),
 ('ft(t,i-.1,.025,.5,0,.545,l-s*.32,L("#c96f2e",.92),.008),ft(t,i-.1,.026,.09,0,.545,l-s*.32+.2,L("#f4f1ea",.95),.006)',
  'placeholder-never'),
]
# generic revert: hardcode full vis3 new->old using patch_vis3 old/new
reverts = [
 ('ft(t,i-.12,.02,.55,0,.581,l-s*.34,L("#c96f2e",.95),.008),ft(t,i-.12,.021,.1,0,.581,l-s*.34+.22,L("#f4f1ea",1),.006),ft(t,.5,.022,.3,-r+.45,.581,l-s*.34,L("#3b6ea5",.95),.006)',
  'ft(t,i-.1,.025,.5,0,.545,l-s*.32,L("#c96f2e",.92),.008),ft(t,i-.1,.026,.09,0,.545,l-s*.32+.2,L("#f4f1ea",.95),.006)'),
 ('N(t,.55,.007,s-.2,0,o+.001,0,L("#c96f2e",.95),!1),N(t,.36,.006,.26,-r+i*.27,o+.002,-l+s*.27,L("#f4f1ea",1),!1),N(t,.36,.006,.26,r-i*.27,o+.002,-l+s*.27,L("#f4f1ea",1),!1),N(t,.36,.006,.26,-r+i*.27,o+.002,l-s*.27,L("#e8e2d4",1),!1),N(t,.36,.006,.26,r-i*.27,o+.002,l-s*.27,L("#e8e2d4",1),!1),N(t,.2,.06,.2,0,o+.004,0,L("#7aa36a",1)),ue(t,.13,.05,.13,0,o+.06,0,L("#a8432a",.95)),ue(t,.045,.045,.045,-.05,o+.1,.04,L("#d94f3d",.95)),ue(t,.045,.045,.045,.05,o+.1,-.03,L("#e2a63d",.95)),ue(t,.045,.045,.045,0,o+.1,-.09,L("#5f8f55",.95))',
  'N(t,.5,.008,s-.2,0,o-.021,0,L("#c96f2e",.92),!1),N(t,.34,.006,.24,-r+i*.26,o-.02,-l+s*.26,L("#f4f1ea",.95),!1),N(t,.34,.006,.24,r-i*.26,o-.02,-l+s*.26,L("#f4f1ea",.95),!1),N(t,.34,.006,.24,-r+i*.26,o-.02,l-s*.26,L("#e8e2d4",.95),!1),N(t,.34,.006,.24,r-i*.26,o-.02,l-s*.26,L("#e8e2d4",.95),!1),N(t,.16,.05,.16,0,o,0,L("#7aa36a",.95)),ue(t,.11,.04,.11,0,o+.045,0,L("#a8432a",.9))'),
 ('N(t,.5,.03,.32,-r+i*.28,o+.001,0,L("#8a5a33",.9),!1),N(t,.34,.035,.24,-r+i*.28,o+.031,0,L("#3b6ea5",.95),!1),N(t,.3,.03,.2,-r+i*.28,o+.066,0,L("#c96f2e",.95),!1),ue(t,.05,.05,.09,r-i*.3,o+.001,.1,L("#f4f1ea",.95)),ue(t,.035,.035,.05,r-i*.3,o+.09,.1,L("#5f8f55",.95))',
  'u(o-.04,.05,.018)'),
 ('ft(t,.34,.025,.5,-r+g/2,.681,0,L("#c96f2e",.95),.008);ft(t,.34,.026,.12,-r+g/2,.681,-.18,L("#f4f1ea",1),.005)}break;case"coffeeTable"',
  'break;case"coffeeTable"'),
]
def getcode(text):
    ms = list(re.finditer(r'<script(?P<attrs>[^>]*)>(?P<code>.*?)</script>', text, re.S))
    blocks = [(len(x.group('code')), x.group('code')) for x in ms if len(x.group('code').strip()) > 100]
    blocks.sort(key=lambda x: x[0])
    return blocks[-1][1]
def check(code, label):
    fd, fp = tempfile.mkstemp(suffix='.mjs')
    os.write(fd, code.encode('utf-8')); os.close(fp)
    r = subprocess.run(['node', '--check', fp], capture_output=True)
    err = r.stderr.decode('utf-8', errors='replace')
    print('####', label, 'rc', r.returncode)
    if r.returncode:
        i = err.find('SyntaxError')
        print('CTX:', repr(err[max(0,i-400):i+200]))
    os.unlink(fp)
# revert all vis3 to get pre-vis3, then re-apply one by one
pre = t
pre = pre.replace(
 "w.rotation.x=-.13}for(let _k=1;_k<y;_k++)N(t,.025,.02,s-.24,-r+g+x*_k,.541,.11,L(we(a,-.45),.9),!1);for(let _k=0;_k<y;_k++)N(t,x-.04,.014,.03,-r+g+x*(_k+.5),.541,.11+(s-.25)/2-.015,L(we(a,-.3),.9),!1);if(n.type",
 "w.rotation.x=-.13}for(let _k=1;_k<y;_k++)N(t,.02,.12,s-.26,-r+g+x*_k,.4,.11,L(we(a,-.4),.85),!1);for(let _k=0;_k<y;_k++)N(t,x-.03,.012,.02,-r+g+x*(_k+.5),.475,.11,L(we(a,-.3),.9),!1);if(n.type")
for new, old in reverts:
    c = pre.count(new)
    print('revert count', c, new[:60])
    assert c == 1, new[:200]
    pre = pre.replace(new, old)
# sofa-blanket revert: the if-block form back to single-for form
old_sb = 'if(n.type==="sofa"&&i>1.3){for(const b of[-1,1])ft(t,.42,.4,.09,b*(r-(b<0?g:m)-.3),.52,-l+.42,L(b<0?"#c96f2e":"#3b6ea5",.95),.04,{puff:[.01,.01,.035]}).rotation.set(-.3,b*.25,b*.12);ft(t,.34,.025,.5,-r+g/2,.681,0,L("#c96f2e",.95),.008);ft(t,.34,.026,.12,-r+g/2,.681,-.18,L("#f4f1ea",1),.005)}break;case"coffeeTable"'
new_sb = 'if(n.type==="sofa"&&i>1.3)for(const b of[-1,1])ft(t,.42,.4,.09,b*(r-(b<0?g:m)-.3),.52,-l+.42,L(b<0?"#c96f2e":"#3b6ea5",.95),.04,{puff:[.01,.01,.035]}).rotation.set(-.3,b*.25,b*.12);break;case"coffeeTable"'
print('revert blanket', pre.count(old_sb))
assert pre.count(old_sb) == 1
pre = pre.replace(old_sb, new_sb)
check(getcode(pre), 'pre-vis3 baseline')
# now apply vis3 reps one by one
steps = [
 ('sofa-top', "w.rotation.x=-.13}for(let _k=1;_k<y;_k++)N(t,.02,.12,s-.26,-r+g+x*_k,.4,.11,L(we(a,-.4),.85),!1);for(let _k=0;_k<y;_k++)N(t,x-.03,.012,.02,-r+g+x*(_k+.5),.475,.11,L(we(a,-.3),.9),!1);if(n.type",
  "w.rotation.x=-.13}for(let _k=1;_k<y;_k++)N(t,.025,.02,s-.24,-r+g+x*_k,.541,.11,L(we(a,-.45),.9),!1);for(let _k=0;_k<y;_k++)N(t,x-.04,.014,.03,-r+g+x*(_k+.5),.541,.11+(s-.25)/2-.015,L(we(a,-.3),.9),!1);if(n.type"),
 ('bed-top', 'ft(t,i-.1,.025,.5,0,.545,l-s*.32,L("#c96f2e",.92),.008),ft(t,i-.1,.026,.09,0,.545,l-s*.32+.2,L("#f4f1ea",.95),.006)',
  'ft(t,i-.12,.02,.55,0,.581,l-s*.34,L("#c96f2e",.95),.008),ft(t,i-.12,.021,.1,0,.581,l-s*.34+.22,L("#f4f1ea",1),.006),ft(t,.5,.022,.3,-r+.45,.581,l-s*.34,L("#3b6ea5",.95),.006)'),
 ('sofa-blanket', 'if(n.type==="sofa"&&i>1.3)for(const b of[-1,1])ft(t,.42,.4,.09,b*(r-(b<0?g:m)-.3),.52,-l+.42,L(b<0?"#c96f2e":"#3b6ea5",.95),.04,{puff:[.01,.01,.035]}).rotation.set(-.3,b*.25,b*.12);break;case"coffeeTable"',
  'if(n.type==="sofa"&&i>1.3){for(const b of[-1,1])ft(t,.42,.4,.09,b*(r-(b<0?g:m)-.3),.52,-l+.42,L(b<0?"#c96f2e":"#3b6ea5",.95),.04,{puff:[.01,.01,.035]}).rotation.set(-.3,b*.25,b*.12);ft(t,.34,.025,.5,-r+g/2,.681,0,L("#c96f2e",.95),.008);ft(t,.34,.026,.12,-r+g/2,.681,-.18,L("#f4f1ea",1),.005)}break;case"coffeeTable"'),
]
acc = pre
for tag, o, n in steps:
    assert acc.count(o) == 1, tag
    acc = acc.replace(o, n)
    check(getcode(acc), 'after-'+tag)
pathlib.Path('scripts/dev/_acc2.html').write_text(acc, encoding='utf-8')
print('wrote acc2')

import pathlib
p = pathlib.Path('assets/template.html')
t = p.read_text(encoding='utf-8')
def rep(old, new, tag):
    global t
    c = t.count(old)
    print(tag, c)
    assert c == 1, tag + ' FAIL len='+str(len(old))+' old='+old[:240]
    t = t.replace(old, new)
rep('function kv(n,e){', 'function __nt(n){return n.userData.noTheme=!0,n}function kv(n,e){', 'helper')
old_sofa = 'if(n.type==="sofa"&&i>1.3)for(const b of[-1,1])ft(t,.42,.4,.09,b*(r-(b<0?g:m)-.3),.52,-l+.42,L(we(a,b<0?-.18:.12),.95),.04,{puff:[.01,.01,.035]}).rotation.set(-.3,b*.25,b*.12);break}'
new_sofa = 'if(n.type==="sofa"&&i>1.3)for(const b of[-1,1])__nt(ft(t,.42,.4,.09,b*(r-(b<0?g:m)-.3),.52,-l+.42,L(b<0?"#d96f2e":"#2f7fd0",1),.04,{puff:[.01,.01,.035]})).rotation.set(-.3,b*.25,b*.12);break}'
rep(old_sofa, new_sofa, 'sofa-all')
rep('ft(t,i+.06,.03,s*.22,0,.575,l-s*.14,L(a,.95),.012)',
    '__nt(ft(t,i+.06,.032,s*.22,0,.581,l-s*.14,L("#c96f2e",.95),.012))', 'bed-runner')
rep('N(t,i-.18,.07,s-.18,0,o-.115,0,L(we(a,-.3),.55)),la(t,.07,.05,o+.2,.02,"#7aa36a");break;case"chair"',
    'N(t,i-.18,.07,s-.18,0,o-.115,0,L(we(a,-.3),.55)),la(t,.07,.05,o+.2,.02,"#7aa36a"),__nt(N(t,.55,.008,s-.2,0,o+.001,0,L("#c96f2e",.95),!1)),__nt(N(t,.36,.007,.26,-r+i*.27,o+.002,-l+s*.27,L("#f4f1ea",1),!1)),__nt(N(t,.36,.007,.26,r-i*.27,o+.002,-l+s*.27,L("#f4f1ea",1),!1)),__nt(N(t,.36,.007,.26,-r+i*.27,o+.002,l-s*.27,L("#e8e2d4",1),!1)),__nt(N(t,.36,.007,.26,r-i*.27,o+.002,l-s*.27,L("#e8e2d4",1),!1)),__nt(N(t,.2,.06,.2,0,o+.004,0,L("#7aa36a",1))),__nt(ue(t,.13,.05,.13,0,o+.06,0,L("#a8432a",.95))),__nt(ue(t,.045,.045,.045,-.05,o+.1,.04,L("#d94f3d",.95))),__nt(ue(t,.045,.045,.045,.05,o+.1,-.03,L("#e2a63d",.95))),__nt(ue(t,.045,.045,.045,0,o+.1,-.09,L("#5f8f55",.95)));break;case"chair"', 'dining-set')
rep('u(o-.04,.05,.018);break;case"tvCabinet"',
    'u(o-.04,.05,.018),__nt(N(t,.5,.032,.32,-r+i*.28,o+.001,0,L("#8a5a33",.9),!1)),__nt(N(t,.34,.036,.24,-r+i*.28,o+.033,0,L("#3b6ea5",.95),!1)),__nt(N(t,.3,.032,.2,-r+i*.28,o+.069,0,L("#c96f2e",.95),!1)),__nt(ue(t,.05,.05,.09,r-i*.3,o+.001,.1,L("#f4f1ea",.95))),__nt(ue(t,.035,.035,.05,r-i*.3,o+.09,.1,L("#5f8f55",.95)));break;case"tvCabinet"', 'coffee-set')
rep('const f=ft(t,i,.42,.05,0,.48,-l+.03,L(a,.85),.02);f.rotation.x=-.08,u(.41,.04,.012,"#2b2e33");break}',
    'const f=ft(t,i,.42,.05,0,.48,-l+.03,L(a,.85),.02);f.rotation.x=-.08,u(.41,.04,.012,"#2b2e33"),__nt(ft(t,i-.1,.028,s-.14,0,.481,.02,L("#c96f2e",.95),.012));break}', 'chair-pad')
p.write_text(t, encoding='utf-8')
print('OK vis6')

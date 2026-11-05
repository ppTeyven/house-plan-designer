import pathlib
p = pathlib.Path('assets/template.html')
t = p.read_text(encoding='utf-8')
def rep(old, new, tag):
    c = t.count(old)
    print(tag, c)
    assert c == 1, tag + ' FAIL ' + old[:200]
    return t.replace(old, new)

# 0) helper: mark mesh as no-theme (skip palette remap)
old0 = 'function kv(n,e){'
new0 = 'function __nt(n){return n.userData.noTheme=!0,n}function kv(n,e){'
t = rep(old0, new0, 'helper')

# 1) sofa pillows keep their orange/blue
old1 = 'L(b<0?"#d96f2e":"#2f7fd0",1),.055,{puff:[.02,.02,.045]})'
new1 = 'L(b<0?"#d96f2e":"#2f7fd0",1),.055,{puff:[.02,.02,.045]}))'
# need full wrap: find the ft( call start
old1f = 'if(n.type==="sofa"&&i>1.3){for(const b of[-1,1])ft(t,.42,.4,.09,'
new1f = 'if(n.type==="sofa"&&i>1.3){for(const b of[-1,1])__nt(ft(t,.42,.4,.09,'
t = rep(old1f, new1f, 'pillow-wrap')
old1e = '.04,{puff:[.01,.01,.035]}).rotation.set(-.3,b*.25,b*.12);ft(t,.34,.025,.5,'
new1e = '.04,{puff:[.01,.01,.035]})).rotation.set(-.3,b*.25,b*.12);__nt(ft(t,.34,.025,.5,'
t = rep(old1e, new1e, 'pillow-end+blanket-wrap')
old1b = 'L("#c96f2e",.95),.008);ft(t,.34,.026,.12,-r+g/2,.681,-.18,'
new1b = 'L("#c96f2e",.95),.008));__nt(ft(t,.34,.026,.12,-r+g/2,.681,-.18,'
t = rep(old1b, new1b, 'blanket-wrap2')
old1c = 'L("#f4f1ea",1),.005)}break;case"coffeeTable"'
new1c = 'L("#f4f1ea",1),.005))}break;case"coffeeTable"'
t = rep(old1c, new1c, 'blanket-end')

# 2) bed runner trio
old2 = 'ft(t,i-.12,.02,.55,0,.581,l-s*.34,L("#c96f2e",.95),.008),ft(t,i-.12,.021,.1,0,.581,l-s*.34+.22,L("#f4f1ea",1),.006),ft(t,.5,.022,.3,-r+.45,.581,l-s*.34,L("#3b6ea5",.95),.006)'
new2 = '__nt(ft(t,i-.12,.02,.55,0,.581,l-s*.34,L("#c96f2e",.95),.008)),__nt(ft(t,i-.12,.021,.1,0,.581,l-s*.34+.22,L("#f4f1ea",1),.006)),__nt(ft(t,.5,.022,.3,-r+.45,.581,l-s*.34,L("#3b6ea5",.95),.006))'
t = rep(old2, new2, 'bed-runner-wrap')

# 3) dining set
old3 = 'N(t,.55,.007,s-.2,0,o+.001,0,L("#c96f2e",.95),!1),N(t,.36,.006,.26,-r+i*.27,o+.002,'
new3 = '__nt(N(t,.55,.007,s-.2,0,o+.001,0,L("#c96f2e",.95),!1)),__nt(N(t,.36,.006,.26,-r+i*.27,o+.002,'
t = rep(old3, new3, 'dining-wrap1')
old3b = 'L("#f4f1ea",1),!1),N(t,.36,.006,.26,r-i*.27,o+.002,-l+s*.27,L("#f4f1ea",1),!1),N(t,.36,.006,.26,-r+i*.27,o+.002,l-s*.27,L("#e8e2d4",1),!1),N(t,.36,.006,.26,r-i*.27,o+.002,l-s*.27,L("#e8e2d4",1),!1),N(t,.2,.06,.2,0,o+.004,0,L("#7aa36a",1)),ue(t,.13,.05,.13,0,o+.06,0,L("#a8432a",.95)),ue(t,.045,.045,.045,-.05,o+.1,.04,L("#d94f3d",.95)),ue(t,.045,.045,.045,.05,o+.1,-.03,L("#e2a63d",.95)),ue(t,.045,.045,.045,0,o+.1,-.09,L("#5f8f55",.95))'
new3b = 'L("#f4f1ea",1),!1)),__nt(N(t,.36,.006,.26,r-i*.27,o+.002,-l+s*.27,L("#f4f1ea",1),!1)),__nt(N(t,.36,.006,.26,-r+i*.27,o+.002,l-s*.27,L("#e8e2d4",1),!1)),__nt(N(t,.36,.006,.26,r-i*.27,o+.002,l-s*.27,L("#e8e2d4",1),!1)),__nt(N(t,.2,.06,.2,0,o+.004,0,L("#7aa36a",1))),__nt(ue(t,.13,.05,.13,0,o+.06,0,L("#a8432a",.95))),__nt(ue(t,.045,.045,.045,-.05,o+.1,.04,L("#d94f3d",.95))),__nt(ue(t,.045,.045,.045,.05,o+.1,-.03,L("#e2a63d",.95))),__nt(ue(t,.045,.045,.045,0,o+.1,-.09,L("#5f8f55",.95)))'
t = rep(old3b, new3b, 'dining-wrap2')

# 4) coffee table set
old4 = 'N(t,.5,.03,.32,-r+i*.28,o+.001,0,L("#8a5a33",.9),!1),N(t,.34,.035,.24,-r+i*.28,o+.031,0,L("#3b6ea5",.95),!1),N(t,.3,.03,.2,-r+i*.28,o+.066,0,L("#c96f2e",.95),!1),ue(t,.05,.05,.09,r-i*.3,o+.001,.1,L("#f4f1ea",.95)),ue(t,.035,.035,.05,r-i*.3,o+.09,.1,L("#5f8f55",.95))'
new4 = '__nt(N(t,.5,.03,.32,-r+i*.28,o+.001,0,L("#8a5a33",.9),!1)),__nt(N(t,.34,.035,.24,-r+i*.28,o+.031,0,L("#3b6ea5",.95),!1)),__nt(N(t,.3,.03,.2,-r+i*.28,o+.066,0,L("#c96f2e",.95),!1)),__nt(ue(t,.05,.05,.09,r-i*.3,o+.001,.1,L("#f4f1ea",.95))),__nt(ue(t,.035,.035,.05,r-i*.3,o+.09,.1,L("#5f8f55",.95)))'
t = rep(old4, new4, 'coffee-wrap')

# 5) chair pad
old5 = 'case"chair":{ft(t,i,.07,s-.04,0,.41,.02,L(a,.85),.025,{puff:[0,.008,0]});ft(t,i-.1,.025,s-.14,0,.455,.02,L("#c96f2e",.95),.012);'
new5 = 'case"chair":{ft(t,i,.07,s-.04,0,.41,.02,L(a,.85),.025,{puff:[0,.008,0]});__nt(ft(t,i-.1,.025,s-.14,0,.455,.02,L("#c96f2e",.95),.012));'
t = rep(old5, new5, 'chair-wrap')

p.write_text(t, encoding='utf-8')
print('OK vis5')

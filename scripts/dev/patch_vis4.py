import pathlib
p = pathlib.Path('assets/template.html')
t = p.read_text(encoding='utf-8')
def rep(old, new, tag):
    c = t.count(old)
    print(tag, c)
    assert c == 1, tag + ' FAIL ' + old[:200]
    return t.replace(old, new)

# 1) sofa: cushions much lighter than base -> visible separation from bird view
# base f stays, cushion h becomes lightened
old1 = 'case"sofa":case"armchair":case"lounge":{const f=L(we(a,-.08),.95),h=L(a,.95)'
new1 = 'case"sofa":case"armchair":case"lounge":{const f=L(we(a,-.18),.95),h=L(we(a,.28),.97)'
t = rep(old1, new1, 'sofa-contrast')

# 2) sofa pillows bigger + brighter
old2 = 'L(b<0?"#c96f2e":"#3b6ea5",.95),.04,{puff:[.01,.01,.035]})'
new2 = 'L(b<0?"#d96f2e":"#2f7fd0",1),.055,{puff:[.02,.02,.045]})'
t = rep(old2, new2, 'sofa-pillow-big')

# 3) bed: duvet near-white + wide terracotta runner + blue accent fold
old3 = 'ft(t,i+.06,.03,s*.22,0,.575,l-s*.14,L(a,.95),.012)'
new3 = 'ft(t,i+.06,.03,s*.22,0,.575,l-s*.14,L("#f7f4ee",1),.012)'
t = rep(old3, new3, 'bed-duvet')

# 4) chair: add contrasting seat pad on top (visible from bird)
old4 = 'case"chair":{ft(t,i,.07,s-.04,0,.41,.02,L(a,.85),.025,{puff:[0,.008,0]});'
new4 = 'case"chair":{ft(t,i,.07,s-.04,0,.41,.02,L(a,.85),.025,{puff:[0,.008,0]});ft(t,i-.1,.025,s-.14,0,.455,.02,L("#c96f2e",.95),.012);'
t = rep(old4, new4, 'chair-pad')

p.write_text(t, encoding='utf-8')
print('OK vis4')

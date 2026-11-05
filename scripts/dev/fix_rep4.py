import pathlib
p = pathlib.Path('assets/template.html')
t = p.read_text(encoding='utf-8')
old = 'N(t,.44,.006,s-.24,0,o+.028,0,L("#c96f2e",.9),!1),N(t,i*.32,.004,.24,-r+i*.24,o+.028,-l+s*.24,L("#f4f1ea",.9),!1),N(t,i*.32,.004,.24,r-i*.24,o+.028,-l+s*.24,L("#f4f1ea",.9),!1),la(t,.07,.05,o+.2,.02,"#7aa36a");break}case"chair"'
new = 'N(t,.44,.006,s-.24,0,o,0,L("#c96f2e",.9),!1),N(t,.3,.004,.2,-r+i*.25,o+.006,0,L("#f4f1ea",.9),!1),N(t,.3,.004,.2,r-i*.25,o+.006,0,L("#f4f1ea",.9),!1),la(t,.07,.05,o+.2,.02,"#7aa36a");break;case"chair"'
print('count', t.count(old))
assert t.count(old) == 1
t = t.replace(old, new)
p.write_text(t, encoding='utf-8')
print('fixed rep4')

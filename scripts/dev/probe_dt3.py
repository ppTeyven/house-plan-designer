import pathlib
t=pathlib.Path('assets/template.html').read_text(encoding='utf-8')
a='N(t,i-.18,.07,s-.18,0,o-.115,0,L(we(a,-.3),.55)),la(t,.07,.05,o+.2,.02,"#7aa36a");break}case"chair"'
print('full-anchor', t.count(a))
b='la(t,.07,.05,o+.2,.02,"#7aa36a")'
print('plant-part', t.count(b))
p=t.find('case"diningTable":N(t,i,.05')
print(repr(t[p:p+420]))

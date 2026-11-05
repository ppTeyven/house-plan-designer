import pathlib
p = pathlib.Path('assets/template.html')
t = p.read_text(encoding='utf-8')
old = "N(t,.012,.1,s-.28,-r+g+_g*_k,.4,.11,L(we(a,-.35),.8),!1)}}}if(n.type"
new = "N(t,.012,.1,s-.28,-r+g+_g*_k,.4,.11,L(we(a,-.35),.8),!1)}}if(n.type"
print('count3', t.count(old))
assert t.count(old) == 1
t = t.replace(old, new)
p.write_text(t, encoding='utf-8')
print('reverted to 2 braces')

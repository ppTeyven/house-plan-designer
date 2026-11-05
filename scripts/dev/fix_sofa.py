import pathlib
p = pathlib.Path('assets/template.html')
t = p.read_text(encoding='utf-8')
old = "N(t,x-.03,.012,.02,-r+g+x*(_k+.5),.475,.11,L(we(a,-.3),.9),!1)}if(n.type===\"sofa\"&&i>1.3)"
new = "N(t,x-.03,.012,.02,-r+g+x*(_k+.5),.475,.11,L(we(a,-.3),.9),!1);if(n.type===\"sofa\"&&i>1.3)"
print('sofa-fix count', t.count(old))
assert t.count(old) == 1
t = t.replace(old, new)
p.write_text(t, encoding='utf-8')
print('sofa brace fixed')

import pathlib
t=pathlib.Path('assets/template.html').read_text(encoding='utf-8')
p=t.find('function qL()')
print(t[p:p+1200])
print('==== wall builder ====')
# find the function containing C(D/1e3+.02,.04,0,U,0,u+.02)
q=t.find('C(D/1e3+.02,.04,0,U,0,u+.02)')
print('cap pos',q)
print(t[max(0,q-4000):q+200].replace('\n',' | ')[-4200:])

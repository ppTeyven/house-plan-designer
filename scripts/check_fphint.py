import pathlib
p = pathlib.Path('assets/template.html')
t = p.read_text(encoding='utf-8')
i = t.find('fphint')
print(t[max(0,i-800):i+1200][:2200])

import pathlib
p = pathlib.Path('assets/template.html')
t = p.read_text(encoding='utf-8')
def show(name, needle):
    i = t.find(needle)
    print(name, 'found' if i>=0 else 'MISSING', i)
    if i>=0:
        print(t[i:i+320])
        print('---')
show('toast', '#toast{position:fixed')
show('share', '#shareBanner{display')
show('fps', '._fps{position:fixed')
show('fphint', '.fphint{position:')

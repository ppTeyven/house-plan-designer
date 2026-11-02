import pathlib
p = pathlib.Path('assets/template.html')
t = p.read_text(encoding='utf-8')
old = '.overlay{position:absolute;display:flex;gap:6px;z-index:2;pointer-events:none;max-width:calc(100% - 24px);flex-wrap:wrap}.overlay button,.overlay input,.overlay select,.overlay .seg,.overlay .glass{pointer-events:auto}'
new = '.overlay{position:absolute;display:flex;gap:6px;z-index:2;pointer-events:none;max-width:calc(100% - 24px);flex-wrap:wrap}.overlay button,.overlay input,.overlay select,.overlay .seg,.overlay .glass{pointer-events:auto}#pane3d .overlay.ov-tl{top:auto;bottom:12px;left:12px;right:auto;max-width:calc(100% - 24px)}'
assert t.count(old) == 1, t.count(old)
t = t.replace(old, new)
# fphint往上抬一点，避免和工具栏重叠，toast再往上
t = t.replace('.fphint{position:absolute;left:10px;bottom:6px;', '.fphint{position:absolute;left:10px;bottom:58px;')
t = t.replace('#toast{position:fixed;left:50%;bottom:44px;', '#toast{position:fixed;left:50%;bottom:108px;')
t = t.replace('#shareBanner{display:none;position:fixed;left:50%;bottom:44px;', '#shareBanner{display:none;position:fixed;left:50%;bottom:108px;')
p.write_text(t, encoding='utf-8')
print('OK move 3d toolbar to bottom')

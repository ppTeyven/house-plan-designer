import pathlib
p = pathlib.Path('assets/template.html')
t = p.read_text(encoding='utf-8')
old_css = '.fphint{position:absolute;left:50%;bottom:16px;transform:translate(-50%);padding:7px 14px;font-size:12px;color:#fff;background:#14181eb3;border-radius:20px;opacity:0;transition:opacity .3s;pointer-events:none;white-space:nowrap}.fphint.show{opacity:1}'
new_css = '.fphint{position:absolute;left:50%;top:10px;transform:translateX(-50%);padding:5px 12px;font-size:11px;color:#fff;background:#14181e99;border-radius:14px;opacity:0;transition:opacity .5s;pointer-events:none;white-space:nowrap;z-index:5;max-width:90%;overflow:hidden;text-overflow:ellipsis}.fphint.show{opacity:.92}'
c = t.count(old_css)
print('css count', c)
assert c >= 1
t = t.replace(old_css, new_css)
old_js = 'he("#fphint").classList.toggle("show",re.active)'
new_js = 'function _fp(s){var f=he("#fphint");if(!f)return;f.classList.toggle("show",s);clearTimeout(_fp.t);if(s)_fp.t=setTimeout(function(){f.classList.remove("show")},3500)}_fp(re.active)'
c2 = t.count(old_js)
print('js count', c2)
assert c2 == 1
t = t.replace(old_js, new_js)
p.write_text(t, encoding='utf-8')
print('OK fphint fixed')

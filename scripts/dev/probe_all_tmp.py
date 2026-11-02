import os, re
t = open('assets/template.html', encoding='utf-8').read()
out = 'scripts/dev/probe_out'
os.makedirs(out, exist_ok=True)
def w(name, s):
    open(f'{out}/{name}', 'w', encoding='utf-8').write(s)
    print(name, len(s))
# 1. full Ua V2
i = t.find('async function Ua(n){/*__viewTransV2*/')
j = t.find('window.addEventListener("keydown"', i)
w('ua.txt', t[i:j])
# 2. all wi( sites
sites = []
for m in re.finditer(r'wi\(', t):
    s = max(0, m.start()-220)
    sites.append(f'--- idx {m.start()} ---\n' + t[s:m.start()+320].replace('\n',' '))
w('wi.txt', '\n\n'.join(sites))
# 3. view event plumbing
ev = []
for m in re.finditer(r'(r0\(.view.|bt\(.view.|Uv\(|function Yc|Yc=\(\)|Yc=n)', t):
    s = max(0, m.start()-160)
    ev.append(f'--- idx {m.start()} :: {m.group(0)} ---\n' + t[s:m.start()+300].replace('\n',' '))
w('viewev.txt', '\n\n'.join(ev))
# 4. fI pointer handlers
i = t.find('function fI(){')
w('fi.txt', t[i:i+7000])
# 5. transition helpers
i = t.find('function __riSmooth')
w('ri.txt', t[i:i+4200])
# 6. smart core
i = t.find('async function rh(n){')
w('smart.txt', t[i:i+5200])
# 7. Ir + en/Wd/Dn
i = t.find('function Ir(){')
w('ir.txt', t[i:i+1500])
for pat, nm in [('const en=', 'en.txt'), ('function Wd(', 'wd.txt'), ('function Dn(', 'dn.txt'), ('Ps=', 'ps.txt')]:
    k = t.find(pat)
    w(nm, ('IDX '+str(k)+'\n'+t[max(0,k-300):k+900]) if k>=0 else 'NOT FOUND')
# 8. walk core
i = t.find('function Vp(')
w('walk.txt', t[i:i+1500])
i = t.find('function Ns(')
w('walk2.txt', t[i:i+1200])
k = t.find('function l3(){')
w('walk3.txt', t[k:k+1800] if k>=0 else 'NOT FOUND')
# 9. pano/xr
i = t.find('定格实景漫游')
w('pano.txt', t[max(0,i-500):i+5200])
k = t.find('panoBtn')
w('pano2.txt', t[max(0,k-700):k+900])
# 10. CSS rules
css = []
for m in re.finditer(r'(\.seg button\.on|\.tbtn\.on|\.btn\.on|\.btn\.glass|\.glass\{|button\.on|#walkCtl|walk-ctl\.show|#fphint|fphint\.show|smart-ui\.show|smart-mode|#panoBtn|#xr-btn|#camSeg|\.stage\[data-view|\.pane\{|\.pop\.open|\.pop\{|\.dropdown\.open)', t):
    s = max(0, m.start()-60)
    css.append(t[s:m.start()+380].replace('\n',' '))
w('css.txt', '\n\n'.join(css[:80]))
print('DONE sites:', len(sites))

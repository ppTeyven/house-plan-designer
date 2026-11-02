import subprocess, os
t = open('assets/template.html', encoding='utf-8').read()

def check(name, code):
    p = r'C:\Users\zzkkg\AppData\Local\Temp\frag_%s.mjs' % name
    open(p, 'w', encoding='utf-8').write(code)
    r = subprocess.run(['node', '--check', p], capture_output=True)
    if r.returncode == 0:
        print(name, 'OK')
    else:
        err = r.stderr.decode('utf-8', 'replace')
        # last 500 chars hold the real message
        print(name, 'FAIL ::', err[-600:].replace('\r', ' ').replace('\n', ' ')[:600])

STUB = 'var Bi,Tt,E,Ze,qr,ha,sl,re,M4,b8,Se,Gh,_x,Je,Zc,Ir,bt,P1,L1,ao,Zv,Ns,Te,Vp,rh,he,W2,Mt,Nc;function Xc(){};'

# F1 IR statement
i = t.find('Tt.enableRotate=!n&&E.view')
frag = t[i:t.find('DOLLY_PAN', i) + len('DOLLY_PAN')]
check('F1-IR', STUB + 'function t(){var n;Fu=6;' + frag + ';}')

# F2 B1 watchdog in sequence context
i = t.find(',function(b_,d_){setTimeout')
j = t.find('}(Bi,e)', i) + len('}(Bi,e)')
frag = t[i:j]
check('F2-B1', STUB + 'function t(){var e=1,nn={};Bi={to:nn,done:null},Tt.enabled=!1' + frag + ';}')

# F3 JL completion
i = t.find('t>=1&&(Bi=null,Tt.enabled')
frag = t[i:t.find('a.call(e))', i) + len('a.call(e))')]
check('F3-JL', STUB + 'function t(){var a;const e={done:null};' + frag + ';}')

# F4 Ua tail
i = t.find('stopGlue=!0;try{Bi=null')
frag = t[i:t.find('E.transitioning=!1;', i) + len('E.transitioning=!1;')]
check('F4-tail', STUB + 'async function t(){' + frag + '}')

# F5 Vp head
i = t.find('function Vp(n){if(E.view==="split")')
frag = t[i:t.find('if(re.active||Bi)return;', i) + len('if(re.active||Bi)return;')]
check('F5-Vp', STUB + frag + '}')

# F11 H1 second view listener
i = t.find('r0("view",()=>{if(E.view==="split"')
frag = t[i:i+400]
# cut at balanced end: find '}})' ending
frag = frag[:frag.find('}})') + 3]
check('F11-H1', STUB + frag + ';')

# F12 H2 change listener in sequence context
i = t.find(',Tt.addEventListener("change",function(){if(E.view==="split"')
j = t.find('window.__spSync=!1}})', i) + len('window.__spSync=!1}})')
frag = t[i:j]
check('F12-H2', STUB + 'function t(){var O0,o;Tt={};' + 'Tt.x=1' + frag + ';}')

t = open('assets/template.html', encoding='utf-8').read()
def show(name, pat, ctx=600):
    i = t.find(pat)
    print('===', name, 'idx', i)
    if i < 0:
        print('NOT FOUND')
        return
    print(t[max(0,i-200):i+ctx].replace('\n',' ')[:2200])
    print()
show('Ua', 'async function Ua(n){/*__viewTransV2*/', 3600)
show('CSSpane', '.pane{position:absolute', 1100)
show('_x', 'function _x(){', 900)
show('Gh', 'function Gh(){', 700)
show('P1', 'function P1(', 500)
show('L1', 'function L1(', 500)
show('ri', 'function ri(n=Se.W', 900)

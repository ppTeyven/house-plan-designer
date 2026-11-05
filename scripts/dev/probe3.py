import pathlib,re
t=pathlib.Path('assets/template.html').read_text(encoding='utf-8')
def show(name, pat, w=500):
    ms=list(re.finditer(pat,t))
    print('===',name,'count',len(ms))
    for m in ms[:3]:
        s=max(0,m.start()-w); e=min(len(t),m.end()+w)
        print(t[s:e].replace('\n',' | ')[:3000])
        print('---POS',m.start())
        print()
show('suncam-setup', r'b\.left=-x,b\.right=x')
show('Ai-def', r'const Ai=\{hemi')
show('j5-def', r'function j5\(')
show('Zh-def', r'for\(let s=0;s<2;s\+\+\)')
show('qR-def', r'class qR|qR=')
show('ro-def', r'\bro=new |ro=\(|class ro')
show('Lb-def', r'class Lb|Lb=')
show('_h-def', r'class _h|_h=')
show('A5-def', r'class A5|A5=')

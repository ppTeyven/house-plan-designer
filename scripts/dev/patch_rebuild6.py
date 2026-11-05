import pathlib
p = pathlib.Path('assets/template.html')
t = p.read_text(encoding='utf-8')
reps = []
# C1: cabinet single panel door — recessed finger groove (full-height, Lema Text style), dark shadow line
reps.append((
'x=(v,w,S=p)=>{pn(n,e,t,s,o,v+.003,w-.003,S),Ys(n,e,t,m,u==="wall"?v+.07:u==="base"?w-.1:v+(w-v)*.45,f,!0,u==="tall"?.4:.12)}',
'x=(v,w,S=p)=>{pn(n,e,t,s,o,v+.003,w-.003,S),_0(n,Lt(e,t,o-30,o-17,v+.012,w-.012,t.depth+15,t.depth+17),v+.012,w-v-.024,we(h,-.45),!1),Ys(n,e,t,m,u==="wall"?v+.07:u==="base"?w-.1:v+(w-v)*.45,f,!0,u==="tall"?.4:.12)}'
))
# C2: cabinet drawer fronts — each drawer gets a recessed pull groove line + edge profile
reps.append((
'pn(n,e,t,s,o,A+.003,A+(w-v)/S-.003,p),Ys(n,e,t,a,A+(w-v)/S*.72,f,!1,Math.min(.3,(o-s)*.45/1e3))',
'pn(n,e,t,s,o,A+.003,A+(w-v)/S-.003,p),_0(n,Lt(e,t,o-28,o-16,A+.014,A+(w-v)/S-.014,t.depth+15,t.depth+17),A+.014,(w-v)/S-.028,we(h,-.45),!1),Ys(n,e,t,a,A+(w-v)/S*.72,f,!1,Math.min(.3,(o-s)*.45/1e3))'
))
for old, new in reps:
    c = t.count(old)
    print('CHECK', c, old[:80])
    assert c == 1, old[:220]
    t = t.replace(old, new)
p.write_text(t, encoding='utf-8')
print('OK cabinet grooves', len(reps))

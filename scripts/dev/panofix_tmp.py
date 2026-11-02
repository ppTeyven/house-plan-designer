p = 'assets/template.html'
t = open(p, encoding='utf-8').read()
a = '};he("#panoBtn").onclick=async()=>{'
print('head-count', t.count(a))
# find end of the pano handler: locate 'OU(e,' then its closing '};he("#leftToggle")'
i = t.find(a)
seg = t[i:i+1200]
print(seg[:1100])

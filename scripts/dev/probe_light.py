import pathlib,re
t=pathlib.Path('assets/template.html').read_text(encoding='utf-8')
# dump lighting v3 full block
i=t.find('整屋统一光照 v3')
print(t[i-200:i+6000].replace('\n',' | ')[:8000])
print('\n====SUN-CAM====')
for pat in [r'shadow\.camera\.(left|right|top|bottom|near|far)[^;]*', r'sun\.position[^;]*', r'i\.position\.set\([^;]*sun|sun[^;]{0,40}position', r'Zh\.push', r'new qR\([^)]*\)', r'function __setLT[^}]+}', r'Ai\.hemi[^;]*', r'pt\.environmentIntensity[^;]*', r'Oa\.intensity[^;]*', r'Tn\.intensity[^;]*']:
    ms=list(re.finditer(pat,t))
    print('==',pat,len(ms))
    for m in ms[:4]:
        print(repr(t[max(0,m.start()-200):m.end()+300][:700]))
    print()

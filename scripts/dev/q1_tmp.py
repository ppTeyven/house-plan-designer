t = open('assets/template.html', encoding='utf-8').read()
i = t.find('async function Ua(n){/*__viewTransV2*/')
print('UA LEN', len(t[i:i+4000]))
print(t[i:i+4000])

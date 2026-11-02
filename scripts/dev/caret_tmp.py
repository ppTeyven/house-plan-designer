d=open(r'C:\Users\zzkkg\AppData\Local\Temp\be4.txt',encoding='utf-8',errors='replace').read().split('\n')
print(len(d))
for i,l in enumerate(d):
    if '^' in l or 'SyntaxError' in l or 'bundle_check' in l:
        print(i, repr(l[:200]))
print('---head---')
print('\n'.join(d[:8])[:2000])

lines = open(r'C:\Users\zzkkg\AppData\Local\Temp\bundle_check.mjs', encoding='utf-8').read().split('\n')
print('total lines', len(lines))
for ln in (8777, 8778, 8779, 8780, 8781):
    print('--- line', ln, 'len', len(lines[ln-1]) if ln-1 < len(lines) else 'OOB')
    print((lines[ln-1] if ln-1 < len(lines) else '')[:600])

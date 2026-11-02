t = open('assets/template.html', encoding='utf-8').read()
def show(name, pat, pre=100, ctx=2600):
    i = t.find(pat)
    print('===', name, 'idx', i, 'count', t.count(pat))
    if i < 0:
        print('NOT FOUND'); print(); return
    print(t[max(0,i-pre):i+ctx].replace('\n',' ')[:3000]); print()
show('Ua_rest', '}else i', 0, 900)
show('wi_full', 'Bi={t0:', 0, 900)
show('Vp', '/* 鸟瞰→漫游', 0, 3400)
show('Bv_lights', 'Oa=new _h(', 600, 1300)
show('dir_shadow', 'new FK(', 300, 700)

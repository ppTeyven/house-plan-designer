import pathlib,re
t=pathlib.Path('assets/template.html').read_text(encoding='utf-8')
# 3D furniture builder is function kv; dump the switch cases for our targets
for key in ['case"cabinet":','case"sideboard":','case"bookshelf":','case"chest":','case"fridge":',
            'case"tvCabinet":','case"chandelier":','case"floorLamp":','case"deskLamp":','case"counter":',
            'case"bathtub":','case"washer":','case"diningTable":','case"officeChair":','case"armchair":',
            'case"mirrorCabinet":','case"displayCabinet":','case"wineCabinet":','case"nightstand":']:
    ps=[m.start() for m in re.finditer(re.escape(key),t)]
    # 3D one is the one with 'L(' inside nearby
    best=None
    for p in ps:
        seg=t[p:p+900]
        if 'L(' in seg and 'n,' in seg:
            best=p; break
    if best is None and ps: best=ps[0]
    print('KEY',key,best)
    if best:
        print(t[best:best+700].replace('\n',' | '))
    print('-----')

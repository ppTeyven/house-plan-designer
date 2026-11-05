import pathlib,re
t=pathlib.Path('assets/template.html').read_text(encoding='utf-8')
for kw in ['case"wall"','case"floor"','case"window"','case"door"','case"glassWall"','case"slat"','case"rug"']:
    ps=[m.start() for m in re.finditer(re.escape(kw), t)]
    print(kw, ps[:6])

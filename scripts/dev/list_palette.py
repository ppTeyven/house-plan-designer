"""从 assets/template.html 挖出真实的家具调色板清单（key/type/name），作为验收站与建模的总目录。"""
import pathlib, re, json, sys
from collections import defaultdict

t = pathlib.Path('assets/template.html').read_text(encoding='utf-8')
items = re.findall(r'\{key:"([^"]+)",type:"([^"]+)",name:"([^"]+)"', t)
print('palette total =', len(items))

bytype = defaultdict(list)
for k, ty, nm in items:
    bytype[ty].append((k, nm))

print('--- distinct types =', len(bytype))
for ty in sorted(bytype, key=lambda x: -len(bytype[x])):
    lst = bytype[ty]
    print(f'{ty:<14} {len(lst):>3}  ' + ', '.join(n for _, n in lst[:8]))

# 存成 JSON 供验收站使用
out = {}
for ty, lst in bytype.items():
    out[ty] = [{"key": k, "name": nm} for k, nm in lst]
pathlib.Path('scripts/dev/_palette.json').write_text(
    json.dumps(out, ensure_ascii=False, indent=1), encoding='utf-8')
print('\nwrote scripts/dev/_palette.json')
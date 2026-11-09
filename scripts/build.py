"""
把 HouseSpec（户型描述 JSON）注入设计器模板，生成单文件 HTML。

用法:
  python build.py spec.json -o 输出.html [--template ../assets/template.html] [--no-underlay]

spec.json 里可选的 "underlay": {"image": "原图路径", "mmPerPx": 17.65, "x": -4410, "y": -1340}
  会把原图作为底图打包进去（默认隐藏，可在左侧“户型”面板勾选显示，用来对照）。
  x, y = 图片左上角在户型坐标系里的位置（mm）。analyze.py 生成的 draft.json 已经算好。
"""
import argparse, base64, hashlib, io, json, os, re, sys
from PIL import Image

sys.stdout.reconfigure(encoding='utf-8')
here = os.path.dirname(os.path.abspath(__file__))
ap = argparse.ArgumentParser()
ap.add_argument('spec')
ap.add_argument('-o', '--out', required=True)
ap.add_argument('--template', default=os.path.join(here, '..', 'assets', 'template.html'))
ap.add_argument('--no-underlay', action='store_true')
ap.add_argument('--no-tex', action='store_true',
                help='不内嵌 PBR 贴图（产物离线打开会因缺 furnlib/ 而全是白墙白地）')
ap.add_argument('--tex-full', action='store_true',
                help='内嵌 ao 通道（+约 6MB）')
ap.add_argument('--tex-size', type=int, default=1024, help='内嵌贴图长边像素（默认 1024）')
ap.add_argument('--tex-quality', type=int, default=72, help='内嵌贴图 JPEG 质量（默认 72）')
ap.add_argument('--tex-data-size', type=int, default=512,
                help='内嵌数据通道（normal/rough/ao）的长边像素（默认 512）。'
                     '这三张只参与法线/粗糙度/遮蔽计算，看不出分辨率差别，'
                     '但体积和 GPU 上传量（texSubImage2D）直接按面积缩。')
a = ap.parse_args()

spec = json.load(open(a.spec, encoding='utf-8'))

def build_tex_manifest(a, html):
    """把模板真正用到的 PBR 贴图转成 base64 data URL。

    离线单文件 HTML 旁边没有 furnlib/ 目录，相对路径必然 404，
    材质会永远停在 1x1 白色占位 -> 整片白墙白地。
    这里按【模板里实际引用的基名】收集，避免把 200MB 全量塞进去。"""
    tex_dir = os.path.join(os.path.dirname(os.path.abspath(a.template)), 'furnlib', 'tex')
    if not os.path.isdir(tex_dir):
        return {}
    need = set()
    m = re.search(r'const __SURF_ROLE=\{(.*?)\};', html, re.S)
    if m:
        need |= set(re.findall(r':"([a-z0-9_]+)"', m.group(1)))
    need |= set(re.findall(r'__archMat\("([a-z0-9_]+)"', html))
    need |= set(re.findall(r'tex:"([a-z0-9_]+)"', html))
    m = re.search(r'const __PBR_ROLES=\{(.*?)\};', html, re.S)
    if m:
        need |= set(re.findall(r':"([a-z0-9_]+)"', m.group(1)))
    need |= set(re.findall(r'"(role_[a-z0-9_]+)"', html))
    need.discard('auto')
    need.add('rough_linen')          # 布艺材质的法线/粗糙度通道
    # AO 通道必须一起内嵌：__surfMat / __applyPBR 会无条件挂 aoMap，
    # 少了它离线打开时 aoMap 404 -> 停在 1x1 白占位 -> 环境光遮蔽全失效（墙角、缝隙没有阴影层次）。
    chans = ['_col', '_nor', '_rough', '_ao']
    manifest = {}
    for base in sorted(need):
        for suf in chans:
            p = os.path.join(tex_dir, base + suf + '.jpg')
            if not os.path.exists(p):
                continue
            try:
                im = Image.open(p).convert('RGB')
            except Exception:
                continue
            w, h = im.size
            # 只有 albedo（_col）需要高分辨率 —— 它是用户直接看到的颜色/纹理。
            # normal / rough / ao 只参与光照计算，512 就够，
            # 而 GPU 上传（texSubImage2D）耗时按面积走，能省一半以上。
            target = a.tex_size if suf == '_col' else a.tex_data_size
            k = min(1.0, target / max(w, h))
            if k < 1:
                im = im.resize((max(1, round(w * k)), max(1, round(h * k))), Image.LANCZOS)
            buf = io.BytesIO()
            im.save(buf, 'JPEG', quality=a.tex_quality, optimize=True)
            manifest[base + suf] = 'data:image/jpeg;base64,' + base64.b64encode(buf.getvalue()).decode()
    return manifest

def pack_underlay(ul):
    p = ul['image'] if os.path.isabs(ul['image']) else os.path.join(os.path.dirname(os.path.abspath(a.spec)), ul['image'])
    im = Image.open(p).convert('RGB')
    w, h = im.size
    # 底图压成 JPEG，长边不超过 1600，控制文件体积
    k = min(1, 1600 / max(w, h))
    if k < 1: im = im.resize((round(w * k), round(h * k)), Image.LANCZOS)
    buf = io.BytesIO(); im.save(buf, 'JPEG', quality=85)
    return {'src': 'data:image/jpeg;base64,' + base64.b64encode(buf.getvalue()).decode(),
            'imgW': im.size[0], 'imgH': im.size[1], 'mmPerPx': ul['mmPerPx'] / k, 'x': ul.get('x', 0), 'y': ul.get('y', 0)}

preset = {'spec': spec}
if 'floors' in spec:
    # 整栋楼：每层可以有自己的底图（原图里这一层的那张平面）
    uls = [fl.pop('underlay', None) for fl in spec['floors']]
    if any(uls) and not a.no_underlay: preset['underlays'] = [pack_underlay(u) if u else None for u in uls]
else:
    ul = spec.pop('underlay', None)
    if ul and not a.no_underlay: preset['underlay'] = pack_underlay(ul)
body = json.dumps(preset, ensure_ascii=False, separators=(',', ':'))
preset['id'] = hashlib.sha1(body.encode()).hexdigest()[:12]  # 户型变了 id 就变，浏览器不会拿旧存档覆盖新户型

html = open(a.template, encoding='utf-8').read()
# 去掉模板里可能残留的预设，再紧跟 <meta charset> 插入（charset 必须留在文件开头）
html = re.sub(r'<script id="__preset">.*?</script>', '', html, count=1, flags=re.S)
html = re.sub(r'<script id="__tex"[^>]*>.*?</script>', '', html, count=1, flags=re.S)
m = re.search(r'<meta charset[^>]*>', html, re.I)
js = json.dumps(preset, ensure_ascii=False, separators=(',', ':')).replace('<', '\\u003c')
html = html[:m.end()] + f'<script id="__preset">window.__PRESET__={js}</script>' + html[m.end():]

# ---------- 内嵌 PBR 贴图（离线单文件必须）----------
# 模板用相对路径 "furnlib/tex/xxx.jpg" 取贴图。产物是【单文件 HTML】，
# 双击离线打开时旁边没有 furnlib/ 目录 -> Image.onerror -> 材质停在 1x1 白占位
# -> 整面墙、整块地板全是纯白。这里把用到的贴图转成 base64 内嵌进 HTML，
# 模板启动时读 <script id="__tex"> 优先用内嵌图。
tex_manifest = {}
if not a.no_tex:
    try:
        tex_manifest = build_tex_manifest(a, html)
    except Exception as e:
        print('warn: 内嵌贴图失败 -> %s' % e, file=sys.stderr)
if tex_manifest:
    tjs = json.dumps(tex_manifest, ensure_ascii=False, separators=(',', ':')).replace('<', '\\u003c')
    # 内容写【纯 JSON】, 不带 window.__TEX_EMBED= 前缀 ——
    # 模板侧统一用 JSON.parse(el.textContent) 读, 带前缀会解析失败 -> 内嵌表为空 -> 全白。
    html = html[:m.end()] + f'<script id="__tex" type="application/json">{tjs}</script>' + html[m.end():]

name = spec.get('name')
if name: html = re.sub(r'<title>.*?</title>', f'<title>{name} · 装修设计器</title>', html, count=1, flags=re.S)
os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
open(a.out, 'w', encoding='utf-8').write(html)
fl = spec.get('floors') or [spec]
print(json.dumps({'out': os.path.abspath(a.out), 'kb': round(len(html.encode()) / 1024), 'floors': len(fl), 'walls': sum(len(f.get('walls', [])) for f in fl),
                  'rooms': sum(len(f.get('rooms', [])) for f in fl), 'tex': len(tex_manifest),
                  'underlay': 'underlay' in preset or 'underlays' in preset}, ensure_ascii=False))

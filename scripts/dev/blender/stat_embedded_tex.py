"""统计 furnlib 全部 GLB 里【嵌入式贴图】的占比。

关键问题：kv() 里只有材质名以 "U_" 开头的才被 __furnMat() 换成外部 PBR 贴图。
如果所有材质的名字都是 U_xxx，那 GLB 内嵌的 JPEG 就是【彻底的死重】——
下载了 4.45MB，从头到尾没被用过。
"""
import io, json, os, struct

FURN = r'D:\house planner\house-plan-designer-main\assets\furnlib'


def load(fn):
    blob = io.open(os.path.join(FURN, fn), 'rb').read()
    off = 12
    js, bin_ = None, b''
    while off + 8 <= len(blob):
        clen, ctype = struct.unpack('<II', blob[off:off + 8])
        data = blob[off + 8:off + 8 + clen]
        if ctype == 0x4E4F534A:
            js = json.loads(data.decode('utf-8'))
        elif ctype == 0x004E4942:
            bin_ = data
        off += 8 + clen
    return js, bin_, len(blob)


rows = []
for fn in sorted(os.listdir(FURN)):
    if not fn.endswith('.glb'):
        continue
    js, bin_, total = load(fn)
    mats = [m.get('name', '') for m in (js.get('materials') or [])]
    non_u = [m for m in mats if not m.startswith('U_')]
    # 嵌图字节
    img_bytes = 0
    for im in (js.get('images') or []):
        bv = im.get('bufferView')
        if bv is not None:
            img_bytes += js['bufferViews'][bv]['byteLength']
    # 几何字节 = bin - img
    geo_bytes = len(bin_) - img_bytes
    rows.append(dict(name=fn[:-4], total=total, img=img_bytes, geo=geo_bytes,
                     mats=len(mats), non_u=non_u))

tot_total = sum(r['total'] for r in rows)
tot_img = sum(r['img'] for r in rows)
tot_geo = sum(r['geo'] for r in rows)
all_u = [r for r in rows if not r['non_u']]

print('文件数            :', len(rows))
print('总体积            : %.1f MB' % (tot_total / 1048576))
print('  其中【嵌图】    : %.1f MB  (%.0f%%)' % (tot_img / 1048576, 100 * tot_img / tot_total))
print('  其中【几何】    : %.1f MB  (%.0f%%)' % (tot_geo / 1048576, 100 * tot_geo / tot_total))
print()
print('材质全部是 U_* 前缀（=嵌图必为死重）的文件数: %d / %d' % (len(all_u), len(rows)))
dead = sum(r['img'] for r in all_u)
print('  这些文件里的嵌图总量: %.1f MB' % (dead / 1048576))
print()
print('含非 U_ 材质（嵌图真在用）的文件:')
for r in rows:
    if r['non_u']:
        print('   %-18s mats=%s 非U=%s  嵌图 %.2fMB' % (
            r['name'], r['mats'], r['non_u'][:3], r['img'] / 1048576))

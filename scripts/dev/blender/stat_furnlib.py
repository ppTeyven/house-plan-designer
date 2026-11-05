"""统计 furnlib 全部 GLB 的三角面数 / 顶点数 / 材质数 / 网格数。

用于定位帧率与首屏加载的瓶颈：
  · 三角面总数 → 3D 渲染的每帧成本
  · 网格数     → draw call 数（每件家具几个 draw call）
  · 材质数     → 材质切换 / shader 编译成本
"""
import io
import json
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
FURN = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))))), 'assets', 'furnlib')

CT_JSON = 0x4E4F534A
CT_BIN = 0x004E4942


def load_glb(path):
    with io.open(path, 'rb') as f:
        blob = f.read()
    off = 12
    js, bin_ = None, b''
    while off + 8 <= len(blob):
        clen, ctype = struct.unpack('<II', blob[off:off + 8])
        data = blob[off + 8:off + 8 + clen]
        if ctype == CT_JSON:
            js = json.loads(data.decode('utf-8'))
        elif ctype == CT_BIN:
            bin_ = data
        off += 8 + clen
    return js, bin_, len(blob)


def stat(path):
    js, bin_, size = load_glb(path)
    tris = 0
    verts = 0
    prims = 0
    for m in js.get('meshes') or []:
        for p in m.get('primitives') or []:
            prims += 1
            pos = p.get('attributes', {}).get('POSITION')
            if pos is not None:
                verts += js['accessors'][pos]['count']
            idx = p.get('indices')
            if idx is None:
                tris += (js['accessors'][pos]['count'] // 3) if pos else 0
            else:
                tris += js['accessors'][idx]['count'] // 3
    mats = len(js.get('materials') or [])
    imgs = len(js.get('images') or [])
    return {
        'tris': tris, 'verts': verts, 'prims': prims,
        'mats': mats, 'imgs': imgs, 'size': size,
        'nodes': len(js.get('nodes') or []),
    }


if __name__ == '__main__':
    rows = []
    for fn in sorted(os.listdir(FURN)):
        if not fn.endswith('.glb'):
            continue
        s = stat(os.path.join(FURN, fn))
        s['name'] = fn[:-4]
        rows.append(s)
    rows.sort(key=lambda r: -r['tris'])
    print('%-18s %10s %10s %6s %6s %6s %9s' % (
        'model', 'tris', 'verts', 'prims', 'mats', 'imgs', 'MB'))
    print('-' * 76)
    for r in rows[:30]:
        print('%-18s %10d %10d %6d %6d %6d %9.2f' % (
            r['name'], r['tris'], r['verts'], r['prims'], r['mats'],
            r['imgs'], r['size'] / 1048576))
    print('-' * 76)
    print('总计: 三角面 %s  顶点 %s  primitive %d  文件 %d  体积 %.1f MB'
          % ('{:,}'.format(sum(r['tris'] for r in rows)),
             '{:,}'.format(sum(r['verts'] for r in rows)),
             sum(r['prims'] for r in rows), len(rows),
             sum(r['size'] for r in rows) / 1048576))
    print('前 50 名占比: 三角面 %.0f%%  体积 %.0f%%'
          % (100 * sum(r['tris'] for r in rows[:50]) / sum(r['tris'] for r in rows),
             100 * sum(r['size'] for r in rows[:50]) / sum(r['size'] for r in rows)))

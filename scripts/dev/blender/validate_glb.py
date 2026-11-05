"""校验剥图后的 GLB 是否仍是合法 glTF（能�� Three.js GLTFLoader 解析）。

检查项：
  1. buffer / bufferView / accessor 索引链条完整且在范围内
  2. buffer.byteLength 与实际 BIN 长度一致
  3. 没有残留的 texture / image 引用
  4. 节点 / mesh 引用的 accessor 都在范围内
  5. 单 buffer 假设是否成立（多 buffer 文件要单独处理）
"""
import io
import json
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from strip_glb_textures import read_glb  # noqa


def validate(js, bin_data):
    errs = []
    buffers = js.get('buffers') or []
    bvs = js.get('bufferViews') or []
    accs = js.get('accessors') or []

    # 1) buffers
    if len(buffers) > 1:
        errs.append('multi-buffer(%d)' % len(buffers))
    for i, b in enumerate(buffers):
        if i == 0 and len(bin_data) < b.get('byteLength', 0):
            errs.append('buffer0.byteLength %d > bin %d' % (b.get('byteLength'), len(bin_data)))

    # 2) bufferViews
    for i, bv in enumerate(bvs):
        if bv.get('buffer', 0) != 0:
            errs.append('bv%d.buffer=%s' % (i, bv.get('buffer')))
        off = bv.get('byteOffset', 0)
        ln = bv.get('byteLength', 0)
        if off + ln > len(bin_data):
            errs.append('bv%d range %d..%d exceeds bin %d' % (i, off, off + ln, len(bin_data)))
        if 'byteStride' in bv:
            st = bv['byteStride']
            if st < 4 or st > 252 or st % 4 != 0:
                errs.append('bv%d bad byteStride %s' % (i, st))

    # 3) accessors
    for i, a in enumerate(accs):
        bv = a.get('bufferView')
        if bv is None:
            continue
        if bv >= len(bvs):
            errs.append('acc%d -> bv%d out of range' % (i, bv))
            continue
        bv2 = bvs[bv]
        ncomp = {'SCALAR': 1, 'VEC2': 2, 'VEC3': 3, 'VEC4': 4, 'MAT2': 4,
                 'MAT3': 9, 'MAT4': 16}.get(a.get('type'), 1)
        csize = {5120: 1, 5121: 1, 5122: 2, 5123: 2, 5125: 4, 5126: 4}.get(a.get('componentType'), 4)
        need = a.get('count', 0) * ncomp * csize
        stride = bv2.get('byteStride') or need
        have = bv2.get('byteLength', 0)
        if need > have and not bv2.get('byteStride'):
            errs.append('acc%d needs %d bytes but bv%d has %d' % (i, need, bv, have))
        sp = a.get('sparse')
        if isinstance(sp, dict):
            for part in ('indices', 'values'):
                q = sp.get(part) or {}
                qb = q.get('bufferView')
                if qb is not None and qb >= len(bvs):
                    errs.append('acc%d sparse %s -> bv%d out of range' % (i, part, qb))

    # 4) 残留贴图引用
    if js.get('images'):
        errs.append('images remain')
    if js.get('textures'):
        errs.append('textures remain')
    for i, m in enumerate(js.get('materials') or []):
        pbr = m.get('pbrMetallicRoughness') or {}
        for k in ('baseColorTexture', 'metallicRoughnessTexture'):
            if k in pbr:
                errs.append('mat%d still has %s' % (i, k))
        for k in ('normalTexture', 'occlusionTexture', 'emissiveTexture'):
            if k in m:
                errs.append('mat%d still has %s' % (i, k))

    # 5) mesh / node 引用
    for i, mesh in enumerate(js.get('meshes') or []):
        for j, p in enumerate(mesh.get('primitives') or []):
            for an, ai in (p.get('attributes') or {}).items():
                if ai >= len(accs):
                    errs.append('mesh%d prim%d attr %s -> acc%d OOR' % (i, j, an, ai))
            idx = p.get('indices')
            if idx is not None and idx >= len(accs):
                errs.append('mesh%d prim%d indices -> acc%d OOR' % (i, j, idx))
    for i, n in enumerate(js.get('nodes') or []):
        if n.get('mesh') is not None and n['mesh'] >= len(js.get('meshes') or []):
            errs.append('node%d -> mesh%d OOR' % (i, n['mesh']))

    return errs


if __name__ == '__main__':
    d = sys.argv[1]
    files = sorted(f for f in os.listdir(d) if f.endswith('.glb'))
    bad = 0
    for fn in files:
        js, bin_ = read_glb(os.path.join(d, fn))
        errs = validate(js, bin_)
        if errs:
            bad += 1
            print('!! %-24s %s' % (fn, '; '.join(errs[:4])))
    print()
    print('校验 %d 个文件，异常 %d 个' % (len(files), bad))

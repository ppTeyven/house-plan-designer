"""独立校验：直接读 furnlib/*.glb，用几何高度剖面判断「床头/靠背在哪一端」。

判定规则（不依赖任何构建脚本的假设，只看最终二进制）：
  把模型按 Z 轴均分若干段，统计每段的顶点最大高度。
  床 / 沙发 / 椅：靠背端应显著高于另一端 → 靠背端 = 真正靠墙端。
  约定：house planner 里床头/靠背 = -Z 端（与 2D 平面图 -a 一致）。
  所以期望：-Z 半段的最大高度 > +Z 半段的最大高度。

输出：每件家具 zLow(=-Z端) 与 zHigh(=+Z端) 的最大高度，PASS/FAIL。
"""
import io
import json
import math
import os
import struct
import sys

FURN = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))))), 'assets', 'furnlib')

# 需要靠背在 -Z 的家具（床/沙发/椅/榻）
NEED_BACK_MINUS_Z = {
    'bed12', 'bed15', 'bed18', 'bed20', 'kingBed', 'kidsBed', 'bunkBed',
    'dayBed', 'roundBed', 'petBed', 'bedBench',
    'sofa', 'loveseat', 'singleSofa', 'lSofa', 'chaiseSofa', 'uSofa',
    'curvedSofa', 'bendSofa', 'theaterSofa', 'booth', 'officeSofa', 'fourSofa',
    'armchair', 'officeChair', 'trainingChair', 'rockingChair', 'gamingChair',
    'armDiningChair', 'readingChair', 'chair', 'hangingChair',
}

# 允许正负误差（米）：两半高度差要大于这个值才算真的有靠背
EPS = 0.05


def load_glb(path):
    with io.open(path, 'rb') as f:
        data = f.read()
    magic, version, total = struct.unpack('<III', data[:12])
    assert magic == 0x46546C67, 'not a glb'
    off = 12
    chunks = {}
    while off < total:
        clen, ctype = struct.unpack('<II', data[off:off + 8])
        cdata = data[off + 8:off + 8 + clen]
        chunks[ctype] = cdata
        off += 8 + clen + ((4 - clen % 4) % 4 if clen % 4 else 0)
    j = json.loads(chunks[0x4E4F534A].decode('utf-8'))
    bin_ = chunks.get(0x004E4942, b'')
    return j, bin_


CT = {5120: ('b', 1), 5121: ('B', 1), 5122: ('h', 2),
      5123: ('H', 2), 5125: ('I', 4), 5126: ('f', 4)}
NC = {'SCALAR': 1, 'VEC2': 2, 'VEC3': 3, 'VEC4': 4, 'MAT4': 16}


def node_world(j, bin_):
    """返回 {mesh_index: (world_min[3], world_max[3])}"""
    nodes = j.get('nodes', [])
    # 父节点 -> 子节点
    child_of = {}
    for i, n in enumerate(nodes):
        for c in n.get('children', []):
            child_of[c] = i

    def local(i):
        n = nodes[i]
        return n.get('matrix') or (
            [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1]
            if 'matrix' not in n else None)

    def mat_of(i):
        n = nodes[i]
        if 'matrix' in n:
            return [list(n['matrix'])]
        if 'children' in n or i in child_of:
            # 组合：先算自身TRS，再乘子
            t = n.get('translation', [0, 0, 0])
            r = n.get('rotation', [0, 0, 0, 1])
            s = n.get('scale', [1, 1, 1])
            return None, (t, r, s)
        return [list(n.get('matrix', [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1]))], None

    def trs_mat(t, r, s):
        x, y, z, w = r
        x2, y2, z2 = x + x, y + y, z + z
        xx, xy, xz = x * x2, x * y2, x * z2
        yy, yz, zz = y * y2, y * z2, z * z2
        wx, wy, wz = w * x2, w * y2, w * z2
        sx, sy, sz = s
        return [
            (1 - (yy + zz)) * sx, (xy + wz) * sx, (xz - wy) * sx, 0,
            (xy - wz) * sy, (1 - (xx + zz)) * sy, (yz + wx) * sy, 0,
            (xz + wy) * sz, (yz - wx) * sz, (1 - (xx + yy)) * sz, 0,
            t[0], t[1], t[2], 1]

    def mul(a, b):
        o = [0.0] * 16
        for i in range(4):
            for j in range(4):
                o[i * 4 + j] = sum(a[i * 4 + k] * b[k * 4 + j] for k in range(4))
        return o

    def basis(i):
        n = nodes[i]
        if 'matrix' in n:
            m = list(n['matrix'])
        else:
            m = trs_mat(n.get('translation', [0, 0, 0]),
                        n.get('rotation', [0, 0, 0, 1]),
                        n.get('scale', [1, 1, 1]))
        p = i
        while p in child_of:
            p = child_of[p]
            pn = nodes[p]
            if 'matrix' in pn:
                pm = list(pn['matrix'])
            else:
                pm = trs_mat(pn.get('translation', [0, 0, 0]),
                             pn.get('rotation', [0, 0, 0, 1]),
                             pn.get('scale', [1, 1, 1]))
            m = mul(pm, m)
        return m

    out = {}
    for i, n in enumerate(nodes):
        if 'mesh' not in n:
            continue
        m = basis(i)
        out.setdefault(n['mesh'], (m, []))[1].append(m)
    return j, bin_, out


def mesh_verts(j, bin_, mi):
    """返回该 mesh 全部顶点的世界坐标列表"""
    m = j['meshes'][mi]
    prim = m['primitives'][0]
    acc = j['accessors'][prim['attributes']['POSITION']]
    bv = j['bufferViews'][acc['bufferView']]
    fmt, size = CT[acc['componentType']]
    n = NC[acc['type']]
    off = bv.get('byteOffset', 0) + acc.get('byteOffset', 0)
    stride = bv.get('byteStride') or (size * n)
    base = bv.get('byteOffset', 0)
    res = []
    for k in range(acc['count']):
        p = base + off - bv.get('byteOffset', 0) + k * stride
        vals = struct.unpack_from('<' + fmt * n, bin_, p)
        res.append(vals)
    return res, j['nodes'], prim


def mesh_world_points(j, bin_, mesh_index, matrices):
    res = []
    for prim in j['meshes'][mesh_index]['primitives']:
        acc = j['accessors'][prim['attributes']['POSITION']]
        bv = j['bufferViews'][acc['bufferView']]
        fmt, size = CT[acc['componentType']]
        n = NC[acc['type']]
        vstride = bv.get('byteStride') or (size * n)
        base = bv.get('byteOffset', 0)
        astart = base + acc.get('byteOffset', 0)
        for m in matrices:
            for k in range(acc['count']):
                p = astart + k * vstride
                vals = struct.unpack_from('<' + fmt * n, bin_, p)
                if n < 3:
                    continue
                x, y, z = vals[0], vals[1], vals[2]
                res.append((
                    m[0] * x + m[4] * y + m[8] * z + m[12],
                    m[1] * x + m[5] * y + m[9] * z + m[13],
                    m[2] * x + m[6] * y + m[10] * z + m[14]))
    return res


def main():
    names = sorted(set(list(NEED_BACK_MINUS_Z)))
    rows = []
    fails = []
    for name in names:
        p = os.path.join(FURN, name + '.glb')
        if not os.path.exists(p):
            rows.append((name, 'MISSING', '', '', ''))
            fails.append(name + ' (missing)')
            continue
        j, bin_ = load_glb(p)
        # 收集所有 mesh -> world matrix 列表
        nodes = j.get('nodes', [])
        child_of = {}
        for i, n in enumerate(nodes):
            for c in n.get('children', []):
                child_of[c] = i

        def trs_mat(t, r, s):
            x, y, z, w = r
            x2, y2, z2 = x + x, y + y, z + z
            xx, xy, xz = x * x2, x * y2, x * z2
            yy, yz, zz = y * y2, y * z2, z * z2
            wx, wy, wz = w * x2, w * y2, w * z2
            sx, sy, sz = s
            return [
                (1 - (yy + zz)) * sx, (xy + wz) * sx, (xz - wy) * sx, 0,
                (xy - wz) * sy, (1 - (xx + zz)) * sy, (yz + wx) * sy, 0,
                (xz + wy) * sz, (yz - wx) * sz, (1 - (xx + yy)) * sz, 0,
                t[0], t[1], t[2], 1]

        def mul(a, b):
            o = [0.0] * 16
            for i in range(4):
                for j2 in range(4):
                    o[i * 4 + j2] = sum(a[i * 4 + k] * b[k * 4 + j2] for k in range(4))
            return o

        def basis(i):
            n = nodes[i]
            if 'matrix' in n:
                m = list(n['matrix'])
            else:
                m = trs_mat(n.get('translation', [0, 0, 0]),
                            n.get('rotation', [0, 0, 0, 1]),
                            n.get('scale', [1, 1, 1]))
            p = i
            while p in child_of:
                p = child_of[p]
                pn = nodes[p]
                pm = list(pn['matrix']) if 'matrix' in pn else trs_mat(
                    pn.get('translation', [0, 0, 0]),
                    pn.get('rotation', [0, 0, 0, 1]),
                    pn.get('scale', [1, 1, 1]))
                m = mul(pm, m)
            return m

        mesh_mats = {}
        for i, n in enumerate(nodes):
            if 'mesh' in n:
                mesh_mats.setdefault(n['mesh'], []).append(basis(i))

        pts = []
        for mi, mats in mesh_mats.items():
            pts.extend(mesh_world_points(j, bin_, mi, mats))
        if not pts:
            rows.append((name, 'NOPTS', '', '', ''))
            fails.append(name + ' (no points)')
            continue
        zmin = min(p[2] for p in pts)
        zmax = max(p[2] for p in pts)
        ymin = min(p[1] for p in pts)
        ymax = max(p[1] for p in pts)
        # 按 Z 分 10 段，统计每段内顶点相对 ymin 的最大高度
        NB = 10
        seg_h = [0.0] * NB
        span = max(zmax - zmin, 1e-9)
        for (x, y, z) in pts:
            k = min(NB - 1, int((z - zmin) / span * NB))
            h = y - ymin
            if h > seg_h[k]:
                seg_h[k] = h
        # 用两端各 25% 的【中位高度】比较：
        # - 中位数而不是最大值 → 避免 L 形/圆弧家具「另一端也有一根高杆」造成的假阴性
        # - 只取两端 25% → 避免「靠背只占中段」时半段最大���取值失真
        def med(vals):
            v = sorted(vals)
            return v[len(v) // 2] if v else 0.0
        edge = max(2, NB // 4)
        zlow = med(seg_h[:edge])     # -Z 端
        zhigh = med(seg_h[NB - edge:])  # +Z 端
        diff = zlow - zhigh
        ok = diff > EPS
        rows.append((name, 'PASS' if ok else 'FAIL',
                     '%.3f' % zlow, '%.3f' % zhigh, '%.3f' % diff))
        if not ok:
            fails.append('%s (-Z端%.3f vs +Z端%.3f)' % (name, zlow, zhigh))

    print('%-16s %-7s %9s %9s %9s' % ('model', 'result', 'back@-Z', 'back@+Z', 'diff'))
    print('-' * 60)
    for r in rows:
        print('%-16s %-7s %9s %9s %9s' % r)
    print('-' * 60)
    print('FAIL %d / %d' % (len(fails), len(rows)))
    for f in fails:
        print('  ! ' + f)
    return 1 if fails else 0


if __name__ == '__main__':
    sys.exit(main())

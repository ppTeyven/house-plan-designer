"""剥掉 GLB 里【从未被使用】的嵌入式贴图。

【为什么这是最大的一个性能坑 —— 实测数据】
  assets/furnlib/ 251 个 GLB 共 427.6 MB，其中：
      嵌图 370.0 MB (87%)
      几何  56.9 MB (13%)
  而浏览器实测（Runtime.evaluate 遍历场景材质）：
      外部贴图 1376 处 / 程序化 canvas 10 处 / 嵌入式 0 处
  → GLB 内嵌的 JPEG 从头到尾【一张都没被用到】。

【为什么用不到】
  kv() 里只有材质名以 "U_" 开头的才会被换成外部扫描 PBR：
      __x.material.name.indexOf("U_")===0 → __furnMat(role, color)
  249/251 个文件的材质名全是 U_* 前缀 → 它们的内嵌贴图必然被替换掉。
  剩下 2 个（miniHeater / wallClock）有非 U_ 材质，那两个的文件【保留贴图】。

【同时会做什么】
  1. 移除 images / textures / samplers，并清掉材质里对它们的引用
  2. 移除随之失效的 bufferView 与 BIN chunk 数据（真正把体积裁掉）
  3. 保留所有几何 accessor（POSITION/NORMAL/TEXCOORD/indices）不动
     → 顶点、UV、法线全部保留，画质零损失
  4. 材质保留 name / baseColorFactor / metallicFactor / roughnessFactor /
     doubleSided / alphaMode / alphaCutoff / extensions
     → 主程序 __furnMat() 用这些参数重造材质，画质不变

用法：
  python strip_glb_textures.py --apply                # 剥 furnlib 全部
  python strip_glb_textures.py --apply --dir <目录>   # 剥指定目录
"""
import io
import json
import os
import struct
import sys

CT_JSON = 0x4E4F534A
CT_BIN = 0x004E4942

# 材质里引用贴图的字段（glTF 2.0 规范 + 常用扩展）
# 材质里引用贴图的字段。
# 结构: (父对象名, 字段名)。父对象为 None 表示字段直接挂在 material 上。
TEX_FIELDS = [
    ('pbrMetallicRoughness', 'baseColorTexture'),
    ('pbrMetallicRoughness', 'metallicRoughnessTexture'),
    (None, 'normalTexture'),
    (None, 'occlusionTexture'),
    (None, 'emissiveTexture'),
]
# 扩展里的贴图引用
EXT_TEX_KEYS = [
    'KHR_materials_specular', 'KHR_materials_clearcoat',
    'KHR_materials_sheen', 'KHR_materials_transmission',
    'KHR_materials_iridescence', 'KHR_materials_volume',
    'KHR_materials_anisotropy',
]
EXT_TEX_SUB = ['specularTexture', 'clearcoatTexture', 'clearcoatRoughnessTexture',
               'sheenColorTexture', 'sheenRoughnessTexture', 'transmissionTexture',
               'iridescenceTexture', 'thicknessTexture', 'anisotropyTexture']


# =====================================================================
# GLB 读写
# =====================================================================
def read_glb(path):
    with open(path, 'rb') as f:
        data = f.read()
    if data[:4] != b'glTF':
        raise ValueError('not a GLB: %s' % path)
    off = 12
    js = None
    bin_data = b''
    while off < len(data):
        clen, ctype = struct.unpack_from('<II', data, off)
        off += 8
        chunk = data[off:off + clen]
        off += clen
        if ctype == CT_JSON:
            js = json.loads(chunk.decode('utf-8'))
        elif ctype == CT_BIN:
            bin_data = chunk
    if js is None:
        raise ValueError('no JSON chunk')
    return js, bin_data


def write_glb(js, bin_data, dest):
    json_bytes = json.dumps(js, separators=(',', ':')).encode('utf-8')
    json_bytes += b' ' * ((4 - len(json_bytes) % 4) % 4)
    bin_bytes = bin_data or b''
    if bin_bytes:
        bin_bytes = bin_bytes + b'\x00' * ((4 - len(bin_bytes) % 4) % 4)
    total = 12 + 8 + len(json_bytes) + (8 + len(bin_bytes) if bin_bytes else 0)
    out = bytearray()
    out += b'glTF'
    out += struct.pack('<II', 2, total)
    out += struct.pack('<II', len(json_bytes), CT_JSON)
    out += json_bytes
    if bin_bytes:
        out += struct.pack('<II', len(bin_bytes), CT_BIN)
        out += bin_bytes
    with open(dest, 'wb') as f:
        f.write(bytes(out))
    return len(out)


# =====================================================================
# 判断这个文件的贴图是否真的没用到
# =====================================================================
def strippable(js):
    """只有【所有材质的名字都是 U_* 前缀】时才可剥。

    非 U_ 材质（如 vintage_electric_kettle / wall_clock）走的是
    主程序 __furnMat 之外的路径，贴图是真在用的，不能动。
    """
    mats = js.get('materials') or []
    if not mats:
        return False, 'no materials'
    for m in mats:
        if not (m.get('name') or '').startswith('U_'):
            return False, 'non-U material: %s' % m.get('name')
    return True, 'ok'


def has_embedded_images(js):
    imgs = js.get('images') or []
    if not imgs:
        return False
    for im in imgs:
        if im.get('uri') is not None:
            return True  # 外链贴图，不能靠剥图省体积
    return True


# =====================================================================
# 剥图
# =====================================================================
def geometry_fingerprint(js, bin_data):
    """对所有几何 accessor 的原始字节做校验和。

    剥图前后必须完全一致 —— 这才能证明"只去掉了贴图，几何一字节没动"。
    """
    import hashlib
    h = hashlib.sha256()
    bvs = js.get('bufferViews') or []
    for a in (js.get('accessors') or []):
        bv = a.get('bufferView')
        if bv is None:
            continue
        b = bvs[bv]
        off = b.get('byteOffset', 0)
        ln = b.get('byteLength', 0)
        h.update(a.get('type', '').encode())
        h.update(struct.pack('<I', a.get('count', 0)))
        h.update(struct.pack('<I', a.get('componentType', 0)))
        h.update(bin_data[off:off + ln])
    return h.hexdigest()


def strip(js, bin_data):
    """返回 (新 js, 新 bin)。所有几何数据保持原样。"""
    js = json.loads(json.dumps(js))  # 深拷贝

    # 1) 记下哪些 bufferView 是纯贴图（后面要连数据一起删）
    bv_img = set()
    for im in (js.get('images') or []):
        bv = im.get('bufferView')
        if bv is not None:
            bv_img.add(bv)

    # 2) 材质：移除所有贴图引用
    for m in (js.get('materials') or []):
        for parent, key in TEX_FIELDS:
            if parent is None:
                m.pop(key, None)
            else:
                p = m.get(parent)
                if isinstance(p, dict):
                    p.pop(key, None)
                    if not p:
                        m.pop(parent, None)
        exts = m.get('extensions')
        if isinstance(exts, dict):
            for ek in EXT_TEX_KEYS:
                e = exts.get(ek)
                if isinstance(e, dict):
                    for sk in EXT_TEX_SUB:
                        e.pop(sk, None)

    # 3) 删掉 images / textures / samplers
    js.pop('images', None)
    js.pop('textures', None)
    js.pop('samplers', None)
    js.pop('extensionsUsed', None) if 'extensionsUsed' in js and \
        all(x.startswith('KHR_texture') for x in (js.get('extensionsUsed') or [])) else None

    # 4) 重建 bufferViews：只保留【被 accessor 真正引用】的，其余（贴图视图、
    #    以及导出器留下的未引用重复视图）全部丢弃，并压缩 buffer 重算 offset。
    #    注意：有些导出器会留一个覆盖整个几何区的"总视图"（如 plant.glb 的 bv16，
    #    offset=0 len=5.3MB，与 bv0..bv15 覆盖范围完全重复）——它不被任何 accessor
    #    引用，若照抄会把几何数据复制一遍，文件反而变大。
    used_bv = set()
    for a in (js.get('accessors') or []):
        bv = a.get('bufferView')
        if bv is not None:
            used_bv.add(bv)
        sp = a.get('sparse')
        if isinstance(sp, dict):
            for part in ('indices', 'values'):
                q = sp.get(part) or {}
                if q.get('bufferView') is not None:
                    used_bv.add(q['bufferView'])

    bvs = js.get('bufferViews') or []
    new_bvs = []
    remap = {}
    new_bin = bytearray()
    for i, bv in enumerate(bvs):
        if i in bv_img or i not in used_bv:
            continue  # 贴图视图 / 未被引用的重复视图 → 丢弃
        bv2 = dict(bv)
        src_off = bv.get('byteOffset', 0)
        length = bv.get('byteLength', 0)
        chunk = bin_data[src_off:src_off + length]
        # 对齐到 4 字节
        pad = (4 - len(new_bin) % 4) % 4
        if pad:
            new_bin += b'\x00' * pad
        bv2['byteOffset'] = len(new_bin)
        bv2['buffer'] = 0
        new_bin += chunk
        remap[i] = len(new_bvs)
        new_bvs.append(bv2)
    js['bufferViews'] = new_bvs

    # 5) accessor 的 bufferView 索引要重映射
    for a in (js.get('accessors') or []):
        bv = a.get('bufferView')
        if bv is not None:
            if bv not in remap:
                raise ValueError('accessor references dropped bufferView %d' % bv)
            a['bufferView'] = remap[bv]
        sp = a.get('sparse')
        if isinstance(sp, dict):
            for part in ('indices', 'values'):
                q = sp.get(part)
                if isinstance(q, dict) and q.get('bufferView') is not None:
                    if q['bufferView'] not in remap:
                        raise ValueError('sparse references dropped bufferView')
                    q['bufferView'] = remap[q['bufferView']]

    # 6) buffer 描述
    if new_bin:
        js['buffers'] = [{'byteLength': len(new_bin)}]
    else:
        js.pop('buffers', None)
        js.pop('bufferViews', None)
        for a in (js.get('accessors') or []):
            a.pop('bufferView', None)

    # 7) 场景里若引用了 sampler（rare），清理
    for n in (js.get('nodes') or []):
        pass  # glTF 里 sampler 只在 material/texture 上，已删

    return js, bytes(new_bin)


# =====================================================================
# 主流程
# =====================================================================
def process_dir(d, apply=False, only=None):
    files = sorted(f for f in os.listdir(d) if f.endswith('.glb'))
    if only:
        files = [f for f in files if f[:-4] in only]
    tot_before = tot_after = 0
    stripped = skipped = 0
    for fn in files:
        src = os.path.join(d, fn)
        js, bin_ = read_glb(src)
        size_before = os.path.getsize(src)
        tot_before += size_before
        ok, why = strippable(js)
        if not ok or not has_embedded_images(js):
            skipped += 1
            tot_after += size_before
            continue
        fp_before = geometry_fingerprint(js, bin_)
        js2, bin2 = strip(js, bin_)
        fp_after = geometry_fingerprint(js2, bin2)
        if fp_before != fp_after:
            print('  !! %s 几何校验和不一致，跳过' % fn)
            skipped += 1
            tot_after += size_before
            continue
        # 校验：几何 accessor 数量不变
        na = len(js.get('accessors') or [])
        nb = len(js2.get('accessors') or [])
        if na != nb:
            print('  !! %s accessor 数变了 %d -> %d，跳过' % (fn, na, nb))
            skipped += 1
            tot_after += size_before
            continue
        # 预估写盘体积（JSON + BIN，与 write_glb 同口径）
        jb = json.dumps(js2, separators=(',', ':')).encode('utf-8')
        jb += b' ' * ((4 - len(jb) % 4) % 4)
        bb = bin2 + b'\x00' * ((4 - len(bin2) % 4) % 4) if bin2 else b''
        est = 12 + 8 + len(jb) + (8 + len(bb) if bb else 0)
        if apply:
            tmp = src + '.tmp'
            write_glb(js2, bin2, tmp)
            # 校验能读回来，且几何 accessor 一致
            j3, b3 = read_glb(tmp)
            assert len(j3.get('accessors') or []) == na
            os.replace(tmp, src)
            est = os.path.getsize(src)
        size_after = est
        tot_after += size_after
        stripped += 1
        if stripped <= 12 or stripped % 50 == 0:
            print('  %-20s %7.2fMB -> %6.2fMB' % (
                fn, size_before / 1048576, size_after / 1048576))
    print()
    print('目录 %s' % d)
    print('  剥图 %d 个 / 保留 %d 个' % (stripped, skipped))
    print('  体积 %.1f MB -> %.1f MB  (省 %.1f MB, %.0f%%)' % (
        tot_before / 1048576, tot_after / 1048576,
        (tot_before - tot_after) / 1048576,
        100 * (tot_before - tot_after) / max(1, tot_before)))
    return stripped, skipped


if __name__ == '__main__':
    args = sys.argv[1:]
    apply = '--apply' in args
    dirs = []
    only = None
    i = 0
    while i < len(args):
        if args[i] == '--dir':
            dirs.append(args[i + 1]); i += 2
        elif args[i] == '--only':
            only = set(args[i + 1].split(',')); i += 2
        else:
            i += 1
    if not dirs:
        root = r'D:\house planner\house-plan-designer-main'
        dirs = [os.path.join(root, 'assets', 'furnlib'),
                os.path.join(root, '验收', 'models')]
    print('mode:', 'APPLY' if apply else 'DRY-RUN')
    for d in dirs:
        if not os.path.isdir(d):
            print('skip (not a dir):', d)
            continue
        process_dir(d, apply=apply, only=only)
        print()

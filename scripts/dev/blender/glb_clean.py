"""GLB 导入后的【场景清理与归一化】—— 所有渲染/分析脚本共用。

【重大坑 · 根因】
  Blender 的 glTF 导入器会保留启动场景里的【默认 Cube】(2×2×2 米)，
  它会带来三重破坏：
    1. 参与包围盒计算 → 相机取景被撑歪、模型偏出画面；
    2. 正视图（从 +Y 看）时【先撞到 Cube】→ 沙发被完全遮住，
       渲染出来是一片灰，看起来像"部件全部消失"；
    3. 分色诊断时多出一个 misc 组，干扰判断。
  实测：连续几次误判"沙发外壳不见了/法线反了/几何塌缩"，
        真凶都是这个 Cube，而射线测量（穿透式）证明几何完全正常。

  正确做法：导入前记录对象集合，导入后删掉【所有新出现的】对象。
  （按名字删 'Cube' 不可靠 —— 自建场景/已有文件里可能没有它，
   也可能有别的杂项。）

用法：
  from glb_clean import import_clean
  objs = import_clean(glb_path)      # 返回有效对象列表
  center, size = normalize_floor(objs)  # 落地 + 居中
"""
import bpy
import mathutils


def import_clean(path):
    """导入 GLB 并清掉导入器留下的杂项（默认 Cube 等）。返回有效对象列表。"""
    before = set(bpy.data.objects.keys())
    bpy.ops.import_scene.gltf(filepath=path)
    after = set(bpy.data.objects.keys())

    # 新出现的对象 = 导入器生成的（模型本体 + 默认 Cube）
    new_objs = [bpy.data.objects[k] for k in (after - before)]

    # 判定"杂项"：不在 GLB 节点树里的对象。
    # glTF 导入后 Blender 会把模型挂在 collection 里，
    # 而默认 Cube 直接落在 Scene Collection 根下。
    model_colls = set()
    for o in new_objs:
        for c in o.users_collection:
            model_colls.add(c)

    removed = []
    for o in new_objs:
        # 默认 Cube：名字为 Cube 且尺寸正好是 2×2×2（Blender 默认值）
        is_default_cube = False
        if o.type == 'MESH' and o.name in ('Cube', 'Cube.001'):
            bb = [o.matrix_world @ mathutils.Vector(c) for c in o.bound_box]
            if bb:
                dx = max(p.x for p in bb) - min(p.x for p in bb)
                dy = max(p.y for p in bb) - min(p.y for p in bb)
                dz = max(p.z for p in bb) - min(p.z for p in bb)
                if abs(dx - 2.0) < 1e-3 and abs(dy - 2.0) < 1e-3 \
                        and abs(dz - 2.0) < 1e-3:
                    is_default_cube = True
        if is_default_cube:
            removed.append(o.name)
            bpy.data.objects.remove(o, do_unlink=True)

    if removed:
        print("[glb_clean] removed stray objects: %s" % ", ".join(removed))

    # 有效对象 = 本次导入的 mesh
    valid = [o for o in new_objs if o.name not in removed and o.type == 'MESH']
    bpy.context.view_layer.update()
    return valid


def normalize_floor(objs):
    """把模型落地 + XY 居中。返回 (center, size)。"""
    mn = [1e9] * 3
    mx = [-1e9] * 3
    for o in objs:
        if o.type != 'MESH':
            continue
        for c in o.bound_box:
            w = o.matrix_world @ mathutils.Vector(c)
            for i in range(3):
                mn[i] = min(mn[i], w[i])
                mx[i] = max(mx[i], w[i])
    size = [mx[i] - mn[i] for i in range(3)]
    cx = (mn[0] + mx[0]) / 2
    cy = (mn[1] + mx[1]) / 2
    for o in objs:
        if o.type != 'MESH':
            continue
        o.location.x -= cx
        o.location.y -= cy
        o.location.z -= mn[2]
    bpy.context.view_layer.update()
    return (cx, cy, mn[2]), size


def bbox(objs):
    """返回 (min, max) 两个 Vector。"""
    mn = [1e9] * 3
    mx = [-1e9] * 3
    for o in objs:
        if o.type != 'MESH':
            continue
        for c in o.bound_box:
            w = o.matrix_world @ mathutils.Vector(c)
            for i in range(3):
                mn[i] = min(mn[i], w[i])
                mx[i] = max(mx[i], w[i])
    return (mathutils.Vector(mn), mathutils.Vector(mx))

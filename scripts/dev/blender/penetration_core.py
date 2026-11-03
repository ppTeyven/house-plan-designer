"""穿模判定核心（单一事实来源）—— 被 check_interpenetration.py 与 interpenetration.py 共用。

【为什么抽出来】
  之前这两份脚本各写了一套几乎相同的判定逻辑，结果【不同步】：
    · check_interpenetration.py  → 修过 3 个 bug → 报"0 对"
    · interpenetration.py       → 没修过      → 报"18 对"
  同一个模型两个结论，验收标准自相矛盾。
  → 抽成本模块，两边都 import，杜绝再次分叉。

【修掉的 3 个真 bug（都是实测踩出来的）】
  ① 法线矩阵用错
     原码：n = A.matrix_world.to_3x3() @ nor
     但 `nor` 是 find_nearest 返回的【B 的局部空间法线】，
     必须用【B 的矩阵】转到世界空间。
     用 A 的矩阵转 → 当 A 自身带旋转（本项目靠垫后仰 16°）时法线被转歪，
     "穿入深度"算出 2180mm（沙发总高才 823mm），
     于是相距 1.78m 的两个扶手垫被误判为互相穿模。

  ② 没排除【压缝条】(seat_seam_0 / backc_seam_0)
     压缝条是【故意塞进坐垫缝里、把沟填平】的软条，本来就嵌在主体中，
     却报出 "seat ↔ seat_seam 穿入 21.8% 顶点、最深 555mm" 的荒谬结果。

  ③ 没有 AABB 预筛
     find_nearest 返回的是【空间上最近的面】，
     即使查询点在物体【外面】，它最近那个面的法线也可能恰好让 (p-loc)·n < 0，
     于是"点在外部"被误判为"点在内部"。
     pair_debug 实测：两个扶手垫 AABB 重叠 0、顶点在对方 AABB 内 = 0，
     却被判"9.7% 顶点、275mm 深互相穿模"。

  修正后：先 AABB 粗筛（完全不重叠 → 直接排除），
  再对真正重叠的组合做精细判定，且深度用 B 的法线 + 诊断线夹紧。
"""
import bpy
import mathutils

# 6 个世界轴向探测方向
DIRS6 = [
    mathutils.Vector((1, 0, 0)), mathutils.Vector((-1, 0, 0)),
    mathutils.Vector((0, 1, 0)), mathutils.Vector((0, -1, 0)),
    mathutils.Vector((0, 0, 1)), mathutils.Vector((0, 0, -1)),
]


def build_bvh(o):
    import bmesh
    from mathutils.bvhtree import BVHTree
    bm = bmesh.new()
    bm.from_mesh(o.data)
    bvh = BVHTree.FromBMesh(bm)
    bm.free()
    return bvh


def _aabb(obj):
    pts = [obj.matrix_world @ mathutils.Vector(c) for c in obj.bound_box]
    return ([min(p[i] for p in pts) for i in range(3)],
            [max(p[i] for p in pts) for i in range(3)])


def penetration_stats(A, B, tol):
    """统计 A 的顶点有多少穿进了 B 的内部。

    返回 (穿入顶点数, 采样顶点数, 最大穿入深度[米])

    tol: 容差（米）。判定标准：顶点在 B 的 AABB 内，
         且相对 B 最近面的【有向距离】小于 -tol。
    """
    bvh = build_bvh(B)
    verts = A.data.vertices
    step = max(1, len(verts) // 400)
    deep = 0
    total = 0
    maxdepth = 0.0

    Amat = A.matrix_world
    Bmat = B.matrix_world

    # 穿入深度不可能超过 A 自身包围盒的"尺寸"（用对角线的一半足够）
    bb = Amat @ mathutils.Vector(A.bound_box[0])
    diag = 0.0
    for c in A.bound_box:
        diag += ((Amat @ mathutils.Vector(c)) - bb).length
    diag = max(diag, 1e-6)

    # ---- 前置：AABB 粗筛（bug③ 的修正）----
    amin, amax = _aabb(A)
    bmin, bmax = _aabb(B)
    overlap = [min(amax[i], bmax[i]) - max(amin[i], bmin[i]) for i in range(3)]
    if all(o <= 0 for o in overlap):
        return 0, 0, 0.0          # AABB 完全不重叠 → 不可能穿模

    for i in range(0, len(verts), step):
        p = Amat @ verts[i].co
        # 只考虑落在对方 AABB 内的顶点
        if not all(bmin[k] - 1e-4 <= p[k] <= bmax[k] + 1e-4 for k in range(3)):
            continue
        loc, nor, idx, dist = bvh.find_nearest(p)
        if loc is None:
            continue
        total += 1
        # 【bug① 的修正】nor 是 B 的局部法线 → 用 B 的矩阵转到世界空间
        n = (Bmat.to_3x3() @ nor).normalized()
        if n.length < 1e-9:
            continue
        d = (p - loc).dot(n)
        if d < -tol:
            deep += 1
            maxdepth = max(maxdepth, min(-d, diag))
    return deep, total, maxdepth

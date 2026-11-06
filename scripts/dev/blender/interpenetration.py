"""穿模检测（可复用模块）—— 供 make_manifest.py 作为第 8 项验收自检调用。

【为什么要有这条自检】
用户验收反馈原文："沙发墙有明显的穿模现象，整体依旧是简陋几何体拼凑的，不满意"
原 7 项自检（尺寸/面数/材质/落地/光影）全部通过，但用户一眼看出穿模 ——
说明验收标准本身缺了"部件互侵"这一维度。

【判据】
对每个主体部件，采样它的顶点，测该点相对对方网格【最近面】的穿透深度：
    d = (p - closest) · normal
d < -tol 表示该点已在对方【内侧】，即穿模。
统计穿透顶点占比，>1% 判定为穿模。

【为什么不用 AABB 重叠】
实测误报严重：滚边/针脚本来就该贴在坐垫上，AABB 几乎 100% 重叠。
必须用"表面是否穿进对方内部"来判断。

用法（在 Blender 内）：
    from interpenetration import scan_file
    res = scan_file("assets/furnlib/sofa.glb", tol_mm=2.0)
    res["issues"]  # [(名称A, 名称B, 穿透百分比, 最深mm), ...]
"""
import bpy
import math
import re

# 滚边 / 针脚 / 腿 —— 这些天然贴合主体，不构成穿模
SKIP_PREFIX = ("seat_pipe", "backc_pipe", "arm_pipe", "deck_pipe",
                "seatdeck_pipe", "back_pipe", "stitch", "seat_stitch",
                "seat_tuft", "arm_stitch", "alu_leg", "leg_cup", "back_stitch",
                "seat_seam", "backc_seam")
BODY_PREFIX = ("seat_", "backc_", "arm_pad_", "backrest", "back_wing",
               "arm_side", "seat_deck", "deck_", "corner_post")
_SUFFIX_RE = re.compile(r'_(pipe|stitch|tuft)(_\d+)*$')
_TRIM_RE = re.compile(r'_\d+$')

# 穿透顶点占比超过此值判定为穿模
PENETRATION_PCT = 1.0


def body_key(name):
    """主体名归并：backc_m0 → backc，seat_m0 → seat

    【v2 修正 · 实测踩坑】不能用 _SUFFIX_RE 剥掉 pipe/stitch 后再归并：
    那样会把滚边(seat_m0_pipe)与主体(seat_m0)并进同一组，
    组内两两比较时产生大量误报（实测 76.3% 穿入 667mm，
    而实际两个部件的 AABB 根本不重叠）。
    正确做法：滚边/针脚由 is_trim 识别并【完全排除在交叉比较之外】。
    """
    k = _SUFFIX_RE.sub('', name)
    k = _TRIM_RE.sub('', k)
    return k


# 【v3】压缝条（seat_seam_0 / backc_seam_0）：嵌在缝里填沟的软条，
#   故意嵌进主体，不参与穿模交叉比较。
_SEAM_RE = re.compile(r'_(seam)(_\d+)*$')


def is_trim(name):
    """滚边/针脚/压缝条类贴合件 —— 不参与穿模交叉比较"""
    if _SEAM_RE.search(name):
        return True
    return bool(_SUFFIX_RE.search(name))


def _bvh(o):
    import bmesh
    from mathutils.bvhtree import BVHTree
    bm = bmesh.new()
    bm.from_mesh(o.data)
    bvh = BVHTree.FromBMesh(bm)
    bm.free()
    return bvh


# 【v3 · 单一事实来源】
# 穿入判定统一复用 penetration_core.penetration_stats ——
# 那份实现修好了三个真 bug（法线矩阵用错 / 未排除压缝条 / 缺 AABB 预筛）。
# 详见 penetration_core.py 内的详细说明。
from penetration_core import penetration_stats as _penetration_stats  # noqa: E402


def _penetration(A, B, tol):
    """A 的顶点有多少穿进了 B 内部。返回 (穿入数, 采样数, 最深深度m)"""
    deep, total, maxd = _penetration_stats(A, B, tol)
    return deep, total, maxd


def scan_objects(objects, tol=0.002):
    """对 Blender 场景里的物体做穿模扫描，返回 issues 列表"""
    bodies = {}
    for o in objects:
        if o.type != 'MESH' or not o.data.polygons:
            continue
        if o.name.startswith(SKIP_PREFIX):
            continue
        if not o.name.startswith(BODY_PREFIX):
            continue
        # 滚边/针脚不参与比较
        if is_trim(o.name):
            continue
        bodies.setdefault(body_key(o.name), []).append(o)

    keys = sorted(bodies.keys())
    issues = []
    for i in range(len(keys)):
        for j in range(i + 1, len(keys)):
            for A in bodies[keys[i]]:
                for B in bodies[keys[j]]:
                    deep, total, maxd = _penetration(A, B, tol)
                    if total == 0:
                        continue
                    pct = deep / total * 100
                    if pct > PENETRATION_PCT:
                        issues.append((keys[i], keys[j], pct, maxd * 1000))
    return issues


def scan_file(path, tol_mm=2.0):
    """导入 GLB 并扫描（会清空当前场景）"""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    bpy.ops.import_scene.gltf(filepath=path)
    issues = scan_objects(list(bpy.context.scene.objects), tol=tol_mm / 1000.0)
    return {"issues": issues, "count": len(issues)}

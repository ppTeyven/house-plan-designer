"""穿模自检：检测家具【主体部件】之间的几何穿模。

【为什么必须有这条】
用户验收反馈原文："沙发墙有明显的穿模现象，整体依旧是简陋几何体拼凑的，不满意"
但原有 7 项自检里【没有穿模检测】 —— 尺寸/面数/材质/落地都过，
用户还是一眼看出穿模。说明验收标准本身有缺口。

【v2 判据修正（实测踩坑）】
v1 用"AABB 重叠体积比"判穿模，结果大量误报：
  · seat_0 ↔ seat_pipe_0  AABB 互侵 100%  ← 滚边本来就该贴在坐垫上
  · seat_0 ↔ seat_stitch_0_x  AABB 互侵 100%  ← 针脚本来就该缝在布上
原因是滚边/针脚是细长件，AABB 几乎完全落在坐垫的 AABB 里，
体积比自然接近 100%。

正确的穿模特征是【表面互相穿透】：
  · A 的面穿到 B 的内部（B 的 AABB 里），且不是"贴在表面"
  · 或 B 的面穿到 A 的内部
判定方法（比 AABB 可靠得多）：
  1. 对 A 的采样顶点，测它在 B 网格的【最近面】距离 d 和最近点法线 n
  2. 算 (p - closest) · n  → 若为负，说明 p 在 B 的【内侧】
  3. 统计"穿入深度 > tol"的顶点占比
  4. 占比 > 1% → 判定穿模

【只比较主体部件】
滚边(pipe_*)、针脚(stitch_*)、铝脚(alu_leg*)、脚杯(leg_cup*)、
绗缝(tuft_*) 都排除 —— 它们本来就该贴在主体上。

用法（Blender 内）：
  blender --background --python check_interpenetration.py -- <glb> [tol_mm]
"""
import bpy
import sys
import os
import re
import math

# 【v4 · 单一事实来源】穿入判定统一走 penetration_core，
# 避免与 interpenetration.py 两份拷贝不同步（一个报 0 对、一个报 18 对）。
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from penetration_core import penetration_stats, build_bvh  # noqa: E402

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
GLB = argv[0] if argv else None
TOL = float(argv[1]) / 1000.0 if len(argv) > 1 else 0.002

if not GLB:
    raise SystemExit("need a glb path")

bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
bpy.ops.import_scene.gltf(filepath=GLB)

# 排除这些前缀（它们天然贴合主体，不构成穿模）
SKIP_PREFIX = ("seat_pipe", "backc_pipe", "arm_pipe", "deck_pipe",
                "seatdeck_pipe", "back_pipe", "stitch", "seat_stitch",
                "seat_tuft", "arm_stitch", "alu_leg", "leg_cup", "back_stitch",
                "seat_seam", "backc_seam")
# 只在这些主体之间比对
BODY_PREFIX = ("seat_", "backc_", "arm_pad_", "backrest", "back_wing",
               "arm_side", "seat_deck", "deck_", "corner_post")
# 【v2 修正 · 实测踩坑】
# body_key 用正则把 seat_m0_pipe 归并成 seat_m0 —— 这是错的：
#   滚边(pipe)与主体(seat_m0)被放进同一组，组内两两比较时
#   "滚边 vs 滚边""滚边 vs 主体"会产生大量误报（实测 76.3% 穿入 667mm，
#   而实际 AABB 根本不重叠）。
# 修正：滚边/针脚单独成组，并且【不与主体交叉比较】——
#   它们本来就该贴在主体上，检测它们没有意义。
_SUFFIX_RE = re.compile(r'_(pipe|stitch|tuft)(_\d+)*$')
# 【v3】压缝条（seat_seam_0 / backc_seam_0）：嵌在缝里填沟的软条
_SEAM_RE = re.compile(r'_(seam)(_\d+)*$')
_TRIM_RE = re.compile(r'_\d+$')


def body_key(name):
    """主体名归并：backc_m0 → backc，seat_m0 → seat

    注意：只去掉末尾的数字序号，不去掉 pipe/stitch 后缀
    （那类零件由 is_trim 单独识别并排除交叉比较）。
    """
    k = _SUFFIX_RE.sub('', name)
    k = _TRIM_RE.sub('', k)
    return k


def is_trim(name):
    """是否是滚边/针脚/压缝条类贴合件（这些不与主体做穿模比较）

    【v3 修正 · 实测踩坑】
    原版只认 _pipe/_stitch/_tuft 后缀，漏掉了【压缝条】(seat_seam_0 / backc_seam_0)。
    压缝条是【故意塞进坐垫缝隙里、把沟填平】的软条 —— 它本来就该嵌进主体。
    但 body_key 会把它归成 "seat_seam" 组，和 "seat" 组做交叉比较，
    于是报出 "seat ↔ seat_seam 穿入 21.8% 顶点, 最深 555mm" 这类荒谬结果
    （555mm 比沙发坐垫本身还高，显然是误报）。
    → 现在把 seam 也归入贴合件，不参与主体穿模比较。
    """
    if _SEAM_RE.search(name):
        return True
    return bool(_SUFFIX_RE.search(name))


def main():
    meshes = [o for o in bpy.context.scene.objects
              if o.type == 'MESH' and len(o.data.polygons) > 0]
    bodies = {}
    for o in meshes:
        if o.name.startswith(SKIP_PREFIX):
            continue
        if not o.name.startswith(BODY_PREFIX):
            continue
        # 【v2】滚边/针脚不参与比较（它们本来就该贴在主体上）
        if is_trim(o.name):
            continue
        k = body_key(o.name)
        bodies.setdefault(k, []).append(o)

    keys = sorted(bodies.keys())
    print("=== 穿模检测 (tol=%.1fmm) ===" % (TOL * 1000))
    print("主体部件组 %d 个: %s" % (len(keys), ", ".join(keys)))

    issues = []
    for i in range(len(keys)):
        for j in range(i + 1, len(keys)):
            ka, kb = keys[i], keys[j]
            for A in bodies[ka]:
                for B in bodies[kb]:
                    deep, total, maxd = penetration_stats(A, B, TOL)
                    if total == 0:
                        continue
                    pct = deep / total * 100
                    if pct > 1.0:
                        issues.append((ka, kb, pct, maxd))
                        print("  ✗ %-14s ↔ %-14s 穿入 %5.1f%% 顶点, 最深 %6.1fmm"
                              % (ka, kb, pct, maxd * 1000))
                    elif deep > 0:
                        print("  · %-14s ↔ %-14s 轻微接触 %5.1f%% (≤1%% 视为正常贴合)"
                              % (ka, kb, pct))
    if not issues:
        print("  ✓ 所有主体部件之间无穿模")
    else:
        print("  ✗ %d 对存在穿模" % len(issues))
    return issues


if __name__ == "__main__":
    main()

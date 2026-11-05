"""沙发几何全面体检 —— 针对用户本轮 6 项投诉的【可测量】诊断。

【用户投诉】
 1. 视口没在看我操作的位置（live.py 的事，脚本外处理）
 2. 红线处滚边断断续续不平滑（锯齿感）
 3. 扶手侧面连接处穿模、不圆滑
 4. 上方穿过沙发的怪异线条 + 凹陷
 5. 纹理差，没有立体毛绒感
 6. 扶手单调、整体不干净

【本脚本做的事】
  真实构建整只沙发（跑 make_sofa_v18 的建模段），然后测量：
  A. 每个网格的法线一致性 / 硬棱数 / 退化面数 / 自交数
  B. 滚边管的环间距均匀性 + 切向转角突变（→ "断续"）
  C. 所有物件两两穿模统计（→ "穿模"）
  D. 找出【悬空】的细长物件（→ "穿过沙发的怪异线条"）
  E. 网格"干净度"总表

用法：blender --background --python audit_sofa.py -- /abs/path/to/out.json
"""
import bpy
import sys
import os
import json
import math
import bmesh
import mathutils

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

BL = "C:\\Program Files\\Blender Foundation\\Blender 4.5\\blender.exe"

# ---- 取命令行参数 ----
argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUTJSON = argv[0] if argv else os.path.join(HERE, "audit_sofa.json")

# =====================================================================
# 构建真实沙发
# =====================================================================
print("[AUDIT] 构建沙发 ...")
import make_sofa_v18 as MS   # 导入即构建

print("[AUDIT] 对象数:", len(bpy.context.scene.objects))

MESHES = [o for o in bpy.context.scene.objects if o.type == 'MESH']


# =====================================================================
# A. 每个网格的健康度
# =====================================================================
def mesh_health(o):
    """法线一致性 + 硬棱 + 退化面 + 非流形"""
    me = o.data
    bm = bmesh.new()
    bm.from_mesh(me)
    bm.faces.ensure_lookup_table()

    # --- 退化面（面积过小）---
    degen = sum(1 for f in bm.faces if f.calc_area() < 1e-7)

    # --- 硬棱：相邻面法线夹角 > 55° ---
    hard = 0
    for e in bm.edges:
        if len(e.link_faces) != 2:
            continue
        n0 = e.link_faces[0].normal
        n1 = e.link_faces[1].normal
        if n0.dot(n1) < math.cos(math.radians(55)):
            hard += 1

    # --- 非流形边 ---
    nonman = sum(1 for e in bm.edges if len(e.link_faces) > 2)

    # --- 边界边（不该有）---
    bound = sum(1 for e in bm.edges if len(e.link_faces) == 1)

    # --- 有符号体积（判断整体朝向）---
    vol = bm.calc_volume(signed=True)
    bm.free()
    return dict(name=o.name, verts=len(me.vertices), faces=len(me.polygons),
                degen=degen, hard=hard, nonman=nonman, bound=bound,
                vol=round(vol, 6))


print("[AUDIT] === A. 网格健康度 ===")
health = []
for o in MESHES:
    h = mesh_health(o)
    health.append(h)
    flag = ""
    if h['degen'] > 0:
        flag += " 退化面!"
    if h['hard'] > 2:
        flag += " 硬棱%d!" % h['hard']
    if h['nonman'] > 0:
        flag += " 非流形%d!" % h['nonman']
    if h['bound'] > 0:
        flag += " 边界边%d!" % h['bound']
    print("  %-22s v%-6d f%-6d deg%-4d hard%-5d nm%-4d bd%-4d%s"
          % (h['name'], h['verts'], h['faces'], h['degen'], h['hard'],
             h['nonman'], h['bound'], flag))

tot_hard = sum(h['hard'] for h in health)
tot_degen = sum(h['degen'] for h in health)
tot_nm = sum(h['nonman'] for h in health)
tot_bd = sum(h['bound'] for h in health)
print("  >>> 合计: 硬棱 %d / 退化面 %d / 非流形 %d / 边界边 %d"
      % (tot_hard, tot_degen, tot_nm, tot_bd))


# =====================================================================
# B. 滚边管的"断续"检测
# =====================================================================
def pipe_continuity(o, sides=20):
    """环间距均匀性 + 切向转角突变点"""
    bm = bmesh.new()
    bm.from_mesh(o.data)
    bm.verts.ensure_lookup_table()
    nv = len(bm.verts)
    nring = nv // sides
    if nring < 4:
        bm.free()
        return None
    rings = []
    for i in range(nring):
        vs = [bm.verts[i * sides + j] for j in range(sides)]
        rings.append(sum((v.co for v in vs), mathutils.Vector()) / sides)
    bm.free()

    steps = []
    for i in range(1, nring):
        steps.append((rings[i] - rings[i - 1]).length)

    # 切向转角
    turns = []
    for i in range(nring):
        if i == 0:
            t = rings[1] - rings[0]
        elif i == nring - 1:
            t = rings[-1] - rings[-2]
        else:
            t = rings[i + 1] - rings[i - 1]
        if t.length > 1e-9:
            turns.append((i, t.normalized()))

    angs = []
    for k in range(1, len(turns)):
        i0, t0 = turns[k - 1]
        i1, t1 = turns[k]
        angs.append((i1, math.degrees(t0.angle(t1))))

    ss = sorted(steps)
    n = len(ss)
    return dict(
        name=o.name, rings=nring,
        step_min=round(ss[0] * 1000, 2), step_med=round(ss[n // 2] * 1000, 2),
        step_max=round(ss[-1] * 1000, 2),
        turn_max=round(max((a for _, a in angs), default=0), 1),
        turn_gt25=sum(1 for _, a in angs if a > 25),
        turn_gt40=sum(1 for _, a in angs if a > 40),
        outliers=[(i, round(a, 1)) for i, a in angs if a > 40],
    )


print()
print("[AUDIT] === B. 滚边连续性 ===")
pipes = []
for o in MESHES:
    if o.name.startswith(("seat_pipe", "backc_pipe", "arm_pipe", "seat_seam_pipe",
                          "shell_shoulder", "shell_cap", "frame_pipe", "pillow")):
        c = pipe_continuity(o)
        if c:
            pipes.append(c)
            print("  %-24s 环%-4d 间距 %5.2f/%5.2f/%5.2fmm  转角max%-6.1f >25°:%-4d >40°:%-4d"
                  % (c['name'], c['rings'], c['step_min'], c['step_med'],
                     c['step_max'], c['turn_max'], c['turn_gt25'],
                     c['turn_gt40']))
            if c['outliers']:
                print("        突变环号:", c['outliers'][:14])


# =====================================================================
# C. 穿模检测
# =====================================================================
print()
print("[AUDIT] === C. 穿模检测 ===")
import penetration_core as PC

SKIP_PAIRS = set()
# 压缝条是故意嵌进去的
for k in range(2):
    SKIP_PAIRS.add(("seat_%d" % k, "seat_seam_%d" % k))
    SKIP_PAIRS.add(("seat_%d" % (k + 1), "seat_seam_%d" % k))
    SKIP_PAIRS.add(("backc_%d" % k, "backc_seam_%d" % k))
    SKIP_PAIRS.add(("backc_%d" % (k + 1), "backc_seam_%d" % k))

pen = []
for i, A in enumerate(MESHES):
    for B2 in MESHES[i + 1:]:
        key = tuple(sorted((A.name, B2.name)))
        if key in SKIP_PAIRS:
            continue
        try:
            d, t, md = PC.penetration_stats(A, B2, 1e-4)
        except Exception:
            continue
        if d > 0 and t > 0:
            ratio = d / t
            if ratio > 0.02:
                pen.append(dict(a=A.name, b=B2.name, deep=d, total=t,
                                ratio=round(ratio, 3),
                                max_mm=round(md * 1000, 1)))
pen.sort(key=lambda x: -x['ratio'])
print("  穿模对数(>2%%顶点):", len(pen))
for p in pen[:30]:
    print("    %-18s ↔ %-18s  %5.1f%% 顶点  最深 %6.1f mm"
          % (p['a'], p['b'], p['ratio'] * 100, p['max_mm']))


# =====================================================================
# D. 悬空/游离的细长物件
# =====================================================================
print()
print("[AUDIT] === D. 悬空/游离物件 ===")
for o in MESHES:
    bb = [o.matrix_world @ mathutils.Vector(c) for c in o.bound_box]
    mn = [min(p[i] for p in bb) for i in range(3)]
    mx = [max(p[i] for p in bb) for i in range(3)]
    size = [mx[i] - mn[i] for i in range(3)]
    diag = math.sqrt(sum(s * s for s in size))
    # "细长"= 最大边 > 3×第二边，且第二边很小
    srt = sorted(size, reverse=True)
    if srt[0] > 0.12 and srt[1] < 0.030 and diag > 0.12:
        print("  %-24s 尺寸 %.0f×%.0f×%.0f mm  ← 细长游离"
              % (o.name, size[0] * 1000, size[1] * 1000, size[2] * 1000))


# =====================================================================
# E. 总表
# =====================================================================
print()
print("[AUDIT] === E. 汇总 ===")
report = dict(
    objects=len(MESHES),
    total_hard=tot_hard, total_degen=tot_degen,
    total_nonmanifold=tot_nm, total_boundary=tot_bd,
    pipes=pipes, penetrations=pen,
    health=health,
)
with open(OUTJSON, "w", encoding="utf-8") as f:
    json.dump(report, f, ensure_ascii=False, indent=1)
print("[AUDIT] 写入", OUTJSON)
print("[AUDIT] ===== 完成 =====")

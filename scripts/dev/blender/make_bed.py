"""bed v1 — 软包床（William 同级标准：绗缝床头 + 厚床垫 + 被褶 + 真实缝线）
蓝图尺寸：W1800 D2000 H1100（1.8m 双人床）
"""
import bpy, math, os, sys, random, mathutils
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bl_lib as B
from palette import PAL, ROLES

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))),
                   "验收", "models", "bed.glb")
os.makedirs(os.path.dirname(OUT), exist_ok=True)
B.wipe()

R = ROLES["bed"]
M_UP = B.fabric("U_upholstery", PAL[R["main"]])
M_UPDK = B.fabric("U_upholsterydk", PAL[R["dark"]])
M_LINEN = B.fabric("U_fabric", PAL["fabric_cream"])
M_WELT = B.pbr("U_dark", PAL[R["welt"]], 0.72)
M_BRASS = B.pbr("U_brass", PAL[R["metal"]], 0.26, 1.0)
M_WOOD = B.wood("U_wood", PAL[R["leg"]])
M_THREAD = B.pbr("U_thread", PAL[R["thread"]], 0.88)

W, D = 1.80, 2.00
BED_H = 0.30           # 床架面高
MAT_T = 0.26          # 床垫厚
HEAD_H = 1.10         # 床头高
HEAD_T = 0.10         # 床头厚
objs = []

# ---------------- 床架（圆角包边 + 踢脚） ----------------
frame = B.box("bedframe", (W, D, BED_H), (0, 0, BED_H / 2), M_UP)
B.bevel(frame, 0.018, 3); B.subsurf(frame, 2)
objs.append(frame)

for sx in (-1, 1):
    for sy in (-1, 1):
        objs.append(B.cyl(f"foot_{sx}_{sy}", 0.030, 0.075,
                          (sx * (W / 2 - 0.09), sy * (D / 2 - 0.09), 0.0375),
                          M_BRASS, verts=16))

# ---------------- 绗缝床头（软包 + 菱格绗缝 + 扣子） ----------------
# 床头板是竖直面：grid() 建在 XY 平面，所以先建再绕 X 轴转到竖直。
# 床头板分 3×6 格，每格中心有拉扣凹陷
head = B.grid("headboard", W, HEAD_H, 60, (0, 0, 0), M_UP)
for v in head.data.vertices:
    u = v.co.x / (W / 2)
    zz = v.co.y / (HEAD_H / 2)          # 竖直方向用 y 表示
    s = abs(u + zz) + abs(u - zz)
    v.co.z -= 0.006 * math.sin(s * 9.5)  # 菱格绗缝褶皱（沿厚度方向）
    if abs(u) > 0.90 or abs(zz) > 0.90:
        v.co.z += 0.010                    # 边缘往回收（软包包裹感）
# 转到竖直并定位到床头位置（绕 X 轴 -90°：平面 y → 竖直 z，平面 z → 深度 y）
e_head = mathutils.Euler((math.radians(-90), 0, 0), 'XYZ').to_matrix()
for v in head.data.vertices:
    v.co = e_head @ v.co
    v.co += mathutils.Vector((0, D / 2 - HEAD_T / 2, HEAD_H / 2))
sm = head.modifiers.new("Solid", 'SOLIDIFY')
sm.thickness = HEAD_T
sm.offset = 0
for p in head.data.polygons:
    p.use_smooth = True
B.smart_uv(head)
objs.append(head)

# 绗缝扣（每格一个凹陷点）
NX, NZ = 3, 6
for ix in range(NX):
    for iz in range(NZ):
        cx = -W / 2 + (ix + 0.5) * W / NX
        cz = (iz + 0.5) * HEAD_H / NZ
        objs.append(B.sphere(f"tuft_{ix}_{iz}", 0.013, (cx, D / 2 - HEAD_T - 0.004, cz),
                             M_UPDK, seg=10, rings=6))

# 床头包边（竖向两条 + 顶部一条）
for sx in (-1, 1):
    objs.append(B.pipe_path(f"head_welt_{sx}", [
        (sx * (W / 2 - 0.012), D / 2 - HEAD_T - 0.002, 0.02),
        (sx * (W / 2 - 0.016), D / 2 - HEAD_T - 0.006, HEAD_H * 0.5),
        (sx * (W / 2 - 0.012), D / 2 - HEAD_T - 0.002, HEAD_H - 0.02),
    ], M_WELT, r=0.009))
objs.append(B.pipe_path("head_welt_top", [
    (-W / 2 + 0.012, D / 2 - HEAD_T - 0.002, HEAD_H - 0.014),
    (0, D / 2 - HEAD_T - 0.006, HEAD_H - 0.006),
    (W / 2 - 0.012, D / 2 - HEAD_T - 0.002, HEAD_H - 0.014),
], M_WELT, r=0.009))

# 床头针脚（沿顶边与两侧）
objs += B.stitch_line("head_stitch_top",
                      (-W / 2 + 0.03, D / 2 - HEAD_T - 0.010, HEAD_H - 0.05),
                      (W / 2 - 0.03, D / 2 - HEAD_T - 0.010, HEAD_H - 0.05),
                      M_THREAD, r=0.00085, lift=0.002)
for sx in (-1, 1):
    objs += B.stitch_line(f"head_stitch_side_{sx}",
                          (sx * (W / 2 - 0.03), D / 2 - HEAD_T - 0.010, 0.04),
                          (sx * (W / 2 - 0.03), D / 2 - HEAD_T - 0.010, HEAD_H - 0.05),
                          M_THREAD, r=0.00085, lift=0.002)

# ---------------- 床垫（高密 + 边缘滚边 + 绗缝格） ----------------
mat = B.grid("mattress", W - 0.04, D - 0.10, 56, (0, -0.03, BED_H + MAT_T / 2), M_LINEN)
for v in mat.data.vertices:
    ex = abs(v.co.x) / ((W - 0.04) / 2)
    ey = abs(v.co.y + 0.03) / ((D - 0.10) / 2)
    # 顶面绗缝格（4×8 格凹陷）
    gx = v.co.x / (W - 0.04) * 4
    gy = (v.co.y + 0.03) / (D - 0.10) * 8
    fx = abs(gx - math.floor(gx) - 0.5)
    fy = abs(gy - math.floor(gy) - 0.5)
    if v.co.z > BED_H + MAT_T * 0.5:
        v.co.z -= 0.004 * max(0.0, 1.0 - min(fx, fy) * 8.0)
    # 边缘外扩（床垫鼓出）
    if ex > 0.92 or ey > 0.92:
        v.co.x *= 1.012
        v.co.y = -0.03 + (v.co.y + 0.03) * 1.008
sm = mat.modifiers.new("Solid", 'SOLIDIFY')
sm.thickness = MAT_T
sm.offset = -1.0
for p in mat.data.polygons:
    p.use_smooth = True
B.smart_uv(mat)
objs.append(mat)

# 床垫顶面滚边（真实圆管）
objs.append(B.pipe_rect("mattress_welt", 0, -0.03, BED_H + MAT_T - 0.018,
                         W - 0.03, D - 0.09, M_WELT, r=0.011))
objs += B.stitch_rect("mattress_stitch", 0, -0.03, BED_H + MAT_T - 0.030,
                      W - 0.10, D - 0.16, M_THREAD, r=0.00085, inset=0.005, lift=0.002)

# ---------------- 枕头（两只，带蓬松感 + 枕套褶皱） ----------------
for i, px in enumerate((-W / 4, W / 4)):
    p = B.box(f"pillow_{i}", (0.62, 0.40, 0.15), (px, D / 2 - 0.32, BED_H + MAT_T + 0.055), M_LINEN)
    B.bevel(p, 0.062, 5); B.subsurf(p, 4)
    random.seed(i * 11 + 3)
    for v in p.data.vertices:
        v.co.z += (random.random() - 0.5) * 0.006
        if abs(v.co.x - px) > 0.24:
            v.co.z -= 0.008
    B.smart_uv(p)
    objs.append(p)
    # 枕套滚边
    objs.append(B.pipe_rect(f"pillow_welt_{i}", px, D / 2 - 0.32, BED_H + MAT_T + 0.012,
                             0.60, 0.38, M_WELT, r=0.006))

# ---------------- 被子（褶皱布料，搭过床尾） ----------------
# 被子只覆盖床面中后段，床尾下垂控制在床架范围内（总深不超过 D=2.0）
quilt = B.grid("quilt", W - 0.02, D * 0.66, 70, (0, -D * 0.02, BED_H + MAT_T + 0.045), M_UP)
random.seed(7)
for v in quilt.data.vertices:
    x, y = v.co.x, v.co.y
    # 主褶皱（横向铺开的被面）
    v.co.z += math.sin(y * 9.0) * 0.016 + math.sin(x * 5.5 + y * 2.0) * 0.010
    v.co.z += (random.random() - 0.5) * 0.006
    # 床尾下垂（控制在床尾沿 -1.0 之内）
    if y < -D * 0.30:
        t = min(1.0, (-D * 0.30 - y) / (D * 0.03 + 0.001))
        v.co.z -= t * 0.24
        v.co.y -= t * 0.008
    # 两侧垂边
    if abs(x) > W / 2 - 0.06:
        t = min(1.0, (abs(x) - (W / 2 - 0.06)) / 0.05)
        v.co.z -= t * 0.30
sm = quilt.modifiers.new("Solid", 'SOLIDIFY')
sm.thickness = 0.018
sm.offset = -1.0
for p in quilt.data.polygons:
    p.use_smooth = True
B.smart_uv(quilt)
objs.append(quilt)

# 被子滚边（前缘）
objs.append(B.pipe_path("quilt_welt", [
    (-W / 2 + 0.03, -D * 0.33, BED_H + MAT_T - 0.01),
    (-W * 0.25, -D * 0.345, BED_H + MAT_T + 0.005),
    (W * 0.25, -D * 0.345, BED_H + MAT_T + 0.005),
    (W / 2 - 0.03, -D * 0.33, BED_H + MAT_T - 0.01),
], M_WELT, r=0.008))

# ---------------- 床尾毯（搭毯） ----------------
throw = B.grid("throw", W - 0.04, 0.50, 40, (0, -D * 0.20, BED_H + MAT_T + 0.085), M_LINEN)
for v in throw.data.vertices:
    v.co.z += math.sin(v.co.x * 11.0) * 0.010 + math.sin(v.co.y * 19.0) * 0.005
sm = throw.modifiers.new("Solid", 'SOLIDIFY')
sm.thickness = 0.010
sm.offset = -1.0
for p in throw.data.polygons:
    p.use_smooth = True
B.smart_uv(throw)
objs.append(throw)

for o in objs:
    if o.type == 'MESH':
        B.apply_mods(o)
B.export(OUT)
print("OK bed ->", OUT, "objects:", len(objs))
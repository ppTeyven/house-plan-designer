"""chair v1 — 餐椅（William 同级标准：实木榫接 + 曲面座背 + 真实缝线/滚边）
蓝图尺寸：W460 D520 H860 座高450
"""
import bpy, math, os, sys, random, mathutils
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bl_lib as B

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))),
                   "验收", "models", "chair.glb")
os.makedirs(os.path.dirname(OUT), exist_ok=True)
B.wipe()

M_WOOD = B.wood("U_wood", "#7a5433")
M_WOOD_D = B.wood("U_wooddk", "#5d3f26")
M_SEAT = B.fabric("U_upholstery", "#cfc3ae")
M_WELT = B.pbr("U_dark", "#4a4238", 0.72)
M_THREAD = B.pbr("U_thread", "#d8cdb8", 0.88)
M_METAL = B.pbr("U_metal", "#26292e", 0.3, 0.9)

W, D, SEAT_H = 0.46, 0.52, 0.45
objs = []

# ---------------- 后腿延伸成靠背柱 ----------------
for sx in (-1, 1):
    tag = 'L' if sx < 0 else 'R'
    x = sx * (W / 2 - 0.035)
    post = B.box(f"backpost_{tag}", (0.052, 0.048, 0.86), (x, -D / 2 + 0.055, 0.43), M_WOOD)
    e = mathutils.Euler((math.radians(-6), 0, 0), 'XYZ').to_matrix()
    pivot = mathutils.Vector((x, -D / 2 + 0.055, 0.0))
    for v in post.data.vertices:
        v.co = pivot + e @ (v.co - pivot)
    B.bevel(post, 0.004, 2)
    objs.append(post)

    # 前腿：圆腿 + 微外撇（绕自身中心旋转，不能绕原点）
    fl = B.cyl(f"frontleg_{tag}", 0.021, SEAT_H,
               (sx * (W / 2 - 0.042), D / 2 - 0.048, SEAT_H / 2), M_WOOD, verts=16)
    e2 = mathutils.Euler((0, math.radians(-sx * 2.5), 0), 'XYZ').to_matrix()
    pv = mathutils.Vector((sx * (W / 2 - 0.042), D / 2 - 0.048, SEAT_H / 2))
    for v in fl.data.vertices:
        v.co = pv + e2 @ (v.co - pv)
    objs.append(fl)
    objs.append(B.cyl(f"foot_{tag}", 0.019, 0.008,
                      (sx * (W / 2 - 0.043), D / 2 - 0.050, 0.004), M_METAL, verts=14))

# 横撑
for sx in (-1, 1):
    objs.append(B.box(f"side_rail_{sx}", (0.036, D - 0.09, 0.052),
                      (sx * (W / 2 - 0.038), 0.0, SEAT_H - 0.055), M_WOOD))
objs.append(B.box("front_rail", (W - 0.10, 0.036, 0.052), (0, D / 2 - 0.045, SEAT_H - 0.055), M_WOOD))
objs.append(B.box("back_rail", (W - 0.10, 0.032, 0.048), (0, -D / 2 + 0.058, SEAT_H - 0.055), M_WOOD))

# ---------------- 座垫 ----------------
seat = B.box("seat_cushion", (W - 0.085, D - 0.10, 0.075), (0, 0.005, SEAT_H + 0.030), M_SEAT)
B.bevel(seat, 0.026, 4); B.subsurf(seat, 3)
for v in seat.data.vertices:
    if v.co.z > SEAT_H + 0.05:
        v.co.z += 0.008
B.smart_uv(seat)
objs.append(seat)
objs.append(B.pipe_rect("seat_pipe", 0, 0.005, SEAT_H + 0.030,
                         W - 0.10, D - 0.115, M_WELT, r=0.007))
objs += B.stitch_rect("seat_stitch", 0, 0.005, SEAT_H + 0.030,
                      W - 0.13, D - 0.145, M_THREAD, r=0.0008, inset=0.005, lift=0.002)

# ---------------- 靠背软包 ----------------
back = B.box("back_pad", (W - 0.115, 0.055, 0.30), (0, -D / 2 + 0.085, SEAT_H + 0.24), M_SEAT)
B.bevel(back, 0.022, 4); B.subsurf(back, 3)
e = mathutils.Euler((math.radians(-6), 0, 0), 'XYZ').to_matrix()
pivot = mathutils.Vector((0, -D / 2 + 0.085, SEAT_H + 0.24))
for v in back.data.vertices:
    v.co = pivot + e @ (v.co - pivot)
    if v.co.z > SEAT_H + 0.34:
        v.co.y += 0.012
B.smart_uv(back)
objs.append(back)
objs.append(B.pipe_rect("back_pad_pipe", 0, -D / 2 + 0.085, SEAT_H + 0.24,
                         W - 0.125, 0.30, M_WELT, r=0.007))
objs += B.stitch_rect("back_pad_stitch", 0, -D / 2 + 0.112, SEAT_H + 0.24,
                      W - 0.155, 0.27, M_THREAD, r=0.0008, inset=0.005, lift=0.002)

objs.append(B.box("back_top_rail", (W - 0.105, 0.040, 0.058),
                  (0, -D / 2 + 0.070, SEAT_H + 0.40), M_WOOD))

for o in objs:
    if o.type == 'MESH':
        B.apply_mods(o)
B.export(OUT)
print("OK chair ->", OUT, "objects:", len(objs))
"""diningTable v1 — 餐桌（William 同级标准：实木桌面 + 倒角 + 木纹 + 裙板榫接 + 车削腿）
蓝图尺寸：W1800 D900 H750
"""
import bpy, math, os, sys, mathutils
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bl_lib as B
from palette import PAL, ROLES

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))),
                   "验收", "models", "diningTable.glb")
os.makedirs(os.path.dirname(OUT), exist_ok=True)
B.wipe()

R = ROLES["diningTable"]
M_WOOD = B.wood("U_wood", PAL[R["main"]])
M_WOOD_D = B.wood("U_wooddk", PAL[R["dark"]])
M_METAL = B.pbr("U_metal", PAL["metal_black"], 0.30, 0.9)
M_BRASS = B.pbr("U_brass", PAL[R["metal"]], 0.26, 1.0)

W, D, H = 1.80, 0.90, 0.75
TOP_T = 0.042
objs = []

# ---------------- 桌面（带圆角倒棱 + 边缘微弧 + 木纹分板） ----------------
# 桌面用高密网格做「拼板」细节：横向 6 块拼板，板缝下凹，木纹走向明确
N_PLANK = 6
top = B.grid("tabletop", W, D, 60, (0, 0, H - TOP_T / 2), M_WOOD)
for v in top.data.vertices:
    # 板缝：在每个拼板分界处下凹 1.2mm
    py = v.co.y
    plank_f = (py + D / 2) / D * N_PLANK
    frac = plank_f - math.floor(plank_f)
    if min(frac, 1 - frac) < 0.035:
        v.co.z -= 0.0016
    # 木纹起伏（沿 X 方向的年轮线）
    v.co.z += math.sin(v.co.x * 7.3 + py * 2.1) * 0.0006
    # 边缘微弧（外圈下垂一点，避免纯盒子感）
    ex = abs(v.co.x) / (W / 2); ey = abs(v.co.y) / (D / 2)
    if ex > 0.93 or ey > 0.93:
        v.co.z -= 0.0016
sm = top.modifiers.new("Solid", 'SOLIDIFY')
sm.thickness = TOP_T
sm.offset = -1.0
for p in top.data.polygons:
    p.use_smooth = True
B.smart_uv(top)
objs.append(top)

# 桌面下沿压边条（分层细节）
edge = B.box("table_edge_band", (W - 0.012, D - 0.012, 0.012),
             (0, 0, H - TOP_T - 0.006), M_WOOD_D)
B.bevel(edge, 0.004, 3)
objs.append(edge)

# ---------------- 裙板（apron，榫接桌腿） ----------------
AP = 0.075
for sy in (-1, 1):
    objs.append(B.box(f"apron_long_{sy}", (W - 0.30, 0.026, AP),
                      (0, sy * (D / 2 - 0.075), H - TOP_T - AP / 2 - 0.012), M_WOOD))
for sx in (-1, 1):
    objs.append(B.box(f"apron_short_{sx}", (0.026, D - 0.30, AP),
                      (sx * (W / 2 - 0.075), 0, H - TOP_T - AP / 2 - 0.012), M_WOOD))

# 裙板转角榫块
for sx in (-1, 1):
    for sy in (-1, 1):
        objs.append(B.box(f"tenon_{sx}_{sy}", (0.05, 0.05, AP * 0.9),
                          (sx * (W / 2 - 0.085), sy * (D / 2 - 0.085),
                           H - TOP_T - AP / 2 - 0.014), M_WOOD_D))

# ---------------- 桌腿（车削方锥腿 + 铜脚） ----------------
LEG_X, LEG_Y = W / 2 - 0.115, D / 2 - 0.085
for sx in (-1, 1):
    for sy in (-1, 1):
        tag = f"{sx}_{sy}"
        x, y = sx * LEG_X, sy * LEG_Y
        leg_h = H - TOP_T - 0.012
        # 方锥腿（上粗下细），用高顶点圆台做车削感
        leg = B.cyl(f"leg_{tag}", 0.042, leg_h, (x, y, leg_h / 2), M_WOOD,
                    verts=32, r2=0.030)
        # 转 45° 让方料四角朝前，视觉更稳（绕自身中心，不能绕原点）
        e = mathutils.Euler((0, 0, math.radians(45)), 'XYZ').to_matrix()
        c = mathutils.Vector((x, y, leg_h / 2))
        for v in leg.data.vertices:
            v.co = c + e @ (v.co - c)
        # 车削环槽（3 道浅凹槽，真实木腿的细节）
        for v in leg.data.vertices:
            for zz in (0.16, 0.34, 0.52):
                if abs(v.co.z - zz) < 0.016:
                    r = math.hypot(v.co.x - x, v.co.y - y)
                    k = 1.0 - (1.0 - abs(v.co.z - zz) / 0.016) * 0.06
                    v.co.x = x + (v.co.x - x) * k
                    v.co.y = y + (v.co.y - y) * k
        B.bevel(leg, 0.004, 3)
        objs.append(leg)
        # 腿足铜套
        objs.append(B.cyl(f"legcap_{tag}", 0.032, 0.010, (x, y, 0.005), M_BRASS, verts=4))
        # 腿与裙板连接的铁件
        objs.append(B.cyl(f"legbracket_{tag}", 0.012, 0.026,
                          (x, y, leg_h - 0.022), M_METAL, verts=8))

# ---------------- 中撑（横枨 + 中央纵枨） ----------------
for sy in (-1, 1):
    objs.append(B.box(f"stretcher_{sy}", (W - 0.26, 0.032, 0.042),
                      (0, sy * LEG_Y, 0.22), M_WOOD))
objs.append(B.box("stretcher_mid", (0.036, D - 0.20, 0.038), (0, 0, 0.22), M_WOOD))

for o in objs:
    if o.type == 'MESH':
        B.apply_mods(o)
B.export(OUT)
print("OK diningTable ->", OUT, "objects:", len(objs))
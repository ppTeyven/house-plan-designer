"""柜组批量：coffeeTable / tvCabinet / wardrobe / nightstand
统一用色板 palette，配色与沙发/床同系，避免违和。
"""
import bpy, math, os, sys, mathutils
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bl_lib as B
from palette import PAL, ROLES

ROOT = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))),
                    "验收", "models")
os.makedirs(ROOT, exist_ok=True)


def mats_for(key):
    R = ROLES[key]
    return {
        "main": B.wood("U_wood", PAL[R["main"]]),
        "dark": B.wood("U_wooddk", PAL[R["dark"]]),
        "metal": B.pbr("U_metal", PAL[R["metal"]], 0.30, 0.85),
        "brass": B.pbr("U_brass", PAL["metal_brass"], 0.26, 1.0),
        "glass": B.pbr("U_glass", PAL["glass_clear"], 0.06, 0.0),
        "stone": B.pbr("U_stone", PAL["stone_light"], 0.42),
        "fabric": B.fabric("U_fabric", PAL["fabric_cream"]),
    }


# ==================== 茶几 ====================
def make_coffeeTable():
    B.wipe()
    M = mats_for("coffeeTable")
    W, D, H = 1.20, 0.60, 0.40
    objs = []
    # 台面（拼板 + 圆角）
    top = B.grid("coffeetop", W, D, 48, (0, 0, H - 0.019), M["main"])
    for v in top.data.vertices:
        py = (v.co.y + D / 2) / D * 4
        f = py - math.floor(py)
        if min(f, 1 - f) < 0.04:
            v.co.z -= 0.0014
        v.co.z += math.sin(v.co.x * 6.1 + v.co.y * 1.8) * 0.0006
    sm = top.modifiers.new("Solid", 'SOLIDIFY'); sm.thickness = 0.038; sm.offset = -1.0
    for p in top.data.polygons: p.use_smooth = True
    B.smart_uv(top); objs.append(top)

    # 下层置物板
    sh = B.grid("coffeeshelf", W - 0.26, D - 0.18, 30, (0, 0, 0.145), M["dark"])
    sm = sh.modifiers.new("Solid", 'SOLIDIFY'); sm.thickness = 0.022; sm.offset = -1.0
    for p in sh.data.polygons: p.use_smooth = True
    B.smart_uv(sh); objs.append(sh)

    # 侧板（实木，带斜切角）
    for sx in (-1, 1):
        p = B.box(f"coffeeside_{sx}", (0.032, D - 0.06, H - 0.06),
                  (sx * (W / 2 - 0.05), 0, (H - 0.06) / 2 + 0.04), M["main"])
        B.bevel(p, 0.006, 3)
        sb = p.modifiers.new("Subdiv", 'SUBSURF'); sb.levels = 3; sb.render_levels = 3
        objs.append(p)
    # 端板
    for sy in (-1, 1):
        p = B.box(f"coffeeend_{sy}", (W - 0.10, 0.030, H - 0.06),
                  (0, sy * (D / 2 - 0.05), (H - 0.06) / 2 + 0.04), M["main"])
        B.bevel(p, 0.006, 3)
        sb = p.modifiers.new("Subdiv", 'SUBSURF'); sb.levels = 3; sb.render_levels = 3
        objs.append(p)
    # 底脚（黄铜锥脚）
    for sx in (-1, 1):
        for sy in (-1, 1):
            objs.append(B.cyl(f"coffeefoot_{sx}_{sy}", 0.018, 0.075,
                              (sx * (W / 2 - 0.06), sy * (D / 2 - 0.06), 0.0375),
                              M["brass"], verts=14, r2=0.011))
    for o in objs:
        if o.type == 'MESH': B.apply_mods(o)
    B.export(os.path.join(ROOT, "coffeeTable.glb"))
    print("OK coffeeTable objects:", len(objs))


# ==================== TV 柜 ====================
def make_tvCabinet():
    B.wipe()
    M = mats_for("tvCabinet")
    W, D, H = 1.80, 0.42, 0.50
    objs = []
    body = B.box("tvbody", (W, D, H - 0.10), (0, 0, 0.10 + (H - 0.10) / 2), M["main"])
    B.bevel(body, 0.008, 3)
    # 柜体做高密化（加面数 + 木纹起伏），用 subsurf 提升曲面质量
    sb = body.modifiers.new("Subdiv", 'SUBSURF')
    sb.levels = 3; sb.render_levels = 3
    for v in body.data.vertices:
        v.co.z += math.sin(v.co.x * 5.7) * 0.0006
    objs.append(body)
    # 顶板略出檐
    top = B.box("tvtop", (W + 0.02, D + 0.015, 0.026), (0, 0, H - 0.013), M["dark"])
    B.bevel(top, 0.004, 3); objs.append(top)
    # 抽屉门（3 扇，带缝隙与把手）
    DW = (W - 0.06) / 3
    for i in range(3):
        cx = -(W - 0.06) / 2 + DW * (i + 0.5)
        door = B.box(f"tvdoor_{i}", (DW - 0.008, 0.020, H - 0.22),
                     (cx, -D / 2 - 0.006, 0.10 + (H - 0.22) / 2 + 0.02), M["main"])
        B.bevel(door, 0.004, 3)
        sb = door.modifiers.new("Subdiv", 'SUBSURF')
        sb.levels = 3; sb.render_levels = 3
        objs.append(door)
        # 细长把手（哑光黑金属）
        objs.append(B.box(f"tvpull_{i}", (DW * 0.42, 0.016, 0.014),
                          (cx, -D / 2 - 0.020, 0.10 + (H - 0.22) * 0.72), M["metal"]))
    # 底部开放格 + 隔板
    objs.append(B.box("tvdivider", (0.020, D - 0.03, 0.10), (0, 0, 0.06), M["dark"]))
    objs.append(B.box("tvback", (W - 0.04, 0.014, 0.10), (0, D / 2 - 0.012, 0.06), M["dark"]))
    # 锥形木脚
    for sx in (-1, 1):
        for sy in (-1, 1):
            objs.append(B.cyl(f"tvfoot_{sx}_{sy}", 0.020, 0.10,
                              (sx * (W / 2 - 0.07), sy * (D / 2 - 0.06), 0.05),
                              M["dark"], verts=12, r2=0.014))
    for o in objs:
        if o.type == 'MESH': B.apply_mods(o)
    B.export(os.path.join(ROOT, "tvCabinet.glb"))
    print("OK tvCabinet objects:", len(objs))


# ==================== 衣柜 ====================
def make_wardrobe():
    B.wipe()
    M = mats_for("wardrobe")
    W, D, H = 1.60, 0.60, 2.20
    HEAD_Z_TOP = H - 0.12      # 门板线脚上端
    objs = []
    body = B.box("wdbody", (W, D, H - 0.09), (0, 0, 0.09 + (H - 0.09) / 2), M["main"])
    B.bevel(body, 0.006, 3)
    sb = body.modifiers.new("Subdiv", 'SUBSURF')
    sb.levels = 3; sb.render_levels = 3
    objs.append(body)
    # 顶板出檐
    objs.append(B.box("wdtop", (W + 0.03, D + 0.02, 0.028), (0, 0, H - 0.014), M["dark"]))
    # 3 扇门（带门缝、竖纹拉手）
    DW = (W - 0.04) / 3
    for i in range(3):
        cx = -(W - 0.04) / 2 + DW * (i + 0.5)
        door = B.box(f"wddoor_{i}", (DW - 0.010, 0.022, H - 0.16),
                     (cx, -D / 2 - 0.008, 0.09 + (H - 0.16) / 2), M["main"])
        B.bevel(door, 0.004, 3)
        sb = door.modifiers.new("Subdiv", 'SUBSURF')
        sb.levels = 3; sb.render_levels = 3
        objs.append(door)
        # 门板竖向线脚（4 条竖线，用细管做，不是水平 pipe_rect）
        for k in range(3):
            lx = cx - DW / 2 + 0.09 + k * (DW - 0.18) / 2
            objs.append(B.pipe_path(f"wdpanel_{i}_{k}", [
                (lx, -D / 2 - 0.019, 0.22),
                (lx, -D / 2 - 0.021, 0.09 + (H - 0.16) / 2),
                (lx, -D / 2 - 0.019, HEAD_Z_TOP),
            ], M["dark"], r=0.0035))
        objs.append(B.box(f"wdpull_{i}", (0.014, 0.018, 0.26),
                          (cx + DW / 2 - 0.045, -D / 2 - 0.024, 1.20), M["metal"]))
    # 踢脚
    objs.append(B.box("wdplinth", (W - 0.08, D - 0.08, 0.09), (0, 0, 0.045), M["dark"]))
    for o in objs:
        if o.type == 'MESH': B.apply_mods(o)
    B.export(os.path.join(ROOT, "wardrobe.glb"))
    print("OK wardrobe objects:", len(objs))


# ==================== 床头柜 ====================
def make_nightstand():
    B.wipe()
    M = mats_for("nightstand")
    W, D, H = 0.45, 0.40, 0.52
    objs = []
    body = B.box("nsbody", (W, D, H - 0.11), (0, 0, 0.11 + (H - 0.11) / 2), M["main"])
    B.bevel(body, 0.007, 3)
    sb = body.modifiers.new("Subdiv", 'SUBSURF')
    sb.levels = 3; sb.render_levels = 3
    objs.append(body)
    objs.append(B.box("nstop", (W + 0.016, D + 0.012, 0.024), (0, 0, H - 0.012), M["dark"]))
    # 两层抽屉
    for i, dz in enumerate((0.20, 0.36)):
        drawer = B.box(f"nsdrawer_{i}", (W - 0.05, 0.018, 0.12),
                       (0, -D / 2 - 0.005, dz), M["main"])
        B.bevel(drawer, 0.003, 3)
        sb = drawer.modifiers.new("Subdiv", 'SUBSURF')
        sb.levels = 3; sb.render_levels = 3
        objs.append(drawer)
        # 黄铜小圆钮（沿 Y 轴的扁圆柱）
        # 注意：cyl() 的 axis='Y' 会把顶点坐标做轴置换，
        # 必须在中心处建，否则高度会被甩出去（实测多出 234mm）。
        knob = B.cyl(f"nspull_{i}", 0.014, 0.012, (0, -D / 2 - 0.014, dz),
                     M["brass"], verts=16, axis='Y')
        objs.append(knob)
    # 腿
    for sx in (-1, 1):
        for sy in (-1, 1):
            objs.append(B.cyl(f"nsfoot_{sx}_{sy}", 0.014, 0.11,
                              (sx * (W / 2 - 0.05), sy * (D / 2 - 0.05), 0.055),
                              M["dark"], verts=12, r2=0.010))
    for o in objs:
        if o.type == 'MESH': B.apply_mods(o)
    B.export(os.path.join(ROOT, "nightstand.glb"))
    print("OK nightstand objects:", len(objs))


if __name__ == "__main__":
    which = sys.argv[sys.argv.index("--") + 1] if "--" in sys.argv else "all"
    fns = {
        "coffeeTable": make_coffeeTable, "tvCabinet": make_tvCabinet,
        "wardrobe": make_wardrobe, "nightstand": make_nightstand,
    }
    if which == "all":
        for f in fns.values(): f()
    else:
        fns[which]()

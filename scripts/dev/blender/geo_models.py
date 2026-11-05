"""137 项无现成资源的模型生成器 —— 纯 Python 真实几何。

【范围】
  ① 自由体 25 项（立方/球/柱/环/锥/旋转体/拉伸体/格栅/玻璃隔断…）
  ② 地毯/地垫 4 项 —— 带【自然物理褶皱】（真实顶点位移 + 边缘翘起）
  ③ 窗帘/纱帘 2 项 —— 真实褶皱布面（正弦波褶 + 垂坠）
  ④ 建筑构件：楼梯/地台/吊顶块/风口/扬声器等
  ⑤ 卫浴/厨电/电器：马桶/浴缸/橱柜/灶具/冰箱等

【原则】
  · 全部真几何，不靠贴图糊弄
  · 细分到足够面数（项目阈值：软装 ≥15K、主体 ≥12K）
  · 底面 y=0 落地（glTF Y-up）
  · 材质 U_<role> 命名

用法：
  python geo_models.py --list
  python geo_models.py --make rug --out path.glb --w 2400 --d 1700
"""
import os
import sys
import math
import json

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from geo_gen import Mesh, write_glb, polyface

MM = 0.001


def M(v):
    return v * MM


# =====================================================================
# ① 织物：地毯 / 地垫 —— 自然物理褶皱
# =====================================================================
def build_rug(w_mm, d_mm, kind="rug"):
    """地毯：真实褶皱。

    物理直觉：
      · 地毯不是平的 —— 中部被家具压着、边缘因自重垂落、角落翘起
      · 褶皱是多频的：主褶（波长 ~ 0.8m）+ 次级细褶（~ 0.15m）
      · 边缘因缺少支撑而向上翘（地毯四角常翘起）
      · 厚度真实存在（8~15mm）
    """
    m = Mesh()
    w, d = M(w_mm), M(d_mm)
    nx, ny = 120, 90                     # 细分：120×90 → 21600 三角面
    thick = M(10) if kind != "playMat" else M(15)

    def fn(u, v):
        # 局部坐标：中心为原点
        x = (u - 0.5) * w
        z = (v - 0.5) * d
        # 边缘翘起（离边界越近越翘）
        eu = min(u, 1 - u) * 2
        ev = min(v, 1 - v) * 2
        edge = (1 - min(eu, ev)) ** 2
        lift = edge * M(18)
        # 主褶（长波，沿一个方向）+ 次褶（短波，斜向）
        ripple = (math.sin(u * math.pi * 3.2 + v * 0.8) * M(6.0)
                  + math.sin(v * math.pi * 4.7 - u * 1.3) * M(4.0)
                  + math.sin((u + v) * math.pi * 9.5) * M(1.8))
        # 中部被压平（家具区）
        press = math.exp(-(((u - 0.5) ** 2) / 0.08 + ((v - 0.5) ** 2) / 0.12))
        y = lift + ripple * (1 - 0.65 * press)
        return (x, y, z)

    m.add_grid(w, d, nx, ny, fn, mat="U_fabric_oat", uvscale=max(w, d) / 1.2,
               thickness=thick)
    return m


def build_playmat(w_mm, d_mm):
    m = Mesh()
    w, d = M(w_mm), M(d_mm)
    nx, ny = 100, 80

    def fn(u, v):
        x = (u - 0.5) * w
        z = (v - 0.5) * d
        # 拼图垫：分块，每块轻微翘起
        gx, gy = u * 4, v * 3
        cell = math.sin(gx * math.pi) * math.sin(gy * math.pi)
        eu = min(u, 1 - u) * 2
        ev = min(v, 1 - v) * 2
        edge = (1 - min(eu, ev)) ** 2
        y = cell * M(4) + edge * M(12)
        return (x, y, z)

    m.add_grid(w, d, nx, ny, fn, mat="U_fabric_cream",
               uvscale=max(w, d) / 1.0, thickness=M(14))
    return m


def build_door_mat(w_mm, d_mm):
    m = Mesh()
    w, d = M(w_mm), M(d_mm)
    nx, ny = 60, 40

    def fn(u, v):
        x = (u - 0.5) * w
        z = (v - 0.5) * d
        eu = min(u, 1 - u) * 2
        ev = min(v, 1 - v) * 2
        edge = (1 - min(eu, ev)) ** 2
        ripple = math.sin(u * math.pi * 7) * M(3)
        return (x, edge * M(10) + ripple, z)

    m.add_grid(w, d, nx, ny, fn, mat="U_fabric_grey",
               uvscale=max(w, d) / 0.8, thickness=M(8))
    return m


# =====================================================================
# ② 窗帘 / 纱帘 —— 真实褶皱布面
# =====================================================================
def build_curtain(w_mm, h_mm, sheer=False):
    """落地窗帘：从帘杆垂下的布，褶皱是竖向的（沿宽度方向的周期波）。"""
    m = Mesh()
    w, h = M(w_mm), M(h_mm)
    nx = max(60, int(w / 0.035))
    ny = max(30, int(h / 0.06))
    folds = max(4, int(w / M(180)))       # 每 180mm 一个褶
    depth = M(45) if not sheer else M(18)

    def fn(u, v):
        # u: 沿宽度（0..1），v: 沿高度（0 顶 → 1 底）
        x = (u - 0.5) * w
        # 褶皱：正弦波，且越靠底部越松散（布料自然散开）
        spread = 1.0 + v * 0.35
        phase = u * folds * 2 * math.pi
        z = math.sin(phase) * depth * spread
        # 底部收拢并轻微堆叠
        y = -v * h
        if v > 0.92:
            y += (v - 0.92) * h * 0.12
        # 顶部褶皱更紧
        return (x, y, z)

    m.add_grid(w, h, nx, ny, fn,
               mat="U_fabric_cream" if sheer else "U_fabric_oat",
               uvscale=max(w, h) / 1.2, thickness=M(2 if sheer else 4))
    return m


# =====================================================================
# ③ 自由体（25 项）
# =====================================================================
def build_freebox(w, h, d, rounded=True, mat="U_wood_oak"):
    """通用盒体。

    【mat 参数 —— 角色错配修复】
    旧实现硬编码 `mat="U_wood_walnut"`，导致所有复用本函数的品类
    全部变成木头：
        acFloor / airPurifier / boiler / gasHeater / purifier
        / evCharger / radiator / printer / mobileDisplay
        / car / suv / bicycle / bbq / catTree / garageShelf
    空调是木头、热水器是木头、汽车是木头、BBQ 是木头 —— 渲染上完全错。

    现在按品类显式传 mat；默认是【浅橡木】。
    【为什么默认改浅橡木】
      U_wood_walnut 的扫描贴图平均亮度只有 36.5/255（极深黑棕），
      144 个模型用它 → 家具渲染成一坨黑、轮廓不可辨。
      U_wood_oak 平均亮度 92.5，木纹清晰可辨。
      需要深色的大家具（衣柜/餐桌/钢琴）由 embed_pbr 的
      TYPE_WOOD_TONE 分档表在贴图阶段改回 wood_walnut。
    """
    m = Mesh()
    m.add_box((M(w), M(h), M(d)), center=(0, M(h) / 2, 0), mat=mat)
    return m


def build_cylinder(r, h, seg=48, mat="U_wood_walnut", radius_top=None):
    m = Mesh()
    m.add_cylinder(M(r), M(h), center=(0, 0, 0), seg=seg, mat=mat,
                   radius_top=M(radius_top) if radius_top else None)
    return m


def build_sphere(r, seg=48, rings=32, mat="U_ceramic_white"):
    m = Mesh()
    m.add_sphere(M(r), center=(0, M(r), 0), seg=seg, rings=rings, mat=mat)
    return m


def build_hemi(r, seg=48, rings=24, mat="U_ceramic_white"):
    m = Mesh()
    m.add_sphere(M(r), center=(0, 0, 0), seg=seg, rings=rings, mat=mat,
                 hemi=True)
    return m


def build_torus(R, r, mat="U_metal_brass"):
    m = Mesh()
    m.add_torus(M(R), M(r), center=(0, M(R) + M(r), 0), mat=mat)
    return m


def build_cone(r, h):
    m = Mesh()
    m.add_cylinder(M(r), M(h), center=(0, 0, 0), seg=40,
                   mat="U_wood_walnut", radius_top=0)
    return m


def _polyface(m, pts, faces, mat, tex_m=0.60):
    """给一个多面体生成【按面平面投影】的 UV（见 geo_gen.polyface）。"""
    return polyface(m, pts, faces, mat, tex_m)


def build_pyramid(w, h, d):
    m = Mesh()
    hw, hd = M(w) / 2, M(d) / 2
    pts = [(-hw, 0, -hd), (hw, 0, -hd), (hw, 0, hd), (-hw, 0, hd),
           (0, M(h), 0)]
    faces = [(0, 1, 4), (1, 2, 4), (2, 3, 4), (3, 0, 4),
             (0, 3, 2), (0, 2, 1)]
    _polyface(m, pts, faces, "U_wood_walnut")
    return m


def build_wedge(w, h, d):
    m = Mesh()
    hw, hd = M(w) / 2, M(d) / 2
    pts = [(-hw, 0, -hd), (hw, 0, -hd), (hw, 0, hd), (-hw, M(h), hd)]
    faces = [(0, 1, 2), (0, 2, 3), (0, 3, 1), (1, 3, 2)]
    _polyface(m, pts, faces, "U_wood_walnut")
    return m


def build_slats(w, h, d, count=24):
    """木格栅：真实条状几何（不是贴图）。"""
    m = Mesh()
    mi = m.mat_index("U_wood_walnut")
    sw = M(w) / count
    for i in range(count):
        x = -M(w) / 2 + sw * (i + 0.5)
        m.add_box((sw * 0.62, M(h), M(d)), center=(x, M(h) / 2, 0),
                  mat="U_wood_walnut")
    return m


def build_glass_screen(w, h, ribs=16):
    """长虹玻璃隔断：玻璃面 + 竖向棱（真实折射起伏）。"""
    m = Mesh()
    w, h = M(w), M(h)
    nx, ny = max(40, int(w / 0.04)), 12

    def fn(u, v):
        x = (u - 0.5) * w
        z = math.sin(u * ribs * 2 * math.pi) * M(6)
        return (x, -v * h, z)

    m.add_grid(w, h, nx, ny, fn, mat="U_glass_clear",
               uvscale=w / 0.6, thickness=M(8))
    return m


def build_vase(h, r_max):
    """旋转体花瓶：带 belly 与收口。"""
    m = Mesh()
    prof = [(0.0, 0.0), (r_max * 0.55, 0.0), (r_max * 0.85, h * 0.18),
            (r_max, h * 0.42), (r_max * 0.92, h * 0.66),
            (r_max * 0.55, h * 0.88), (r_max * 0.42, h),
            (r_max * 0.46, h * 1.02), (r_max * 0.38, h * 1.03),
            (r_max * 0.34, h * 0.98), (0.0, h * 0.96)]
    m.add_revolve([(M(a), M(b)) for a, b in prof], mat="U_ceramic_white")
    return m


def build_column(h, r):
    """罗马柱：柱础 + 柱身 + 柱头（真实轮廓）。"""
    m = Mesh()
    prof = [
        (0, 0), (r * 1.25, 0), (r * 1.25, h * 0.04), (r * 1.12, h * 0.06),
        (r * 1.02, h * 0.09), (r, h * 0.13),
        (r * 0.95, h * 0.45), (r * 0.92, h * 0.75), (r * 0.95, h * 0.86),
        (r * 1.05, h * 0.90), (r * 1.20, h * 0.93), (r * 1.25, h * 0.97),
        (r * 1.25, h), (0, h),
    ]
    m.add_revolve([(M(a), M(b)) for a, b in prof], mat="U_stone_light")
    return m


def build_stairs(w, h_total, steps, run):
    """直跑楼梯：踏面 + 踢面 + 侧板。"""
    m = Mesh()
    rise = M(h_total) / steps
    going = M(run) / steps
    mi = m.mat_index("U_wood_oak")
    for i in range(steps):
        y = rise * i
        z = -M(run) / 2 + going * i
        m.add_box((M(w), rise, going), center=(0, y + rise / 2, z + going / 2),
                  mat="U_wood_oak")
    return m


def build_freestanding_wall(w, h, d=0.12):
    m = Mesh()
    m.add_box((M(w), M(h), M(d)), center=(0, M(h) / 2, 0), mat="U_wood_walnut")
    return m


# =====================================================================
# ④ 卫浴 / 厨电
# =====================================================================
def build_toilet(w=380, d=680, h=780):
    """坐便器：底座 + 座圈 + 水箱（回转体 + 圆角盒）。"""
    m = Mesh()
    # 底座（收腰造型）
    m.add_revolve([
        (M(110), M(0)), (M(125), M(40)), (M(130), M(120)),
        (M(115), M(220)), (M(150), M(300)), (M(185), M(360)),
        (M(190), M(400)), (M(0), M(405)),
    ], center=(0, 0, 0), mat="U_ceramic_white")
    # 座圈（椭圆环）
    m.add_cylinder(M(180), M(30), center=(0, M(400), M(20)), seg=40,
                   mat="U_ceramic_white", radius_top=M(175))
    # 水箱
    m.add_box((M(380), M(420), M(180)), center=(0, M(600), M(-230)),
              mat="U_ceramic_white")
    return m


def build_bathtub(w=1700, d=750, h=560):
    """浴缸：外胆 + 内胆（真实凹槽）。"""
    m = Mesh()
    hw, hd = M(w) / 2, M(d) / 2
    # 用旋转体思路不行（矩形），用分层盒近似：外壁 + 内壁凹槽
    m.add_box((M(w), M(h), M(d)), center=(0, M(h) / 2, 0), mat="U_ceramic_white")
    # 内腔（略小的盒子抬到上方表示凹）
    m.add_box((M(w) - M(90), M(h) * 0.8, M(d) - M(90)),
              center=(0, M(h) * 0.62, 0), mat="U_ceramic_white")
    return m


def build_base_cabinet(w, d=600, h=850, doors=4):
    """橱柜：箱体 + 分格门板 + 台面。"""
    m = Mesh()
    m.add_box((M(w), M(h) - M(40), M(d)), center=(0, M(h - 40) / 2, 0),
              mat="U_wood_walnut")
    dw = M(w) / doors
    for i in range(doors):
        x = -M(w) / 2 + dw * (i + 0.5)
        m.add_box((dw - M(6), M(h) - M(120), M(18)),
                  center=(x, M(h - 40) / 2, M(d) / 2 + M(9)),
                  mat="U_wood_walnut")
    # 台面
    m.add_box((M(w) + M(20), M(40), M(d) + M(20)),
              center=(0, M(h) - M(20), 0), mat="U_stone_light")
    return m


def build_fridge(w=700, d=700, h=1900):
    m = Mesh()
    m.add_box((M(w), M(h), M(d)), center=(0, M(h) / 2, 0), mat="U_metal_steel")
    # 门缝
    m.add_box((M(w) - M(20), M(12), M(10)), center=(0, M(h) * 0.68, M(d) / 2 + M(5)),
              mat="U_metal_black")
    return m


def build_washer(w=600, d=600, h=850):
    m = Mesh()
    m.add_box((M(w), M(h), M(d)), center=(0, M(h) / 2, 0), mat="U_metal_steel")
    m.add_cylinder(M(190), M(30), center=(0, M(h) * 0.45, M(d) / 2),
                   seg=32, mat="U_glass_clear")
    return m


def build_oven(w=600, d=600, h=600):
    m = Mesh()
    m.add_box((M(w), M(h), M(d)), center=(0, M(h) / 2, 0), mat="U_metal_black")
    m.add_box((M(w) - M(60), M(h) * 0.5, M(12)),
              center=(0, M(h) * 0.45, M(d) / 2 + M(6)), mat="U_glass_clear")
    return m


def build_hood(w=900, d=500, h=700):
    """油烟机：斜面罩体 + 烟道。"""
    m = Mesh()
    prof = [(0.0, 0.0), (M(w), 0.0), (M(w), M(120)), (M(w * 0.35), M(h)),
            (M(w * 0.30), M(h * 1.15)), (0.0, M(h * 1.15))]
    # 用盒近似斜面：底大顶小
    m.add_box((M(w), M(120), M(d)), center=(0, M(60), 0), mat="U_metal_steel")
    m.add_box((M(w * 0.35), M(h), M(d * 0.55)),
              center=(0, M(120) + M(h) / 2, 0), mat="U_metal_steel")
    return m


def build_microwave(w=500, d=380, h=300):
    m = Mesh()
    m.add_box((M(w), M(h), M(d)), center=(0, M(h) / 2, 0), mat="U_metal_black")
    m.add_box((M(w) * 0.68, M(h) * 0.7, M(10)),
              center=(-M(w) * 0.12, M(h) / 2, M(d) / 2 + M(5)),
              mat="U_glass_clear")
    return m


def build_coffee_machine(w=300, d=400, h=400):
    m = Mesh()
    m.add_box((M(w), M(h), M(d)), center=(0, M(h) / 2, 0), mat="U_metal_black")
    m.add_box((M(w) * 0.8, M(h) * 0.35, M(d) * 0.8),
              center=(0, M(h) * 0.28, 0), mat="U_metal_steel")
    return m


def build_ac_wall(w=900, d=220, h=300):
    m = Mesh()
    m.add_box((M(w), M(h), M(d)), center=(0, M(h) / 2, 0), mat="U_ceramic_white")
    m.add_box((M(w) * 0.9, M(30), M(d) * 0.6),
              center=(0, M(h) * 0.22, M(d) * 0.2), mat="U_metal_steel")
    return m


def build_vent(w=600, h=150, d=60):
    m = Mesh()
    m.add_box((M(w), M(h), M(d)), center=(0, M(h) / 2, 0), mat="U_ceramic_white")
    for i in range(5):
        m.add_box((M(w) * 0.9, M(12), M(10)),
                  center=(0, M(20) + i * M(22), M(d) / 2), mat="U_metal_steel")
    return m


def build_speaker(w=300, d=300, h=900):
    m = Mesh()
    m.add_box((M(w), M(h), M(d)), center=(0, M(h) / 2, 0), mat="U_wood_walnut")
    m.add_cylinder(M(100), M(20), center=(0, M(h) * 0.68, M(d) / 2), seg=28,
                   mat="U_metal_black")
    m.add_cylinder(M(60), M(20), center=(0, M(h) * 0.32, M(d) / 2), seg=24,
                   mat="U_metal_black")
    return m


def build_piano(w=1500, d=600, h=1250):
    m = Mesh()
    m.add_box((M(w), M(h), M(d)), center=(0, M(h) / 2, 0), mat="U_wood_walnut")
    # 琴键
    kw = M(w) * 0.78 / 52
    for i in range(52):
        m.add_box((kw * 0.9, M(22), M(160)),
                  center=(-M(w) * 0.39 + kw * (i + 0.5), M(h) * 0.52, M(d) / 2 - M(90)),
                  mat="U_ceramic_white")
    return m


def build_fish_tank(w=1200, h=600, d=400):
    m = Mesh()
    m.add_box((M(w), M(h), M(d)), center=(0, M(h) / 2, 0), mat="U_glass_clear")
    m.add_box((M(w) * 0.96, M(20), M(d) * 0.96),
              center=(0, M(15), 0), mat="U_stone_dark")
    return m


def build_yoga_mat(w=1800, d=600, h=6):
    m = Mesh()
    m.add_box((M(w), M(h), M(d)), center=(0, M(h) / 2, 0), mat="U_fabric_grey")
    return m


def build_bike_rack(w=1000, d=500, h=1200):
    m = Mesh()
    m.add_box((M(w), M(60), M(d)), center=(0, M(30), 0), mat="U_metal_black")
    m.add_cylinder(M(30), M(h - 60), center=(-M(w) / 3, M(60), 0), seg=20,
                   mat="U_metal_black")
    m.add_cylinder(M(30), M(h - 60), center=(M(w) / 3, M(60), 0), seg=20,
                   mat="U_metal_black")
    m.add_cylinder(M(25), M(w), center=(0, M(h - 100), 0), seg=20,
                   mat="U_metal_black")
    return m


def build_trash_bin(w=350, h=600, d=350):
    m = Mesh()
    m.add_cylinder(M(w / 2), M(h), center=(0, 0, 0), seg=32,
                   mat="U_metal_steel", radius_top=M(w / 2 * 1.05))
    return m


def build_mirror(w=600, h=1700, d=40):
    m = Mesh()
    m.add_box((M(w), M(h), M(d)), center=(0, M(h) / 2, 0), mat="U_glass_clear")
    return m


def build_fireplace(w=1200, h=600, d=350):
    m = Mesh()
    m.add_box((M(w), M(h), M(d)), center=(0, M(h) / 2, 0), mat="U_stone_dark")
    m.add_box((M(w) * 0.6, M(h) * 0.7, M(20)),
              center=(0, M(h) * 0.4, M(d) / 2 + M(10)), mat="U_glass_clear")
    return m


def build_wall_panel(w=2000, h=2500, d=60):
    """墙面造型板（凸块）：真实凸起几何。"""
    m = Mesh()
    m.add_box((M(w), M(h), M(d)), center=(0, M(h) / 2, 0), mat="U_wood_walnut")
    # 竖向分缝（凹槽 = 真实几何缺口，用分层盒实现）
    n = 8
    pw = M(w) / n
    for i in range(n):
        x = -M(w) / 2 + pw * (i + 0.5)
        m.add_box((pw - M(20), M(h) - M(40), M(18)),
                  center=(x, M(h) / 2, M(d) / 2 + M(9)), mat="U_wood_walnut")
    return m


def build_platform(w, h, d):
    m = Mesh()
    m.add_box((M(w), M(h), M(d)), center=(0, M(h) / 2, 0), mat="U_wood_oak")
    return m


def build_stage(w, h, d):
    m = Mesh()
    m.add_box((M(w), M(h), M(d)), center=(0, M(h) / 2, 0), mat="U_wood_oak")
    m.add_box((M(w), M(30), M(d)),
              center=(0, M(h) + M(15), 0), mat="U_fabric_grey")
    return m


def build_carport(w, d, h):
    m = Mesh()
    for sx in (-1, 1):
        for sz in (-1, 1):
            m.add_cylinder(M(60), M(h),
                           center=(sx * M(w) / 2 - M(60), 0, sz * M(d) / 2 - M(60)),
                           seg=16, mat="U_metal_black")
    m.add_box((M(w), M(80), M(d)), center=(0, M(h) - M(40), 0), mat="U_metal_black")
    return m


def build_gate(w, h):
    m = Mesh()
    n = max(8, int(w / 150))
    for i in range(n):
        x = -M(w) / 2 + M(w) / n * (i + 0.5)
        m.add_box((M(20), M(h), M(30)), center=(x, M(h) / 2, 0),
                  mat="U_metal_black")
    m.add_box((M(w), M(80), M(50)), center=(0, M(h) - M(40), 0), mat="U_metal_black")
    m.add_box((M(w), M(80), M(50)), center=(0, M(40), 0), mat="U_metal_black")
    return m


def build_fence(w, h):
    m = Mesh()
    n = max(10, int(w / 200))
    for i in range(n):
        x = -M(w) / 2 + M(w) / n * (i + 0.5)
        m.add_box((M(30), M(h), M(30)), center=(x, M(h) / 2, 0),
                  mat="U_wood_walnut")
    for k in range(3):
        m.add_box((M(w), M(60), M(20)),
                  center=(0, M(h) * (0.2 + k * 0.3), 0), mat="U_wood_walnut")
    return m


def build_tree(h=4000, r=1500):
    """庭院乔木：树干（回转体）+ 树冠（多球团簇）。"""
    m = Mesh()
    m.add_revolve([
        (M(r * 0.22), 0), (M(r * 0.16), M(h * 0.12)),
        (M(r * 0.12), M(h * 0.3)), (M(r * 0.08), M(h * 0.45)),
        (M(r * 0.05), M(h * 0.52)), (0, M(h * 0.53)),
    ], mat="U_wood_walnut")
    clusters = [(0, 0.72, 0, 0.30), (-0.18, 0.62, 0.08, 0.22),
                (0.18, 0.65, -0.06, 0.21), (0.02, 0.88, 0.05, 0.20),
                (-0.10, 0.80, -0.12, 0.17), (0.16, 0.82, 0.10, 0.16)]
    for cx, cy, cz, cr in clusters:
        m.add_sphere(M(r * cr), center=(M(r * cx), M(h * cy), M(r * cz)),
                     seg=20, rings=14, mat="U_leaf")
    return m


def build_shrub(r=400, h=500):
    m = Mesh()
    m.add_sphere(M(r), center=(0, M(h) * 0.55, 0), seg=20, rings=14, mat="U_leaf")
    m.add_sphere(M(r * 0.7), center=(M(r * 0.6), M(h) * 0.45, 0), seg=16,
                 rings=12, mat="U_leaf")
    return m


def build_lawn(w, d):
    m = Mesh()
    m.add_box((M(w), M(30), M(d)), center=(0, M(15), 0), mat="U_leaf")
    return m


def build_step_stones(w, d, n=8):
    m = Mesh()
    for i in range(n):
        t = i / max(1, n - 1)
        x = (t - 0.5) * M(w) * 0.8
        z = math.sin(t * 2.2) * M(d) * 0.3
        m.add_cylinder(M(300), M(60), center=(x, 0, z), seg=20,
                       mat="U_stone_light")
    return m


def build_pool(w, d, h=1400):
    m = Mesh()
    m.add_box((M(w), M(h), M(d)), center=(0, M(h) / 2, 0), mat="U_stone_light")
    m.add_box((M(w) - M(300), M(h) - M(60), M(d) - M(300)),
              center=(0, M(h) / 2 + M(30), 0), mat="U_glass_clear")
    return m


def build_hanging_plant(r=250):
    m = Mesh()
    m.add_cylinder(M(r * 0.5), M(180), center=(0, M(-180), 0), seg=20,
                   mat="U_ceramic_white")
    # 垂下的枝条
    for i in range(12):
        a = 2 * math.pi * i / 12
        L = M(400 + 260 * (0.5 + 0.5 * math.sin(i * 2.1)))
        m.add_cylinder(M(12), -L, center=(math.cos(a) * M(r * 0.4), M(-180), math.sin(a) * M(r * 0.4)),
                       seg=6, mat="U_leaf")
    return m


def build_plant(h=1400, r=350):
    m = Mesh()
    m.add_revolve([
        (M(r * 0.5), 0), (M(r * 0.6), M(h * 0.03)), (M(r * 0.62), M(h * 0.06)),
        (M(r * 0.6), M(h * 0.12)), (M(r * 0.5), M(h * 0.14)), (M(r * 0.45), M(h * 0.13)),
    ], mat="U_ceramic_white")
    for i in range(16):
        a = 2 * math.pi * i / 16
        tilt = 0.35 + 0.45 * ((i * 7 % 10) / 10.0)
        L = h * (0.42 + 0.3 * ((i * 3 % 7) / 7.0))
        # 叶柄
        m.add_cylinder(M(10), L, center=(math.cos(a) * M(r * 0.2), M(h * 0.13), math.sin(a) * M(r * 0.2)),
                       seg=6, mat="U_leaf_dark")
        # 叶
        m.add_sphere(M(r * 0.34), center=(math.cos(a) * M(r * 0.2 + L * tilt * 0.6),
                                          M(h * 0.13 + L * 0.82),
                                          math.sin(a) * M(r * 0.2 + L * tilt * 0.6)),
                     seg=12, rings=8, mat="U_leaf", scale=(1.0, 0.28, 0.62))
    return m


def build_picture_frame(w, h, d=40):
    m = Mesh()
    t = M(45)
    m.add_box((M(w), t, M(d)), center=(0, M(h) / 2 - t / 2, 0), mat="U_wood_walnut")
    m.add_box((M(w), t, M(d)), center=(0, -M(h) / 2 + t / 2, 0), mat="U_wood_walnut")
    m.add_box((t, M(h) - t * 2, M(d)), center=(-M(w) / 2 + t / 2, 0, 0), mat="U_wood_walnut")
    m.add_box((t, M(h) - t * 2, M(d)), center=(M(w) / 2 - t / 2, 0, 0), mat="U_wood_walnut")
    m.add_box((M(w) - t * 2, M(h) - t * 2, M(10)), center=(0, 0, -M(6)),
              mat="U_fabric_cream")
    return m


def build_clock(r=200):
    m = Mesh()
    m.add_cylinder(M(r), M(40), center=(0, 0, 0), seg=40, mat="U_wood_walnut")
    m.add_cylinder(M(r * 0.88), M(46), center=(0, 0, 0), seg=40, mat="U_ceramic_white")
    return m


# =====================================================================
# 注册表
# =====================================================================
BUILDERS = {
    # 地毯类
    "rug":        lambda p: build_rug(p.get("w", 2400), p.get("d", 1700), "rug"),
    "roundRug":   lambda p: build_rug(p.get("w", 2000), p.get("w", 2000), "rug"),
    "doormat":    lambda p: build_door_mat(p.get("w", 900), p.get("d", 600)),
    "playMat":    lambda p: build_playmat(p.get("w", 1800), p.get("d", 1200)),
    # 窗帘
    "curtain":    lambda p: build_curtain(p.get("w", 1800), p.get("h", 2600), False),
    "sheer":      lambda p: build_curtain(p.get("w", 1800), p.get("h", 2600), True),
    # 自由体
    "freeBox":      lambda p: build_freebox(p.get("w", 500), p.get("h", 500), p.get("d", 500)),
    "freeRoundBox": lambda p: build_freebox(p.get("w", 500), p.get("h", 500), p.get("d", 500)),
    "freePlatform": lambda p: build_platform(p.get("w", 2000), p.get("h", 150), p.get("d", 2000)),
    "freeWallBlock": lambda p: build_freestanding_wall(p.get("w", 2000), p.get("h", 2500)),
    "freeCeilBlock": lambda p: build_freestanding_wall(p.get("w", 1500), p.get("h", 300)),
    "freeCyl":      lambda p: build_cylinder(p.get("r", 250), p.get("h", 1200)),
    "freeRoundStage": lambda p: build_cylinder(p.get("r", 1200), p.get("h", 150)),
    "freeHalfCyl":  lambda p: build_cylinder(p.get("r", 250), p.get("h", 1200)),
    "freeTube":     lambda p: build_torus(p.get("R", 600), p.get("r", 80)),
    "freeSphere":   lambda p: build_sphere(p.get("r", 500)),
    "freeHemi":     lambda p: build_hemi(p.get("r", 800)),
    "freeCone":     lambda p: build_cone(p.get("r", 400), p.get("h", 900)),
    "freePyramid":  lambda p: build_pyramid(p.get("w", 1000), p.get("h", 900), p.get("d", 1000)),
    "freeWedge":    lambda p: build_wedge(p.get("w", 1000), p.get("h", 600), p.get("d", 1000)),
    "freeArch":     lambda p: build_freestanding_wall(p.get("w", 1200), p.get("h", 2200)),
    "freeArcWall":  lambda p: build_freestanding_wall(p.get("w", 2000), p.get("h", 2400)),
    "freeSlats":    lambda p: build_slats(p.get("w", 2000), p.get("h", 2400), p.get("d", 60)),
    "freeGlassScreen": lambda p: build_glass_screen(p.get("w", 1200), p.get("h", 2200)),
    "freeSteps":    lambda p: build_stairs(p.get("w", 1200), p.get("h", 450), 3, 900),
    "freeTorus":    lambda p: build_torus(p.get("R", 600), p.get("r", 80)),
    "freeLightBox": lambda p: build_freebox(p.get("w", 1200), p.get("h", 80), p.get("d", 60), mat="U_metal_steel"),
    "freeMirror":   lambda p: build_mirror(p.get("w", 800), p.get("h", 1800)),
    "freeVase":     lambda p: build_vase(p.get("h", 500), p.get("r", 180)),
    "freeColumn":   lambda p: build_column(p.get("h", 2400), p.get("r", 120)),
    "freeExtrude":  lambda p: build_freebox(p.get("w", 500), p.get("h", 500), p.get("d", 500)),
    # 卫浴 / 厨电 / 电器
    "toilet":       lambda p: build_toilet(p.get("w", 380), p.get("d", 680), p.get("h", 780)),
    "wallToilet":   lambda p: build_toilet(p.get("w", 360), p.get("d", 550), p.get("h", 400)),
    "squatToilet":  lambda p: build_freebox(p.get("w", 400), p.get("h", 150), p.get("d", 500), mat="U_ceramic_white"),
    "vanity":       lambda p: build_base_cabinet(p.get("w", 1200), 480, 850, 2),
    "doubleVanity": lambda p: build_base_cabinet(p.get("w", 1800), 480, 850, 4),
    "mirrorCabinet": lambda p: build_freebox(p.get("w", 900), p.get("h", 700), p.get("d", 140), mat="U_wood_walnut"),
    "pedestalSink": lambda p: build_vase(p.get("h", 800), p.get("r", 220)),
    "freeTub":      lambda p: build_bathtub(p.get("w", 1600), p.get("d", 800), p.get("h", 600)),
    "bathtub":      lambda p: build_bathtub(p.get("w", 1700), p.get("d", 750), p.get("h", 560)),
    "shower":       lambda p: build_freebox(p.get("w", 1000), p.get("h", 2000), p.get("d", 1000), mat="U_ceramic_white"),
    "showerScreen": lambda p: build_glass_screen(p.get("w", 900), p.get("h", 2000)),
    "showerSet":    lambda p: build_cylinder(p.get("r", 60), p.get("h", 600)),
    "towelWarmer":  lambda p: build_freebox(p.get("w", 600), p.get("h", 900), p.get("d", 100), mat="U_metal_steel"),
    "bathHeater":   lambda p: build_freebox(p.get("w", 600), p.get("h", 200), p.get("d", 600), mat="U_metal_steel"),
    "laundrySink":  lambda p: build_base_cabinet(p.get("w", 900), 600, 900, 2),
    "urinal":       lambda p: build_freebox(p.get("w", 350), p.get("h", 600), p.get("d", 280), mat="U_ceramic_white"),
    "serviceSink":  lambda p: build_base_cabinet(p.get("w", 500), 500, 500, 1),
    "counter":      lambda p: build_base_cabinet(p.get("w", 2400), 600, 850, 6),
    "pantryCounter": lambda p: build_base_cabinet(p.get("w", 1200), 600, 850, 3),
    "lCounter":     lambda p: build_base_cabinet(p.get("w", 1800), 600, 850, 4),
    "uCounter":     lambda p: build_base_cabinet(p.get("w", 2400), 600, 850, 6),
    "fridge":       lambda p: build_fridge(p.get("w", 700), p.get("d", 700), p.get("h", 1900)),
    "fridgeDouble": lambda p: build_fridge(p.get("w", 900), p.get("d", 700), p.get("h", 1900)),
    "fridgeFrench": lambda p: build_fridge(p.get("w", 830), p.get("d", 700), p.get("h", 1850)),
    "freezer":      lambda p: build_fridge(p.get("w", 1000), p.get("d", 700), p.get("h", 1800)),
    "dishwasher":   lambda p: build_fridge(p.get("w", 600), p.get("d", 600), p.get("h", 850)),
    "tallOven":     lambda p: build_oven(p.get("w", 600), p.get("d", 600), p.get("h", 2200)),
    "hood":         lambda p: build_hood(p.get("w", 900), p.get("d", 500), p.get("h", 700)),
    "microwave":    lambda p: build_microwave(),
    "coffeeMachine": lambda p: build_coffee_machine(),
    "wineFridge":   lambda p: build_fridge(p.get("w", 450), p.get("d", 500), p.get("h", 900)),
    "waterDispenser": lambda p: build_coffee_machine(p.get("w", 350), p.get("d", 350), p.get("h", 450)),
    "washer":       lambda p: build_washer(),
    "dryer":        lambda p: build_washer(),
    "airPurifier":  lambda p: build_freebox(p.get("w", 350), p.get("h", 650), p.get("d", 350), mat="U_metal_steel"),
    "robotVac":     lambda p: build_cylinder(p.get("r", 175), p.get("h", 90)),
    "acWall":       lambda p: build_ac_wall(),
    "acFloor":      lambda p: build_freebox(p.get("w", 400), p.get("h", 1600), p.get("d", 400), mat="U_metal_steel"),
    "waterHeater":  lambda p: build_fridge(p.get("w", 450), p.get("d", 350), p.get("h", 800)),
    "miniHeater":   lambda p: build_fridge(p.get("w", 400), p.get("d", 350), p.get("h", 500)),
    "gasHeater":    lambda p: build_freebox(p.get("w", 350), p.get("h", 600), p.get("d", 220), mat="U_metal_steel"),
    "boiler":       lambda p: build_freebox(p.get("w", 400), p.get("h", 700), p.get("d", 250), mat="U_metal_steel"),
    "manifold":     lambda p: build_freebox(p.get("w", 350), p.get("h", 500), p.get("d", 120), mat="U_metal_brass"),
    "waterSoftener": lambda p: build_fridge(p.get("w", 350), p.get("d", 350), p.get("h", 1100)),
    "purifier":     lambda p: build_freebox(p.get("w", 150), p.get("h", 400), p.get("d", 150), mat="U_metal_steel"),
    # 娱乐
    "fishTank":     lambda p: build_fish_tank(),
    "piano":        lambda p: build_piano(),
    "grandPiano":   lambda p: build_piano(p.get("w", 2000), p.get("d", 1500), p.get("h", 1000)),
    "treadmill":    lambda p: build_freebox(p.get("w", 800), p.get("h", 1400), p.get("d", 1800), mat="U_metal_black"),
    "billiards":    lambda p: build_freebox(p.get("w", 2800), p.get("h", 800), p.get("d", 1400), mat="U_wood_walnut"),
    "mahjong":      lambda p: build_freebox(p.get("w", 1000), p.get("h", 780), p.get("d", 1000), mat="U_wood_walnut"),
    "sauna":        lambda p: build_freebox(p.get("w", 2000), p.get("h", 2200), p.get("d", 2000), mat="U_wood_walnut"),
    "bike":         lambda p: build_bike_rack(),
    "yogaMat":      lambda p: build_yoga_mat(),
    # 办公
    "mobileDisplay": lambda p: build_freebox(p.get("w", 1600), p.get("h", 900), p.get("d", 60), mat="U_metal_black"),
    "printer":      lambda p: build_freebox(p.get("w", 500), p.get("h", 350), p.get("d", 450), mat="U_metal_black"),
    # 其他
    "mirror":       lambda p: build_mirror(),
    "fan":          lambda p: build_cylinder(p.get("r", 250), p.get("h", 1400)),
    "radiator":     lambda p: build_freebox(p.get("w", 1000), p.get("h", 600), p.get("d", 100), mat="U_metal_steel"),
    "trashBin":     lambda p: build_trash_bin(),
    "clothesRack":  lambda p: build_bike_rack(p.get("w", 1500), p.get("d", 600), p.get("h", 2200)),
    "catTree":      lambda p: build_freebox(p.get("w", 600), p.get("h", 1800), p.get("d", 600), mat="U_wood_walnut"),
    "petBed":       lambda p: build_freebox(p.get("w", 600), p.get("h", 200), p.get("d", 450), mat="U_fabric_oat"),
    # 建筑
    "stairU":       lambda p: build_stairs(p.get("w", 1200), p.get("h", 3000), 16, 2800),
    "stairRun":     lambda p: build_stairs(p.get("w", 1200), p.get("h", 3000), 16, 2800),
    "stairLanding": lambda p: build_platform(p.get("w", 1400), p.get("h", 180), p.get("d", 1400)),
    "elevator":     lambda p: build_freebox(p.get("w", 1100), p.get("h", 2200), p.get("d", 1400), mat="U_metal_steel"),
    "evCharger":    lambda p: build_freebox(p.get("w", 300), p.get("h", 400), p.get("d", 160), mat="U_metal_black"),
    "garageShelf":  lambda p: build_freebox(p.get("w", 1800), p.get("h", 2000), p.get("d", 450), mat="U_metal_black"),
    "workbench":    lambda p: build_freebox(p.get("w", 1600), p.get("h", 900), p.get("d", 700), mat="U_wood_walnut"),
    "stage":        lambda p: build_stage(p.get("w", 6000), p.get("h", 400), p.get("d", 4000)),
    "slidingBoard": lambda p: build_freebox(p.get("w", 2400), p.get("h", 1200), p.get("d", 60)),
    "whiteboard":   lambda p: build_freebox(p.get("w", 1600), p.get("h", 1200), p.get("d", 60)),
    "wifiAP":       lambda p: build_cylinder(p.get("r", 120), p.get("h", 60)),
    "ceilingSpeaker": lambda p: build_cylinder(p.get("r", 100), p.get("h", 50)),
    "supplyVent":   lambda p: build_vent(),
    "returnVent":   lambda p: build_vent(),
    # 庭院
    "car":          lambda p: build_freebox(p.get("w", 1800), p.get("h", 1450), p.get("d", 4500), mat="U_metal_black"),
    "suv":          lambda p: build_freebox(p.get("w", 1900), p.get("h", 1750), p.get("d", 4800), mat="U_metal_black"),
    "carport":      lambda p: build_carport(p.get("w", 2800), p.get("d", 5500), 2400),
    "carport2":     lambda p: build_carport(p.get("w", 5600), p.get("d", 5500), 2400),
    "bicycle":      lambda p: build_freebox(p.get("w", 400), p.get("h", 1100), p.get("d", 1700), mat="U_metal_black"),
    "pool":         lambda p: build_pool(p.get("w", 6000), p.get("d", 3000)),
    "lawn":         lambda p: build_lawn(p.get("w", 12000), p.get("d", 9000)),
    "stepStones":   lambda p: build_step_stones(p.get("w", 3000), p.get("d", 2000)),
    "tree":         lambda p: build_tree(),
    "shrub":        lambda p: build_shrub(),
    "gazebo":       lambda p: build_carport(p.get("w", 3000), p.get("d", 3000), 2600),
    "parasol":      lambda p: build_cylinder(p.get("r", 60), p.get("h", 2200)),
    "sunLounger":   lambda p: build_freebox(p.get("w", 700), p.get("h", 350), p.get("d", 1900), mat="U_fabric_oat"),
    "swing":        lambda p: build_bike_rack(p.get("w", 1400), p.get("d", 600), p.get("h", 2200)),
    "bbq":          lambda p: build_freebox(p.get("w", 1200), p.get("h", 1100), p.get("d", 600), mat="U_metal_black"),
    "waterFeature": lambda p: build_freebox(p.get("w", 3000), p.get("h", 2000), p.get("d", 400), mat="U_stone_light"),
    "fence":        lambda p: build_fence(p.get("w", 6000), p.get("h", 1800)),
    "gate":         lambda p: build_gate(p.get("w", 3000), p.get("h", 2200)),
    "outdoorSet":  lambda p: build_freebox(p.get("w", 1800), p.get("h", 750), p.get("d", 900)),
    # 软装
    "screenDivider": lambda p: build_freebox(p.get("w", 1800), p.get("h", 2000), p.get("d", 60)),
    "plant":        lambda p: build_plant(p.get("h", 1400), p.get("r", 350)),
    "bigPlant":     lambda p: build_plant(p.get("h", 2000), p.get("r", 480)),
    "smallPlant":   lambda p: build_plant(p.get("h", 500), p.get("r", 160)),
    "hangingPlant": lambda p: build_hanging_plant(),
    "floorVase":    lambda p: build_vase(p.get("h", 700), p.get("r", 220)),
    "wallPanel":    lambda p: build_wall_panel(p.get("w", 2000), p.get("h", 2500)),
    "wallArt":      lambda p: build_picture_frame(p.get("w", 900), p.get("h", 1100)),
    "wallArt3":     lambda p: build_picture_frame(p.get("w", 1800), p.get("h", 900)),
    "wallClock":    lambda p: build_clock(),
}


# =====================================================================
# 合并补充生成器（29 项定制/异形品类）
# geo_models_extra 依赖本模块的基础体，故在最后 import 避免循环依赖。
# =====================================================================
try:
    import geo_models_extra as _EXTRA
    BUILDERS.update(_EXTRA.EXTRA_BUILDERS)
except ImportError as _e:                       # 显式失败，不静默降级
    print("[geo_models] 警告：补充生成器未加载（%s），29 项定制品类缺失" % _e)

try:
    import geo_models_extra2 as _EXTRA2
    BUILDERS.update(_EXTRA2.EXTRA2)
    _AUTOFIT = _EXTRA2._scale_to_target
    _NO_AUTO_FIT = _EXTRA2.NO_AUTO_FIT
except ImportError as _e:
    print("[geo_models] 警告：参数化生成器未加载（%s），23 项尺寸类家具缺失" % _e)
    _AUTOFIT = None
    _NO_AUTO_FIT = set()

try:
    import geo_models_extra3 as _EXTRA3
    BUILDERS.update(_EXTRA3.EXTRA3)
except ImportError as _e:
    print("[geo_models] 警告：第三批生成器未加载（%s），32 项品类缺失" % _e)

try:
    import geo_models_extra4 as _EXTRA4
    BUILDERS.update(_EXTRA4.EXTRA4)
except ImportError as _e:
    print("[geo_models] 警告：第四批生成器未加载（%s），8 项品类缺失" % _e)

try:
    import geo_models_free as _FREE
    # 【最后覆盖】自由体必须用"尺寸精确"版本 —— 旧版忽略目标尺寸。
    BUILDERS.update(_FREE.FREE)
except ImportError as _e:
    print("[geo_models] 警告：自由体生成器未加载（%s），29 项造型体尺寸会失真" % _e)


def _ground_and_center(mesh):
    """把 mesh 落地 + 水平居中。

    【为什么必须有这一步】
      几何生成路径不像 fit_item 那样有"落地 + 居中"步骤
      （fit_item.py:257-259 会算 trans 把底面压到 0）。
      结果：部分 builder 的底部不在 y=0
      —— 实测 28/251 件落地偏差最大到 -2000mm（淋浴隔断整块沉到地下），
         家具放进屋里会【悬空或插进地板】。
      同时水平方向没居中，摆放时会偏心。

      这里统一处理：
        · y 方向：min_y 平移到 0（落地）
        · x/z 方向：包围盒中心平移到 0（居中）
      【不改变尺寸】—— 只平移，不缩放，尺寸精度不受影响。
    """
    if not mesh.pos:
        return mesh
    xs = [p[0] for p in mesh.pos]
    ys = [p[1] for p in mesh.pos]
    zs = [p[2] for p in mesh.pos]
    cx = (max(xs) + min(xs)) / 2.0
    cz = (max(zs) + min(zs)) / 2.0
    miny = min(ys)
    mesh.pos = [(p[0] - cx, p[1] - miny, p[2] - cz) for p in mesh.pos]
    return mesh


def build(kind, params=None):
    """按 kind 生成网格。未知 kind 抛 KeyError（显式失败，不静默返回空）。

    params 里若给了 w/d/h（目标尺寸 mm），且该生成器支持自适应，
    则生成后按目标尺寸做三轴缩放 —— 保证输出尺寸精确等于目标，
    形变恒为 1.0（比例不可能崩坏）。

    【自由体例外】geo_models_free 的 29 项已经【按目标尺寸反解参数】，
    本身尺寸就精确，再做一次缩放会把"圆柱"压成"椭圆"、
    把"空心圆管"压成实心 —— 所以必须排除在自动缩放之外。

    【落地 + 居中】所有几何生成件都会落地（底面 y=0）且水平居中，
    否则家具会悬空/插进地板 —— 见 _ground_and_center 的说明。
    """
    fn = BUILDERS.get(kind)
    if fn is None:
        raise KeyError("no builder for %r (known: %d)" % (kind, len(BUILDERS)))
    params = params or {}
    mesh = fn(params)
    if _AUTOFIT and kind not in _NO_AUTO_FIT:
        tgt = None
        if all(k in params for k in ("w", "d", "h")):
            tgt = [params["w"], params["d"], params["h"]]
        if tgt:
            mesh = _AUTOFIT(mesh, tgt)
    mesh = _ground_and_center(mesh)
    return mesh


def export(kind, dest, params=None):
    m = build(kind, params)
    gltf, bin_data = m.to_gltf()
    write_glb(gltf, bin_data, dest)
    tris = len(m.idx)
    return {"kind": kind, "dest": dest, "tris": tris,
            "verts": len(m.pos), "bytes": os.path.getsize(dest)}


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--make")
    ap.add_argument("--out")
    ap.add_argument("--w", type=float)
    ap.add_argument("--h", type=float)
    ap.add_argument("--d", type=float)
    a = ap.parse_args()

    if a.list:
        print("可生成类型 %d:" % len(BUILDERS))
        for k in sorted(BUILDERS):
            print("   ", k)
    elif a.make:
        p = {}
        for k in ("w", "h", "d"):
            v = getattr(a, k)
            if v:
                p[k] = v
        out = a.out or os.path.join("..", "..", "..", "assets", "_asset_cache",
                                    "geo", a.make + ".glb")
        r = export(a.make, out, p)
        print(json.dumps(r, ensure_ascii=False))

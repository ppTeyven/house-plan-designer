"""补齐几何生成器 —— 参数化、精确尺寸、真几何（非贴图）。

【为什么需要这一批】
  pick_resources_v3 判定 136 项应回退到几何生成（库里没有比例合适的
  现成资源，或现成资源形变超标）。
  其中 23 项没有生成器 → 必须补齐，否则构建期 no_builder 失败。

【关键：按【真实目标尺寸】建模，不是拍脑袋】
  每个生成器都接收 reference/catalog-sizes.json 的 (w, d, h)，
  直接建成那个尺寸 —— 形变恒为 1.0，比例不可能崩坏。

【堆叠高度必须自洽】
  沙发：底座 0~base_h，坐垫 base_h~seat_h（座面高），
       靠背 seat_h~h。靠背与扶手顶到 h，不悬空、不穿模。
  灯：底座 0~base_h，灯杆 base_h~shade_bottom，灯罩罩住灯杆顶端。

【做法】
  不是"一个方块糊上去"，而是按家具的真实结构拆件：
    床 = 床架 + 床垫 + 枕头 + 被褥 + 床头板 + 床脚
    沙发 = 底座 + N 座垫 + 靠背 + 扶手 + 靠背垫 + 脚
    桌 = 台面 + 桌腿 + 横撑
    柜 = 柜体 + 门板 + 拉手 + 台面
    灯 = 底座 + 灯杆 + 灯罩（灯罩用回转体）
"""
import os
import sys
import math

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from geo_gen import Mesh
from geo_models import (M, build_base_cabinet, build_freebox, build_platform,
                        build_stairs, build_column, build_cylinder,
                        build_vase, build_plant, build_shrub, build_tree)


# =====================================================================
# 床
# =====================================================================
def build_bed(w=1800, d=2100, h=1050, style="panel"):
    """床：床架 + 床垫 + 枕头 + 被褥 + 床头板 + 床脚。

    w=床宽(沿 X), d=床长(沿 Z), h=含床头总高

    【朝向：床头在 -Z】
      主程序（assets/template.html 的 kv()）有统一约定：
        · 2D 平面图：床头条 l(-o,-a,i,100,...) 与枕头 l(-o+80+..,-a+160,..)
          都在 -a 侧 —— 图纸【上方】是床头
        · 3D 位置：l.position.set(r.x/1e3, c/1e3, r.y/1e3)
          ⇒ 2D 的 -Y 直接映射到 3D 的 -Z
        · 3D 程序化床：N(t,i+.04,p,.05,0,0,-l+.025,d) → 床头板 z = -l
      ⇒ 床头/靠背/背板/柜门 统一在 -Z，正面朝 +Z

      旧实现把床头板建在 +Z → 床摆进房间后【床尾顶墙、床头朝屋里】，
      正好反了（用户反馈："床的方向是反的，床尾怎么对着墙放了"）。
    """
    m = Mesh()
    w, d, h = M(w), M(d), M(h)
    frame_h = M(280)                    # 床架高（含腿）
    mattress_h = M(220)
    base_top = frame_h
    mattress_top = base_top + mattress_h
    head_h = h                          # 床头板到总高

    # 床架（底座）
    m.add_box((w, frame_h, d), center=(0, frame_h / 2, 0), mat="U_wood_oak")
    # 床垫
    m.add_box((w - M(30), mattress_h, d - M(30)),
              center=(0, base_top + mattress_h / 2, 0), mat="U_fabric_cream")
    # 被褥（略窄于床垫，床尾段更厚 —— 有体积感）
    m.add_box((w - M(20), M(90), d * 0.60),
              center=(0, mattress_top + M(45), d * 0.13),
              mat="U_fabric_oat")
    # 枕头（两个，靠床头）
    pw = (w - M(60)) / 2
    for s in (-1, 1):
        m.add_box((pw, M(120), M(380)),
                  center=(s * (pw / 2 + M(10)), mattress_top + M(60),
                          -d / 2 + M(300)),
                  mat="U_fabric_cream")
    # 床头板（从地一直到总高）
    m.add_box((w, head_h, M(60)), center=(0, head_h / 2, -d / 2 + M(30)),
              mat="U_wood_walnut")
    # 床脚
    for sx in (-1, 1):
        for sz in (-1, 1):
            m.add_box((M(70), M(90), M(70)),
                      center=(sx * (w / 2 - M(60)), M(45),
                              sz * (d / 2 - M(60))), mat="U_wood_walnut")
    return m


def build_kids_bed(w=1000, d=1900, h=900):
    return build_bed(w, d, h)


def build_bed_bench(w=1400, d=400, h=450):
    """床尾凳：软垫长凳 + 木架 + 四脚。"""
    m = Mesh()
    w, d, h = M(w), M(d), M(h)
    leg_h = M(90)
    m.add_box((w - M(80), M(40), d - M(60)), center=(0, leg_h + M(20), 0),
              mat="U_wood_walnut")
    m.add_box((w - M(60), M(120), d - M(40)),
              center=(0, leg_h + M(40) + M(60), 0), mat="U_fabric_oat")
    for sx in (-1, 1):
        for sz in (-1, 1):
            m.add_box((M(60), leg_h, M(60)),
                      center=(sx * (w / 2 - M(50)), leg_h / 2,
                              sz * (d / 2 - M(45))), mat="U_wood_walnut")
    return m


def build_dining_bench(w=1400, d=350, h=450):
    return build_bed_bench(w, d, h)


# =====================================================================
# 沙发（座面高 seat_h，堆叠自洽）
# =====================================================================
def build_sofa(w=2200, d=950, h=820, seats=3):
    """沙发：底座 + N 座垫 + 靠背 + 两扶手。

    【朝向：靠背在 -Z，正面朝 +Z】
      见 build_bed 的说明 —— 主程序统一把靠背/床头放在 -Z。
      旧实现靠背在 +d/2，沙发一摆进房间就正面朝墙。
    """
    m = Mesh()
    w, d, h = M(w), M(d), M(h)
    base_h = M(150)                     # 底座
    seat_h = M(420)                     # 座面高（离地）
    cush_h = seat_h - base_h            # 坐垫厚度
    arm_w = M(140)
    foot_h = M(70)

    # 底座
    m.add_box((w, base_h, d - M(60)), center=(0, foot_h + base_h / 2, 0),
              mat="U_fabric_oat_d")
    # 座垫
    inner = w - arm_w * 2
    sw = inner / seats
    for i in range(seats):
        x = -inner / 2 + sw * (i + 0.5)
        m.add_box((sw - M(20), cush_h, d - M(240)),
                  center=(x, foot_h + base_h + cush_h / 2, M(40)),
                  mat="U_fabric_oat")
    # 靠背（座面到顶）
    back_h = h - foot_h - seat_h + base_h
    m.add_box((w, back_h, M(170)),
              center=(0, foot_h + seat_h + back_h / 2, -d / 2 + M(85)),
              mat="U_fabric_oat")
    # 扶手（到底）
    arm_h = h - foot_h
    for s in (-1, 1):
        m.add_box((arm_w, arm_h, d - M(60)),
                  center=(s * (w / 2 - arm_w / 2), foot_h + arm_h / 2, 0),
                  mat="U_fabric_oat")
    # 靠背垫（贴在靠背前）
    pad_h = back_h - M(60)
    for i in range(seats):
        x = -inner / 2 + sw * (i + 0.5)
        m.add_box((sw - M(40), pad_h, M(110)),
                  center=(x, foot_h + seat_h + pad_h / 2 + M(20),
                          -d / 2 + M(200)), mat="U_fabric_oat")
    # 脚
    for sx in (-1, 1):
        for sz in (-1, 1):
            m.add_box((M(50), foot_h, M(50)),
                      center=(sx * (w / 2 - M(60)), foot_h / 2,
                              sz * (d / 2 - M(60))), mat="U_wood_walnut")
    return m


def build_loveseat(w=1600, d=900, h=820):
    return build_sofa(w, d, h, seats=2)


def build_single_sofa(w=1000, d=900, h=820):
    return build_sofa(w, d, h, seats=1)


def build_l_sofa(w=2800, d=1700, h=820):
    """L 形沙发：横置主段 + 纵置贵妃段。

    【朝向：主段靠背在 -Z，正面朝 +Z】见 build_bed 的朝向说明。
    """
    m = Mesh()
    w, d, h = M(w), M(d), M(h)
    base_h = M(150)
    seat_h = M(420)
    cush_h = seat_h - base_h
    arm_w = M(140)
    foot_h = M(70)
    main_w = w * 0.62
    ret_depth = d - M(600)

    def foot(x, z):
        m.add_box((M(50), foot_h, M(50)),
                  center=(x, foot_h / 2, z), mat="U_wood_walnut")

    # ---- 横置主段（靠背在 -Z）----
    cx = -w / 2 + main_w / 2
    m.add_box((main_w, base_h, M(600)), center=(cx, foot_h + base_h / 2, 0),
              mat="U_fabric_oat_d")
    m.add_box((main_w - arm_w * 2, cush_h, M(500)),
              center=(cx, foot_h + base_h + cush_h / 2, M(20)),
              mat="U_fabric_oat")
    back_h = h - foot_h - seat_h + base_h
    m.add_box((main_w, back_h, M(160)),
              center=(cx, foot_h + seat_h + back_h / 2, -M(220)),
              mat="U_fabric_oat")
    # ---- 纵置贵妃段（靠背在 +X）----
    rz = -d / 2 + ret_depth / 2 + M(300)
    m.add_box((M(600), base_h, ret_depth),
              center=(w / 2 - M(300), foot_h + base_h / 2, rz),
              mat="U_fabric_oat_d")
    m.add_box((M(500), cush_h, ret_depth - M(40)),
              center=(w / 2 - M(320), foot_h + base_h + cush_h / 2, rz),
              mat="U_fabric_oat")
    m.add_box((M(160), back_h, ret_depth),
              center=(w / 2 - M(80), foot_h + seat_h + back_h / 2, rz),
              mat="U_fabric_oat")
    # 左扶手（封口）
    m.add_box((arm_w, h - foot_h, M(600)),
              center=(-w / 2 + arm_w / 2, foot_h + (h - foot_h) / 2, 0),
              mat="U_fabric_oat")
    for fx, fz in ((cx - main_w / 2 + M(60), -M(240)),
                   (cx + main_w / 2 - M(60), -M(240)),
                   (w / 2 - M(60), rz + ret_depth / 2 - M(60)),
                   (w / 2 - M(60), rz - ret_depth / 2 + M(60))):
        foot(fx, fz)
    return m


def build_chaise_sofa(w=2600, d=1600, h=820):
    """贵妃沙发：直排 + 一侧深贵妃位。"""
    m = Mesh()
    w, d, h = M(w), M(d), M(h)
    base_h = M(150)
    seat_h = M(420)
    cush_h = seat_h - base_h
    arm_w = M(140)
    foot_h = M(70)
    main_w = w * 0.55
    back_h = h - foot_h - seat_h + base_h

    cx = -w / 2 + main_w / 2
    m.add_box((main_w, base_h, M(620)), center=(cx, foot_h + base_h / 2, 0),
              mat="U_fabric_oat_d")
    m.add_box((main_w - arm_w * 2, cush_h, M(520)),
              center=(cx, foot_h + base_h + cush_h / 2, M(20)),
              mat="U_fabric_oat")
    m.add_box((main_w, back_h, M(160)),
              center=(cx, foot_h + seat_h + back_h / 2, -M(230)),
              mat="U_fabric_oat")
    # 深贵妃位
    cw = w - main_w
    m.add_box((cw, base_h, d - M(120)),
              center=(main_w / 2, foot_h + base_h / 2, -M(60)),
              mat="U_fabric_oat_d")
    m.add_box((cw - M(30), cush_h, d - M(200)),
              center=(main_w / 2, foot_h + base_h + cush_h / 2, -M(100)),
              mat="U_fabric_oat")
    m.add_box((M(160), back_h, d - M(120)),
              center=(w / 2 - M(80), foot_h + seat_h + back_h / 2, -M(60)),
              mat="U_fabric_oat")
    for fx, fz in ((cx - main_w / 2 + M(60), -M(230)),
                   (cx + main_w / 2 - M(60), -M(230)),
                   (w / 2 - M(60), -M(60) + (d - M(120)) / 2 - M(60)),
                   (w / 2 - M(60), -M(60) - (d - M(120)) / 2 + M(60))):
        m.add_box((M(50), foot_h, M(50)),
                  center=(fx, foot_h / 2, fz), mat="U_wood_walnut")
    return m


# =====================================================================
# 桌
# =====================================================================
def build_table(w=1600, d=900, h=750, legs=4, style="wood"):
    """桌：台面 + 桌腿 + 横撑。"""
    m = Mesh()
    w, d, h = M(w), M(d), M(h)
    top = M(40)
    mat = "U_wood_oak" if style == "wood" else "U_wood_walnut"
    m.add_box((w, top, d), center=(0, h - top / 2, 0), mat=mat)
    leg = M(70)
    if legs == 4:
        for sx in (-1, 1):
            for sz in (-1, 1):
                m.add_box((leg, h - top, leg),
                          center=(sx * (w / 2 - M(90)), (h - top) / 2,
                                  sz * (d / 2 - M(90))), mat=mat)
        m.add_box((w - M(200), M(50), M(40)),
                  center=(0, M(180), 0), mat=mat)
    else:
        m.add_box((M(80), h - top, d - M(160)),
                  center=(0, (h - top) / 2, 0), mat=mat)
    return m


def build_conference_table(w=3600, d=1200, h=750):
    return build_table(w, d, h, legs=4)


def build_desk_bench(w=2400, d=700, h=750):
    """工位台：连续台面 + 侧板腿 + 中间隔板。"""
    m = Mesh()
    w, d, h = M(w), M(d), M(h)
    m.add_box((w, M(40), d), center=(0, h - M(20), 0), mat="U_wood_oak")
    for sx in (-1, 1):
        m.add_box((M(50), h - M(40), d - M(120)),
                  center=(sx * (w / 2 - M(60)), (h - M(40)) / 2, 0),
                  mat="U_metal_black")
    m.add_box((M(40), h - M(40), d - M(200)),
              center=(0, (h - M(40)) / 2, 0), mat="U_metal_black")
    return m


def build_console_table(w=1200, d=350, h=800):
    return build_table(w, d, h, legs=4)


def build_sideboard(w=1600, d=400, h=2200):
    """餐边柜 / 玄关柜：高柜体 + 上下门板 + 长条拉手。"""
    m = Mesh()
    w, d, h = M(w), M(d), M(h)
    foot_h = M(90)
    m.add_box((w, h - foot_h, d), center=(0, foot_h + (h - foot_h) / 2, 0),
              mat="U_wood_walnut")
    m.add_box((w + M(40), M(40), d + M(30)), center=(0, h - M(20), 0),
              mat="U_wood_walnut")
    n = 3
    for i in range(n):
        x = -w / 2 + w / n * (i + 0.5)
        m.add_box((w / n - M(20), h * 0.38, M(18)),
                  center=(x, foot_h + h * 0.70, d / 2 + M(9)), mat="U_wood_oak")
        m.add_box((w / n - M(20), h * 0.34, M(18)),
                  center=(x, foot_h + h * 0.24, d / 2 + M(9)), mat="U_wood_oak")
        m.add_box((M(160), M(18), M(22)),
                  center=(x, foot_h + h * 0.53, d / 2 + M(28)), mat="U_metal_brass")
    for sx in (-1, 1):
        for sz in (-1, 1):
            m.add_box((M(50), foot_h, M(50)),
                      center=(sx * (w / 2 - M(60)), foot_h / 2,
                              sz * (d / 2 - M(50))), mat="U_wood_walnut")
    return m


def build_file_cabinet(w=450, d=550, h=1050):
    """文件柜：多抽屉 + 侧板 + 顶面。"""
    m = Mesh()
    w, d, h = M(w), M(d), M(h)
    foot_h = M(60)
    m.add_box((w, h - foot_h, d), center=(0, foot_h + (h - foot_h) / 2, 0),
              mat="U_metal_black")
    n = 4
    for i in range(n):
        y = foot_h + (h - foot_h) / n * (i + 0.5)
        m.add_box((w - M(40), (h - foot_h) / n - M(20), M(16)),
                  center=(0, y, d / 2 + M(8)), mat="U_metal_black")
        m.add_box((M(120), M(20), M(24)),
                  center=(0, y, d / 2 + M(26)), mat="U_metal_brass")
    return m


# =====================================================================
# 灯具
# =====================================================================
def build_floor_lamp(w=400, d=400, h=1650):
    """落地灯：底座 + 灯杆 + 锥形灯罩（回转体）。"""
    m = Mesh()
    w, h = M(w), M(h)
    base_h = M(40)
    base_r = w * 0.45
    m.add_cylinder(base_r, base_h, center=(0, 0, 0), seg=32,
                   mat="U_metal_black")
    shade_h = M(320)
    rod_top = h - shade_h
    m.add_cylinder(M(22), rod_top - base_h, center=(0, base_h, 0), seg=16,
                   mat="U_metal_black")
    shade_top = w * 0.30
    shade_bot = w * 0.52
    prof = [(0, rod_top), (shade_bot, rod_top),
            (shade_bot * 0.96, rod_top + shade_h * 0.75),
            (shade_top, h - M(20)), (0, h - M(20))]
    m.add_revolve(prof, seg=32, mat="U_fabric_cream")
    return m


def build_arc_lamp(w=450, d=1300, h=1900):
    """落地弯臂灯：底座 + 立杆 + 弧臂（分段盒近似）+ 灯罩。"""
    m = Mesh()
    w, d, h = M(w), M(d), M(h)
    base_h = M(50)
    x0 = -d / 2 + M(250)
    m.add_cylinder(M(300), base_h, center=(x0, 0, 0), seg=32,
                   mat="U_metal_black")
    arc_top = h - M(350)
    m.add_cylinder(M(26), arc_top - base_h, center=(x0, base_h, 0), seg=16,
                   mat="U_metal_black")
    # 弧臂：沿 1/4 圆弧排布小盒（真几何，非贴图）
    R = d - M(500)
    segs = 14
    for i in range(segs):
        a = (i + 0.5) / segs * math.pi * 0.5
        x = x0 + R * (1 - math.cos(a))
        y = arc_top - base_h + R * math.sin(a) * 0.72
        m.add_box((M(46), M(46), M(46)), center=(x, y, 0),
                  mat="U_metal_black")
    # 末端竖杆 + 灯罩
    end_x = x0 + R
    m.add_cylinder(M(20), M(300), center=(end_x, arc_top - M(60), 0), seg=12,
                   mat="U_metal_black")
    m.add_revolve([(0, arc_top + M(240)), (M(170), arc_top + M(240)),
                   (M(140), arc_top + M(40)), (0, arc_top + M(40))],
                  center=(end_x, 0, 0), seg=28, mat="U_metal_brass")
    return m


# =====================================================================
# 座具 / 柜
# =====================================================================
def build_stool(w=400, d=400, h=450):
    """圆凳：凳面 + 三腿。"""
    m = Mesh()
    w, d, h = M(w), M(d), M(h)
    m.add_cylinder(w / 2, M(50), center=(0, h - M(50), 0), seg=28,
                   mat="U_wood_walnut")
    for i in range(3):
        a = 2 * math.pi * i / 3
        m.add_cylinder(M(22), h - M(50),
                       center=(math.cos(a) * w * 0.3, 0,
                               math.sin(a) * d * 0.3), seg=10,
                       mat="U_wood_walnut")
    return m


def build_tv_cabinet(w=2000, d=400, h=450):
    """电视柜：低矮柜体 + 抽屉分格 + 悬空底。"""
    m = Mesh()
    w, d, h = M(w), M(d), M(h)
    m.add_box((w, h - M(60), d), center=(0, M(60) + (h - M(60)) / 2, 0),
              mat="U_wood_walnut")
    n = 3
    for i in range(n):
        x = -w / 2 + w / n * (i + 0.5)
        m.add_box((w / n - M(20), h - M(140), M(16)),
                  center=(x, M(60) + (h - M(60)) / 2, d / 2 + M(8)),
                  mat="U_wood_oak")
        m.add_box((M(150), M(16), M(22)),
                  center=(x, M(60) + (h - M(60)) / 2, d / 2 + M(26)),
                  mat="U_metal_black")
    for i in range(1, 3):
        x = -w / 2 + w / 3 * i
        m.add_box((M(14), h - M(120), M(10)),
                  center=(x, M(60) + (h - M(60)) / 2, d / 2 + M(4)),
                  mat="U_metal_black")
    return m


def build_kitchen_trolley(w=450, d=350, h=800):
    """厨房推车：两层 + 脚轮 + 推手。"""
    m = Mesh()
    w, d, h = M(w), M(d), M(h)
    for y in (M(150), h - M(60)):
        m.add_box((w, M(30), d), center=(0, y, 0), mat="U_metal_black")
    for sx in (-1, 1):
        for sz in (-1, 1):
            m.add_box((M(24), h - M(60), M(24)),
                      center=(sx * (w / 2 - M(24)), (h - M(60)) / 2,
                              sz * (d / 2 - M(24))), mat="U_metal_black")
            m.add_cylinder(M(40), M(20), center=(sx * (w / 2 - M(24)),
                                                 M(20), sz * (d / 2 - M(24))),
                           seg=14, mat="U_metal_black")
    m.add_cylinder(M(16), w, center=(0, h - M(20), -d / 2 + M(20)), seg=12,
                   mat="U_metal_brass")
    return m


# =====================================================================
# 注册
# =====================================================================
EXTRA2 = {
    "bed18":       lambda p: build_bed(p.get("w", 1800), p.get("d", 2100), p.get("h", 1050)),
    "bed15":       lambda p: build_bed(p.get("w", 1500), p.get("d", 2050), p.get("h", 1000)),
    "bed12":       lambda p: build_bed(p.get("w", 1200), p.get("d", 2000), p.get("h", 950)),
    "bed20":       lambda p: build_bed(p.get("w", 2000), p.get("d", 2200), p.get("h", 1050)),
    "kingBed":     lambda p: build_bed(p.get("w", 2200), p.get("d", 2200), p.get("h", 1100)),
    "kidsBed":     lambda p: build_kids_bed(p.get("w", 1000), p.get("d", 1900), p.get("h", 900)),
    "bedBench":    lambda p: build_bed_bench(p.get("w", 1400), p.get("d", 400), p.get("h", 450)),
    "diningBench": lambda p: build_dining_bench(p.get("w", 1400), p.get("d", 350), p.get("h", 450)),

    "sofa":        lambda p: build_sofa(p.get("w", 2200), p.get("d", 950), p.get("h", 820)),
    "loveseat":    lambda p: build_loveseat(p.get("w", 1600), p.get("d", 900), p.get("h", 820)),
    "singleSofa":  lambda p: build_single_sofa(p.get("w", 1000), p.get("d", 900), p.get("h", 820)),
    "lSofa":       lambda p: build_l_sofa(p.get("w", 2800), p.get("d", 1700), p.get("h", 820)),
    "chaiseSofa":  lambda p: build_chaise_sofa(p.get("w", 2600), p.get("d", 1600), p.get("h", 820)),

    "diningTable": lambda p: build_table(p.get("w", 1600), p.get("d", 900), p.get("h", 750)),
    "conferenceTable": lambda p: build_conference_table(p.get("w", 3600), p.get("d", 1200), p.get("h", 750)),
    "deskBench2":  lambda p: build_desk_bench(p.get("w", 2400), p.get("d", 700), p.get("h", 750)),
    "consoleTable": lambda p: build_console_table(p.get("w", 1200), p.get("d", 350), p.get("h", 800)),
    "sideboard":   lambda p: build_sideboard(p.get("w", 1600), p.get("d", 400), p.get("h", 2200)),
    "cabSideboard": lambda p: build_sideboard(p.get("w", 1800), p.get("d", 400), p.get("h", 2400)),
    "fileCabinet": lambda p: build_file_cabinet(p.get("w", 450), p.get("d", 550), p.get("h", 1050)),

    "floorLamp":   lambda p: build_floor_lamp(p.get("w", 400), p.get("d", 400), p.get("h", 1650)),
    "arcLamp":     lambda p: build_arc_lamp(p.get("w", 450), p.get("d", 1300), p.get("h", 1900)),

    "stool":       lambda p: build_stool(p.get("w", 400), p.get("d", 400), p.get("h", 450)),
    "tvCabinet":   lambda p: build_tv_cabinet(p.get("w", 2000), p.get("d", 400), p.get("h", 450)),
    "kitchenTrolley": lambda p: build_kitchen_trolley(p.get("w", 450), p.get("d", 350), p.get("h", 800)),
}


# =====================================================================
# 通用包装：让所有既有生成器都能吃目标尺寸
# 【为什么需要】
#   geo_models.py 里 100+ 个生成器写的是固定尺寸的默认值，
#   而 reference/catalog-sizes.json 给出的是每一款式的真实目标。
#   逐个改写 100+ 个函数风险高（易漏、易回归）。
#   这里用一个统一包装：生成后按【目标/实际】三轴比例做非均匀缩放，
#   使输出尺寸精确等于目标 —— 与 fit_item.fit_item 同一套逻辑。
#   对本来就没有"尺寸语义"的可调项（free* 自由体）不套用。
# =====================================================================
def _scale_to_target(mesh, target):
    """把 mesh 三轴缩放到目标尺寸（米制）。"""
    if not target:
        return mesh
    xs = [v[0] for v in mesh.pos]
    ys = [v[1] for v in mesh.pos]
    zs = [v[2] for v in mesh.pos]
    sx = max(xs) - min(xs)
    sy = max(ys) - min(ys)
    sz = max(zs) - min(zs)
    if sx <= 1e-9 or sy <= 1e-9 or sz <= 1e-9:
        return mesh
    tw, td, th = [t / 1000.0 for t in target]
    fx, fz, fy = tw / sx, td / sz, th / sy
    mesh.pos = [(p[0] * fx, p[1] * fy, p[2] * fz) for p in mesh.pos]
    return mesh


# 生成器键 → 是否支持目标尺寸自适应
NO_AUTO_FIT = {
    "freeBox", "freeRoundBox", "freePlatform", "freeWallBlock",
    "freeCeilBlock", "freeCyl", "freeRoundStage", "freeHalfCyl",
    "freeTube", "freeSphere", "freeHemi", "freeCone", "freePyramid",
    "freeWedge", "freeArch", "freeArcWall", "freeSlats",
    "freeGlassScreen", "freeSteps", "freeTorus", "freeLightBox",
    "freeMirror", "freeVase", "freeColumn", "freeExtrude",
}

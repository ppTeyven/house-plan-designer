"""第三批生成器 —— 补齐 32 项缺口的参数化家具。

【为什么需要】
  pick_resources_v5 判定 211 项走几何生成（库里无比例合适的现成资源），
  其中 32 项没有对应生成器 → 必须补齐，否则构建期 no_builder。

【统一做法】
  全部按 reference/catalog-sizes.json 的目标尺寸建（形变恒为 1.0），
  且按真实结构拆件，不是一个方块糊上去。
"""
import os
import sys
import math

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from geo_gen import Mesh
from geo_models import M, build_base_cabinet, build_cylinder


# =====================================================================
# 椅子
# =====================================================================
def build_armchair(w=850, d=850, h=800):
    """扶手椅：底座 + 坐垫 + 靠背 + 两扶手 + 四腿。

    【朝向：靠背在 -Z，正面朝 +Z】见 build_bed 的朝向说明。
    """
    m = Mesh()
    w, d, h = M(w), M(d), M(h)
    seat_h = M(420)
    leg_h = M(180)
    cushion_h = seat_h - leg_h
    arm_w = M(110)

    m.add_box((w - M(60), cushion_h, d - M(60)),
              center=(0, leg_h + cushion_h / 2, M(20)), mat="U_fabric_oat")
    # 靠背
    back_h = h - leg_h
    m.add_box((w, back_h, M(130)),
              center=(0, leg_h + back_h / 2, -d / 2 + M(65)), mat="U_fabric_oat")
    # 扶手
    for s in (-1, 1):
        m.add_box((arm_w, M(230), d - M(60)),
                  center=(s * (w / 2 - arm_w / 2), leg_h + cushion_h + M(115), M(20)),
                  mat="U_fabric_oat")
    # 腿
    for sx in (-1, 1):
        for sz in (-1, 1):
            m.add_box((M(55), leg_h, M(55)),
                      center=(sx * (w / 2 - M(70)), leg_h / 2,
                              sz * (d / 2 - M(70))), mat="U_wood_walnut")
    return m


def build_arm_dining_chair(w=560, d=560, h=820):
    """扶手餐椅。【朝向：靠背在 -Z，正面朝 +Z】见 build_bed 的朝向说明。"""
    m = Mesh()
    w, d, h = M(w), M(d), M(h)
    seat_h = M(460)
    m.add_box((w - M(40), M(60), d - M(40)), center=(0, seat_h - M(30), 0),
              mat="U_wood_walnut")
    m.add_box((w - M(60), M(50), d - M(60)), center=(0, seat_h + M(25), 0),
              mat="U_fabric_oat")
    # 靠背
    m.add_box((w - M(40), h - seat_h - M(60), M(45)),
              center=(0, seat_h + (h - seat_h - M(60)) / 2 + M(30), -d / 2 + M(40)),
              mat="U_wood_walnut")
    # 前腿
    for sx in (-1, 1):
        m.add_box((M(45), seat_h - M(60), M(45)),
                  center=(sx * (w / 2 - M(45)), (seat_h - M(60)) / 2, d / 2 - M(45)),
                  mat="U_wood_walnut")
    # 后腿连靠背
    for sx in (-1, 1):
        m.add_box((M(45), h - M(60), M(45)),
                  center=(sx * (w / 2 - M(45)), (h - M(60)) / 2, -d / 2 + M(45)),
                  mat="U_wood_walnut")
    # 扶手
    for s in (-1, 1):
        m.add_box((M(40), M(40), d - M(140)),
                  center=(s * (w / 2 - M(30)), seat_h + M(200), -M(20)),
                  mat="U_wood_walnut")
    return m


def build_office_chair(w=600, d=600, h=1050):
    """办公椅：五星脚 + 升降杆 + 座 + 靠背 + 扶手。

    【朝向：靠背在 -Z，正面朝 +Z】见 build_bed 的朝向说明。
    """
    m = Mesh()
    w, d, h = M(w), M(d), M(h)
    seat_h = M(480)
    # 五星脚
    for i in range(5):
        a = 2 * math.pi * i / 5
        m.add_box((M(300), M(45), M(60)),
                  center=(math.cos(a) * M(140), M(60), math.sin(a) * M(140)),
                  mat="U_metal_black")
        m.add_cylinder(M(35), M(30), center=(math.cos(a) * M(280), M(30),
                                            math.sin(a) * M(280)),
                       seg=12, mat="U_metal_black")
    m.add_cylinder(M(45), seat_h - M(90), center=(0, M(90), 0), seg=14,
                   mat="U_metal_black")
    # 座
    m.add_box((w * 0.88, M(90), d * 0.88), center=(0, seat_h - M(45), 0),
              mat="U_fabric_grey")
    # 靠背
    m.add_box((w * 0.84, h - seat_h, M(110)),
              center=(0, seat_h + (h - seat_h) / 2, -d * 0.34), mat="U_fabric_grey")
    # 扶手
    for s in (-1, 1):
        m.add_box((M(50), M(180), M(240)),
                  center=(s * w * 0.46, seat_h + M(120), -M(20)),
                  mat="U_fabric_grey")
    return m


def build_training_chair(w=500, d=500, h=830):
    """培训椅：座板 + 靠背 + 四腿（叠放椅造型）。

    【朝向：靠背在 -Z，正面朝 +Z】见 build_bed 的朝向说明。
    """
    m = Mesh()
    w, d, h = M(w), M(d), M(h)
    seat_h = M(450)
    m.add_box((w, M(45), d), center=(0, seat_h, 0), mat="U_wood_oak")
    m.add_box((w - M(20), M(35), d - M(20)), center=(0, seat_h + M(38), 0),
              mat="U_fabric_oat")
    m.add_box((w - M(30), h - seat_h - M(70), M(40)),
              center=(0, seat_h + M(45) + (h - seat_h - M(70)) / 2, -d / 2 + M(30)),
              mat="U_wood_oak")
    for sx in (-1, 1):
        for sz in (-1, 1):
            m.add_box((M(38), seat_h - M(22), M(38)),
                      center=(sx * (w / 2 - M(40)), (seat_h - M(22)) / 2,
                              sz * (d / 2 - M(40))), mat="U_metal_black")
    # 横撑
    m.add_box((w - M(90), M(28), M(28)),
              center=(0, M(180), -d / 2 + M(40)), mat="U_metal_black")
    return m


def build_bar_stool(w=400, d=400, h=750):
    """吧椅：圆座 + 高脚 + 脚踏圈。"""
    m = Mesh()
    w, d, h = M(w), M(d), M(h)
    m.add_cylinder(w / 2, M(60), center=(0, h - M(60), 0), seg=28,
                   mat="U_wood_walnut")
    leg_h = h - M(60)
    for i in range(4):
        a = math.pi * 0.25 + i * math.pi * 0.5
        m.add_cylinder(M(20), leg_h,
                       center=(math.cos(a) * w * 0.32, 0,
                               math.sin(a) * d * 0.32), seg=10,
                       mat="U_metal_black")
    # 脚踏
    m.add_cylinder(w * 0.36, M(18), center=(0, M(200), 0), seg=24,
                   mat="U_metal_brass", radius_top=w * 0.36)
    return m


def build_rocking_chair(w=700, d=950, h=900):
    """摇椅：座 + 靠背 + 两根弧形摇杆。

    【朝向：靠背在 -Z，正面朝 +Z】见 build_bed 的朝向说明。
    """
    m = Mesh()
    w, d, h = M(w), M(d), M(h)
    seat_h = M(430)
    m.add_box((w - M(60), M(70), d * 0.52), center=(0, seat_h, -M(40)),
              mat="U_wood_oak")
    m.add_box((w - M(90), M(50), d * 0.48), center=(0, seat_h + M(60), -M(40)),
              mat="U_fabric_oat")
    m.add_box((w - M(70), h - seat_h - M(60), M(55)),
              center=(0, seat_h + M(70) + (h - seat_h - M(60)) / 2,
                      -(d * 0.24 + M(40))), mat="U_wood_oak")
    # 摇杆（弧形用多段盒近似）
    for s in (-1, 1):
        x = s * (w / 2 - M(50))
        segs = 7
        for i in range(segs):
            t = i / (segs - 1)
            y = M(120) * math.sin(math.pi * t)
            z = d * 0.34 - d * 0.62 * t
            m.add_box((M(50), M(60), M(60)), center=(x, y, z), mat="U_wood_oak")
    return m


def build_entry_bench(w=900, d=350, h=450):
    """换鞋凳：软垫 + 木架 + 四腿。"""
    m = Mesh()
    w, d, h = M(w), M(d), M(h)
    leg_h = M(100)
    m.add_box((w - M(60), M(35), d - M(50)), center=(0, leg_h + M(18), 0),
              mat="U_wood_oak")
    m.add_box((w - M(40), M(110), d - M(30)),
              center=(0, leg_h + M(35) + M(55), 0), mat="U_fabric_oat")
    for sx in (-1, 1):
        for sz in (-1, 1):
            m.add_box((M(50), leg_h, M(50)),
                      center=(sx * (w / 2 - M(45)), leg_h / 2,
                              sz * (d / 2 - M(40))), mat="U_wood_oak")
    return m


def build_shoe_bench(w=1200, d=380, h=450):
    return build_entry_bench(w, d, h)


# =====================================================================
# 桌
# =====================================================================
def build_desk(w=1200, d=600, h=750):
    """办公桌：台面 + 侧板腿 + 后挡板 + 抽屉柜。"""
    m = Mesh()
    w, d, h = M(w), M(d), M(h)
    m.add_box((w, M(40), d), center=(0, h - M(20), 0), mat="U_wood_oak")
    for sx in (-1, 1):
        m.add_box((M(50), h - M(40), d - M(100)),
                  center=(sx * (w / 2 - M(60)), (h - M(40)) / 2, 0),
                  mat="U_metal_black")
    # 后挡板
    m.add_box((w - M(140), M(120), M(25)), center=(0, h - M(100), d / 2 - M(60)),
              mat="U_wood_oak")
    # 侧抽屉柜
    m.add_box((M(360), M(340), d - M(140)),
              center=(-w / 2 + M(240), M(170) + M(20), 0), mat="U_wood_walnut")
    for i in range(2):
        y = M(80) + M(170) * i
        m.add_box((M(330), M(150), M(16)),
                  center=(-w / 2 + M(240), y, (d - M(140)) / 2 + M(8)),
                  mat="U_wood_oak")
    return m


def build_kids_desk(w=1000, d=600, h=700):
    """儿童学习桌：台面 + 侧板 + 挡板。"""
    m = Mesh()
    w, d, h = M(w), M(d), M(h)
    m.add_box((w, M(35), d), center=(0, h - M(18), 0), mat="U_wood_oak")
    for sx in (-1, 1):
        m.add_box((M(45), h - M(35), d - M(90)),
                  center=(sx * (w / 2 - M(55)), (h - M(35)) / 2, 0),
                  mat="U_wood_oak")
    m.add_box((w - M(140), M(120), M(25)), center=(0, h - M(90), d / 2 - M(50)),
              mat="U_wood_oak")
    return m


def build_training_table(w=1200, d=450, h=750):
    """培训桌：窄台面 + 两侧 A 形腿。"""
    m = Mesh()
    w, d, h = M(w), M(d), M(h)
    m.add_box((w, M(35), d), center=(0, h - M(18), 0), mat="U_wood_oak")
    for sx in (-1, 1):
        for sz in (-1, 1):
            m.add_box((M(40), h - M(35), M(40)),
                      center=(sx * (w / 2 - M(50)), (h - M(35)) / 2,
                              sz * (d / 2 - M(40))), mat="U_metal_black")
        m.add_box((M(35), M(35), d - M(80)),
                  center=(sx * (w / 2 - M(50)), M(160), 0), mat="U_metal_black")
    return m


def build_office_desk(w=1400, d=700, h=750):
    m = build_desk(w, d, h)
    return m


def build_standing_desk(w=1400, d=700, h=750):
    """升降桌：台面 + 两根升降柱 + 底脚。"""
    m = Mesh()
    w, d, h = M(w), M(d), M(h)
    m.add_box((w, M(45), d), center=(0, h - M(22), 0), mat="U_wood_oak")
    for sx in (-1, 1):
        m.add_box((M(80), h - M(140), M(80)),
                  center=(sx * (w / 2 - M(160)), (h - M(140)) / 2 + M(50), 0),
                  mat="U_metal_black")
        m.add_box((M(90), M(50), d - M(120)),
                  center=(sx * (w / 2 - M(160)), M(25), 0), mat="U_metal_black")
    m.add_box((M(60), M(60), M(60)), center=(0, h - M(120), -d / 2 + M(120)),
              mat="U_metal_black")
    return m


def build_tea_table(w=1800, d=800, h=700):
    """茶几/茶桌：台面 + 束腰 + 圈足。"""
    m = Mesh()
    w, d, h = M(w), M(d), M(h)
    m.add_box((w, M(45), d), center=(0, h - M(22), 0), mat="U_wood_walnut")
    m.add_box((w - M(200), M(90), d - M(160)),
              center=(0, h - M(90), 0), mat="U_wood_walnut")
    for sx in (-1, 1):
        for sz in (-1, 1):
            m.add_box((M(60), h - M(135), M(60)),
                      center=(sx * (w / 2 - M(130)), (h - M(135)) / 2,
                              sz * (d / 2 - M(110))), mat="U_wood_walnut")
    m.add_box((w - M(260), M(35), M(35)), center=(0, M(160), 0),
              mat="U_wood_walnut")
    return m


def build_bar_table(w=1400, d=500, h=1050):
    """吧台桌：高台面 + 侧板腿。"""
    m = Mesh()
    w, d, h = M(w), M(d), M(h)
    m.add_box((w, M(45), d), center=(0, h - M(22), 0), mat="U_wood_walnut")
    for sx in (-1, 1):
        m.add_box((M(60), h - M(45), d - M(90)),
                  center=(sx * (w / 2 - M(60)), (h - M(45)) / 2, 0),
                  mat="U_metal_black")
    m.add_box((w - M(160), M(35), M(35)), center=(0, M(200), 0),
              mat="U_metal_black")
    return m


def build_oval_coffee_table(w=1300, d=800, h=380):
    """椭圆茶几：椭圆台面（回转体压扁）+ 三腿。"""
    m = Mesh()
    w, d, h = M(w), M(d), M(h)
    prof = [(0, 0), (w / 2, 0), (w / 2, M(40)), (0, M(40))]
    m.add_revolve(prof, seg=40, mat="U_wood_oak")
    # 用网格压成椭圆更准：改用圆盘 + 缩放
    m2 = Mesh()
    m2.add_cylinder(w / 2, M(40), center=(0, 0, 0), seg=44, mat="U_wood_oak")
    m2.pos = [(p[0], p[1], p[2] * (d / w)) for p in m2.pos]
    m = m2
    for i in range(3):
        a = 2 * math.pi * i / 3
        m.add_box((M(50), h - M(40), M(50)),
                  center=(math.cos(a) * w * 0.32, (h - M(40)) / 2,
                          math.sin(a) * d * 0.32), mat="U_wood_walnut")
    return m


def build_side_table(w=500, d=500, h=550):
    """边几：圆台面 + 中心柱 + 圆底座。"""
    m = Mesh()
    w, d, h = M(w), M(d), M(h)
    m.add_cylinder(w / 2, M(35), center=(0, h - M(35), 0), seg=32,
                   mat="U_wood_walnut")
    m.add_cylinder(M(45), h - M(90), center=(0, M(45), 0), seg=16,
                   mat="U_metal_brass")
    m.add_cylinder(w * 0.34, M(45), center=(0, 0, 0), seg=28,
                   mat="U_metal_brass")
    return m


def build_nest_tables(w=600, d=600, h=450):
    """套叠几：大几 + 小几（错位叠放）。"""
    m = build_side_table(w, d, h)
    w2, d2, h2 = M(w) * 0.66, M(d) * 0.66, M(h) * 0.88
    m.add_cylinder(w2 / 2, M(30), center=(M(w) * 0.22, h2 - M(30), M(60)), seg=28,
                   mat="U_wood_oak")
    m.add_cylinder(M(35), h2 - M(60), center=(M(w) * 0.22, M(45), M(60)), seg=14,
                   mat="U_metal_brass")
    m.add_cylinder(w2 * 0.32, M(40), center=(M(w) * 0.22, M(10), M(60)), seg=24,
                   mat="U_metal_brass")
    return m


def build_round_meeting_table(w=1000, d=1000, h=750):
    """圆会议桌：圆台面 + 中央柱 + 十字底座。"""
    m = Mesh()
    w, d, h = M(w), M(d), M(h)
    m.add_cylinder(w / 2, M(45), center=(0, h - M(45), 0), seg=48,
                   mat="U_wood_oak")
    m.add_cylinder(M(70), h - M(100), center=(0, M(50), 0), seg=18,
                   mat="U_metal_black")
    m.add_box((w * 0.55, M(50), M(90)), center=(0, M(25), 0), mat="U_metal_black")
    m.add_box((M(90), M(50), w * 0.55), center=(0, M(25), 0), mat="U_metal_black")
    return m


def build_desk_bench4(w=2400, d=1400, h=750):
    """四人工位台：2×2 台面 + 中间走道隔板。"""
    m = Mesh()
    w, d, h = M(w), M(d), M(h)
    m.add_box((w, M(40), d), center=(0, h - M(20), 0), mat="U_wood_oak")
    for sx in (-1, 1):
        m.add_box((M(50), h - M(40), d - M(120)),
                  center=(sx * (w / 2 - M(60)), (h - M(40)) / 2, 0),
                  mat="U_metal_black")
    # 中间纵向隔板
    m.add_box((M(35), M(350), d - M(200)), center=(0, h - M(200), 0),
              mat="U_metal_black")
    return m


# =====================================================================
# 柜
# =====================================================================
def build_wardrobe2(w=1000, d=600, h=2200):
    """小衣柜：柜体 + 双开门 + 拉手 + 踢脚。"""
    m = Mesh()
    w, d, h = M(w), M(d), M(h)
    foot = M(80)
    m.add_box((w, h - foot, d), center=(0, foot + (h - foot) / 2, 0),
              mat="U_wood_walnut")
    for s in (-1, 1):
        m.add_box((w / 2 - M(16), h - foot - M(30), M(20)),
                  center=(s * w / 4, foot + (h - foot) / 2, d / 2 + M(10)),
                  mat="U_wood_oak")
        m.add_box((M(22), M(280), M(26)),
                  center=(s * M(30), foot + h * 0.48, d / 2 + M(28)),
                  mat="U_metal_brass")
    m.add_box((w + M(40), M(35), d + M(30)), center=(0, h - M(18), 0),
              mat="U_wood_walnut")
    return m


def build_wardrobe3(w=1500, d=600, h=2300):
    """三门衣柜。"""
    m = Mesh()
    w, d, h = M(w), M(d), M(h)
    foot = M(80)
    m.add_box((w, h - foot, d), center=(0, foot + (h - foot) / 2, 0),
              mat="U_wood_walnut")
    for i in range(3):
        x = -w / 2 + w / 3 * (i + 0.5)
        m.add_box((w / 3 - M(16), h - foot - M(30), M(20)),
                  center=(x, foot + (h - foot) / 2, d / 2 + M(10)),
                  mat="U_wood_oak")
        m.add_box((M(22), M(280), M(26)),
                  center=(x + w / 6 - M(30), foot + h * 0.48, d / 2 + M(28)),
                  mat="U_metal_brass")
    m.add_box((w + M(40), M(35), d + M(30)), center=(0, h - M(18), 0),
              mat="U_wood_walnut")
    return m


def build_shoe_cabinet(w=1200, d=350, h=1000):
    """鞋柜：柜体 + 翻门 + 通风孔条。"""
    m = Mesh()
    w, d, h = M(w), M(d), M(h)
    foot = M(90)
    m.add_box((w, h - foot, d), center=(0, foot + (h - foot) / 2, 0),
              mat="U_wood_walnut")
    for i in range(2):
        x = -w / 2 + w / 2 * (i + 0.5)
        m.add_box((w / 2 - M(20), h - foot - M(60), M(18)),
                  center=(x, foot + (h - foot) / 2, d / 2 + M(9)), mat="U_wood_oak")
        m.add_box((M(140), M(18), M(24)),
                  center=(x, foot + h * 0.62, d / 2 + M(26)), mat="U_metal_brass")
        # 通风孔（细条）
        for k in range(4):
            m.add_box((w / 2 - M(120), M(12), M(8)),
                      center=(x, foot + M(60) + M(45) * k, d / 2 + M(14)),
                      mat="U_metal_black")
    for sx in (-1, 1):
        for sz in (-1, 1):
            m.add_box((M(45), foot, M(45)),
                      center=(sx * (w / 2 - M(50)), foot / 2,
                              sz * (d / 2 - M(45))), mat="U_wood_walnut")
    return m


def build_cab_shoe(w=1200, d=380, h=2400):
    """高鞋柜。"""
    m = build_shoe_cabinet(w, d, h)
    return m


def build_toy_cabinet(w=900, d=350, h=800):
    """玩具柜：矮柜 + 双门 + 抽屉。"""
    m = Mesh()
    w, d, h = M(w), M(d), M(h)
    foot = M(80)
    m.add_box((w, h - foot, d), center=(0, foot + (h - foot) / 2, 0),
              mat="U_wood_walnut")
    m.add_box((w / 2 - M(20), (h - foot) * 0.62, M(18)),
              center=(-w / 4, foot + (h - foot) * 0.62, d / 2 + M(9)),
              mat="U_wood_oak")
    m.add_box((w / 2 - M(20), (h - foot) * 0.62, M(18)),
              center=(w / 4, foot + (h - foot) * 0.62, d / 2 + M(9)),
              mat="U_wood_oak")
    for i in range(2):
        x = -w / 4 + w / 2 * i
        m.add_box((w / 2 - M(20), (h - foot) * 0.26, M(18)),
                  center=(x, foot + (h - foot) * 0.18, d / 2 + M(9)),
                  mat="U_wood_oak")
        m.add_box((M(120), M(16), M(22)),
                  center=(x, foot + (h - foot) * 0.45, d / 2 + M(26)),
                  mat="U_metal_brass")
    return m


def build_chest(w=900, d=480, h=1100):
    """五斗柜：柜体 + 五层抽屉 + 拉手。"""
    m = Mesh()
    w, d, h = M(w), M(d), M(h)
    foot = M(100)
    m.add_box((w, h - foot, d), center=(0, foot + (h - foot) / 2, 0),
              mat="U_wood_walnut")
    n = 5
    for i in range(n):
        y = foot + (h - foot) / n * (i + 0.5)
        m.add_box((w - M(60), (h - foot) / n - M(16), M(18)),
                  center=(0, y, d / 2 + M(9)), mat="U_wood_oak")
        m.add_box((M(180), M(18), M(26)),
                  center=(0, y, d / 2 + M(28)), mat="U_metal_brass")
    for sx in (-1, 1):
        for sz in (-1, 1):
            m.add_box((M(55), foot, M(55)),
                      center=(sx * (w / 2 - M(60)), foot / 2,
                              sz * (d / 2 - M(50))), mat="U_wood_walnut")
    return m


def build_lockers(w=1200, d=450, h=1850):
    """更衣柜：柜体 + 三列门 + 通风格栅 + 编号牌。"""
    m = Mesh()
    w, d, h = M(w), M(d), M(h)
    foot = M(80)
    m.add_box((w, h - foot, d), center=(0, foot + (h - foot) / 2, 0),
              mat="U_metal_black")
    for i in range(3):
        x = -w / 2 + w / 3 * (i + 0.5)
        m.add_box((w / 3 - M(14), h - foot - M(20), M(18)),
                  center=(x, foot + (h - foot) / 2, d / 2 + M(9)),
                  mat="U_metal_black")
        # 通风格栅
        for k in range(5):
            m.add_box((w / 3 - M(90), M(12), M(6)),
                      center=(x, h - M(120) - M(30) * k, d / 2 + M(16)),
                      mat="U_metal_black")
        # 编号牌
        m.add_box((M(70), M(50), M(8)), center=(x, h - M(70), d / 2 + M(16)),
                  mat="U_metal_brass")
        # 门把
        m.add_box((M(24), M(90), M(24)),
                  center=(x + w / 6 - M(50), foot + h * 0.55, d / 2 + M(24)),
                  mat="U_metal_brass")
    return m


def build_bath_shelf(w=600, d=250, h=1600):
    """浴室置物架：立柱 + 三层隔板 + 挂钩。"""
    m = Mesh()
    w, d, h = M(w), M(d), M(h)
    for s in (-1, 1):
        m.add_box((M(28), h, M(28)),
                  center=(s * (w / 2 - M(20)), h / 2, -d / 2 + M(30)),
                  mat="U_metal_brass")
    for lvl, y in enumerate((M(300), M(800), M(1300))):
        m.add_box((w, M(25), d - M(40)), center=(0, y, 0), mat="U_wood_oak")
        # 栏
        m.add_box((w - M(60), M(20), M(20)), center=(0, y + M(60), d / 2 - M(50)),
                  mat="U_metal_brass")
    # 挂钩
    for i in range(3):
        x = -w / 4 + w / 4 * i
        m.add_cylinder(M(12), M(90), center=(x, h - M(60), d / 2 - M(40)), seg=8,
                       mat="U_metal_brass")
    return m


# =====================================================================
# 灯 / 电器 / 其他
# =====================================================================
def build_desk_lamp(w=250, d=250, h=450):
    """台灯：底座 + 灯杆 + 灯罩（回转体）+ 开关。"""
    m = Mesh()
    w, h = M(w), M(h)
    base_r = w * 0.48
    m.add_cylinder(base_r, M(30), center=(0, 0, 0), seg=28, mat="U_metal_black")
    m.add_cylinder(M(14), h - M(150), center=(0, M(30), 0), seg=12,
                   mat="U_metal_black")
    prof = [(0, h - M(120)), (w * 0.46, h - M(120)),
            (w * 0.40, h - M(40)), (0, h - M(40))]
    m.add_revolve(prof, seg=26, mat="U_metal_brass")
    m.add_cylinder(M(18), M(16), center=(base_r * 0.6, M(30), 0), seg=12,
                   mat="U_metal_brass")
    return m


def build_wall_tv(w=1450, d=60, h=830):
    """壁挂电视：面板 + 边框 + 壁挂架 + 屏幕。"""
    m = Mesh()
    w, d, h = M(w), M(d), M(h)
    bezel = M(24)
    m.add_box((w, h, d), center=(0, h / 2, 0), mat="U_metal_black")
    m.add_box((w - bezel * 2, h - bezel * 2, M(10)),
              center=(0, h / 2, d / 2 - M(4)), mat="U_glass_clear")
    # 壁挂架
    m.add_box((M(300), M(200), M(40)), center=(0, h / 2, -d / 2 - M(20)),
              mat="U_metal_black")
    return m


def build_proj_screen(w=2400, d=80, h=1500):
    """投影幕布：卷轴 + 幕布（细分网格，带自然垂坠弧度）。"""
    m = Mesh()
    w, d, h = M(w), M(d), M(h)
    # 卷轴
    m.add_cylinder(M(60), w, center=(0, h - M(60), 0), seg=20,
                   mat="U_metal_black")
    # 幕布（网格 + 轻微垂坠）
    nx, ny = 40, 18
    bw, bh = w - M(80), h - M(160)

    def fn(u, v):
        x = (u - 0.5) * bw
        y = h - M(120) - v * bh
        # 垂坠：中间略鼓
        bulge = math.sin(math.pi * u) * math.sin(math.pi * v) * M(18)
        z = -d / 2 + M(10) - bulge
        return (x, y, z)

    m.add_grid(bw, bh, nx, ny, fn, mat="U_fabric_cream", uvscale=bw / 1.5)
    return m


def build_day_bed(w=1900, d=800, h=750):
    """罗汉床：长座 + 靠背 + 扶手 + 垫。

    【朝向：靠背在 -Z，正面朝 +Z】见 build_bed 的朝向说明。
    """
    m = Mesh()
    w, d, h = M(w), M(d), M(h)
    base_h = M(140)
    seat_h = M(400)
    m.add_box((w, base_h, d - M(40)), center=(0, base_h / 2, 0),
              mat="U_wood_walnut")
    m.add_box((w - M(60), seat_h - base_h, d - M(140)),
              center=(0, base_h + (seat_h - base_h) / 2, M(20)),
              mat="U_fabric_oat")
    # 靠背
    m.add_box((w, h - base_h, M(110)),
              center=(0, base_h + (h - base_h) / 2, -d / 2 + M(55)),
              mat="U_wood_walnut")
    # 扶手
    for s in (-1, 1):
        m.add_box((M(90), h - base_h - M(120), d - M(40)),
                  center=(s * (w / 2 - M(45)),
                          base_h + (h - base_h - M(120)) / 2, 0),
                  mat="U_wood_walnut")
    # 靠垫
    for i in range(2):
        m.add_box((w * 0.36, M(280), M(90)),
                  center=(-w / 4 + w * 0.5 * i, seat_h + M(140), -d / 2 + M(140)),
                  mat="U_fabric_cream")
    return m


# =====================================================================
# 补齐缺口：梳妆台 / 书架
#
# 【为什么需要】
#   pick_resources_v5 v6 修掉语义错配后：
#     dresser  → metal_tool_chest（工具箱）被 EXCLUDE 排除
#     bookshelf → steel_frame_shelves_01（工业货架）被 EXCLUDE 排除
#   两者都回落几何生成，但【没有 builder】→ 构建期 no_builder → 缺件。
#   现成资源也救不了：实测形变 1.56~2.31（远超 1.35 阈值），
#   硬塞会造成用户明令禁止的"比例崩坏"。
#   所以补精确尺寸的参数化生成器 —— 形变恒为 1.0。
#
# 【尺寸真源】reference/catalog-sizes.json
#   dresser   = 1000 × 450 × 750
#   bookshelf =  900 × 350 × 2000
# =====================================================================


def build_dresser(w=1000, d=450, h=750):
    """梳妆台：台面 + 两侧抽屉柜 + 中央抽屉 + 圆镜 + 腿部空间。

    真实梳妆台的结构（不是三块板拼）：
      · 台面（略出挑，有 20mm 圆角）
      · 两侧抽屉柜（各 2 抽）+ 中央单抽
      · 底部横撑 + 4 只锥形木脚
      · 桌面上的椭圆镜子（镜框 + 镜面），带支撑柱
      · 一个小收纳托盘
    """
    m = Mesh()
    w, d, h = M(w), M(d), M(h)
    top_t = M(34)          # 台面板厚
    leg_h = M(140)         # 腿高
    body_h = h - top_t     # 柜体高
    body_d = d - M(60)     # 柜体比台面浅

    # ---- 台面（出挑 30mm）----
    m.add_box((w, top_t, d), center=(0, h - top_t / 2, 0), mat="U_wood_walnut")

    # ---- 柜体：左抽屉柜 ----
    side_w = w * 0.30
    for s in (-1, 1):
        cx = s * (w / 2 - side_w / 2 - M(10))
        m.add_box((side_w, body_h - leg_h, body_d),
                  center=(cx, leg_h + (body_h - leg_h) / 2, M(20)),
                  mat="U_wood_oak")
        # 两个抽屉面
        for k in range(2):
            yy = leg_h + (body_h - leg_h) * (0.25 + 0.5 * k)
            m.add_box((side_w - M(40), (body_h - leg_h) / 2 - M(20), M(16)),
                      center=(cx, yy, M(20) + body_d / 2 + M(8)),
                      mat="U_wood_walnut")
            # 拉手
            m.add_cylinder(M(9), M(120),
                           center=(cx, yy, M(20) + body_d / 2 + M(18)),
                           seg=14, mat="U_metal_brass", rot=(0, 90, 0))

    # ---- 中央抽屉（比两侧略高，作为视觉焦点）----
    mid_w = w - side_w * 2 - M(60)
    m.add_box((mid_w, body_h - leg_h, body_d),
              center=(0, leg_h + (body_h - leg_h) / 2, M(20)),
              mat="U_wood_oak")
    m.add_box((mid_w - M(30), body_h - leg_h - M(70), M(16)),
              center=(0, leg_h + (body_h - leg_h) / 2, M(20) + body_d / 2 + M(8)),
              mat="U_wood_walnut")
    m.add_cylinder(M(9), M(110), center=(0, leg_h + (body_h - leg_h) / 2,
                                         M(20) + body_d / 2 + M(18)),
                   seg=14, mat="U_metal_brass", rot=(0, 90, 0))

    # ---- 底部横撑 ----
    m.add_box((w - M(40), M(50), M(40)),
              center=(0, leg_h - M(25), M(20) + body_d / 2 - M(30)),
              mat="U_wood_walnut")

    # ---- 4 只锥形木脚 ----
    for sx in (-1, 1):
        for sz in (-1, 1):
            m.add_cylinder(M(24), leg_h,
                           center=(sx * (w / 2 - M(70)), 0, sz * (d / 2 - M(60))),
                           seg=12, mat="U_wood_walnut", radius_top=M(15))

    # ---- 镜子（椭圆镜片 + 框 + 立柱）----
    mir_r = M(210)
    mir_h = M(300)                       # 镜心离台面高
    m.add_cylinder(mir_r, M(14),
                   center=(0, h + mir_h - mir_r, -d / 2 + M(70)),
                   seg=40, mat="U_wood_walnut", rot=(90, 0, 0))
    m.add_cylinder(mir_r - M(18), M(16),
                   center=(0, h + mir_h - mir_r, -d / 2 + M(62)),
                   seg=40, mat="U_glass_clear", rot=(90, 0, 0))
    # 镜柱
    m.add_box((M(36), mir_h, M(28)),
              center=(0, h + mir_h / 2 - M(40), -d / 2 + M(70)),
              mat="U_wood_walnut")
    # 镜座
    m.add_box((M(160), M(26), M(90)),
              center=(0, h + M(13), -d / 2 + M(70)), mat="U_wood_walnut")

    # ---- 桌面小托盘（细节）----
    m.add_box((M(180), M(28), M(120)),
              center=(w * 0.30, h + M(14), d * 0.18), mat="U_wood_oak")
    return m


def build_bookshelf(w=900, d=350, h=2000):
    """落地书架：5 层开放格 + 侧板 + 背板 + 踢脚底座 + 顶部挡板。

    真实书架结构：
      · 侧板（通高）+ 背板（内凹，形成可见深度）
      · 层板（5 层 → 6 格），层板前端有圆角条
      · 中竖隔（把宽度分成 2 列，视觉更稳）
      · 底座踢脚（内缩，视觉上"浮起"）
      · 顶部加一条装饰挡板（比主体略宽出挑）
      · 少量书籍点缀（打破空荡感）
    """
    m = Mesh()
    w, d, h = M(w), M(d), M(h)
    foot = M(70)          # 踢脚高
    frame = M(36)         # 侧板厚
    back_t = M(14)        # 背板厚

    # ---- 背板（内凹）----
    m.add_box((w - frame * 2, h - foot, back_t),
              center=(0, foot + (h - foot) / 2, -d / 2 + back_t / 2),
              mat="U_wood_walnut")
    # ---- 侧板（通高）----
    for s in (-1, 1):
        m.add_box((frame, h - foot, d),
                  center=(s * (w / 2 - frame / 2), foot + (h - foot) / 2, 0),
                  mat="U_wood_walnut")
    # ---- 底板 ----
    m.add_box((w - frame * 2, M(30), d - M(20)),
              center=(0, foot + M(15), 0), mat="U_wood_oak")

    # ---- 层板（5 层）----
    inner_h = h - foot - M(34)
    n_shelf = 5
    for k in range(1, n_shelf + 1):
        yy = foot + inner_h * k / float(n_shelf)
        m.add_box((w - frame * 2, M(28), d - M(26)),
                  center=(0, yy, M(4)), mat="U_wood_oak")
        # 层板前沿圆角条
        m.add_box((w - frame * 2, M(14), M(14)),
                  center=(0, yy - M(10), d / 2 - M(13)), mat="U_wood_walnut")

    # ---- 中竖隔（贯通，但下半部分断开门洞感）----
    m.add_box((M(28), inner_h, d - M(26)),
              center=(0, foot + inner_h / 2, M(4)), mat="U_wood_walnut")

    # ---- 顶部挡板（出挑）----
    m.add_box((w + M(30), M(40), d + M(16)),
              center=(0, h - M(20), 0), mat="U_wood_walnut")

    # ---- 踢脚（内缩，视觉浮起）----
    m.add_box((w - M(70), foot, d - M(70)),
              center=(0, foot / 2, M(10)), mat="U_wood_walnut")

    # ---- 书籍点缀（几本竖放 + 横放）----
    bk_colors = ["U_wood_walnut", "U_fabric_oat", "U_wood_oak", "U_fabric_cream"]
    shelf_y = [foot + inner_h * k / float(n_shelf) + M(14)
               for k in range(n_shelf + 1)]
    for si, sy in enumerate(shelf_y[:-1]):
        if si % 2 == 1:
            continue
        x = -w * 0.28
        for b in range(4):
            bw = M(38) + M((b * 17) % 26)
            bh = M(210) + M((b * 37) % 70)
            m.add_box((bw, bh, d - M(90)),
                      center=(x + bw / 2, sy + bh / 2, M(6)),
                      mat=bk_colors[(si + b) % len(bk_colors)])
            x += bw + M(4)
    # 一本横放的书
    if len(shelf_y) >= 3:
        sy = shelf_y[1]
        m.add_box((M(240), M(36), d - M(90)),
                  center=(w * 0.26, sy + M(18), M(6)), mat="U_fabric_oat")
    return m


# =====================================================================
# 注册
# =====================================================================
EXTRA3 = {
    "armchair":       lambda p: build_armchair(p.get("w", 850), p.get("d", 850), p.get("h", 800)),
    "armDiningChair": lambda p: build_arm_dining_chair(p.get("w", 560), p.get("d", 560), p.get("h", 820)),
    "officeChair":    lambda p: build_office_chair(p.get("w", 600), p.get("d", 600), p.get("h", 1050)),
    "trainingChair":  lambda p: build_training_chair(p.get("w", 500), p.get("d", 500), p.get("h", 830)),
    "barStool":       lambda p: build_bar_stool(p.get("w", 400), p.get("d", 400), p.get("h", 750)),
    "rockingChair":   lambda p: build_rocking_chair(p.get("w", 700), p.get("d", 950), p.get("h", 900)),
    "entryBench":     lambda p: build_entry_bench(p.get("w", 900), p.get("d", 350), p.get("h", 450)),
    "shoeBench":      lambda p: build_shoe_bench(p.get("w", 1200), p.get("d", 380), p.get("h", 450)),

    "desk":           lambda p: build_desk(p.get("w", 1200), p.get("d", 600), p.get("h", 750)),
    "kidsDesk":       lambda p: build_kids_desk(p.get("w", 1000), p.get("d", 600), p.get("h", 700)),
    "trainingTable":  lambda p: build_training_table(p.get("w", 1200), p.get("d", 450), p.get("h", 750)),
    "officeDesk":     lambda p: build_office_desk(p.get("w", 1400), p.get("d", 700), p.get("h", 750)),
    "standingDesk":   lambda p: build_standing_desk(p.get("w", 1400), p.get("d", 700), p.get("h", 750)),
    "teaTable":       lambda p: build_tea_table(p.get("w", 1800), p.get("d", 800), p.get("h", 700)),
    "barTable":       lambda p: build_bar_table(p.get("w", 1400), p.get("d", 500), p.get("h", 1050)),
    "ovalCoffee":     lambda p: build_oval_coffee_table(p.get("w", 1300), p.get("d", 800), p.get("h", 380)),
    "sideTable":      lambda p: build_side_table(p.get("w", 500), p.get("d", 500), p.get("h", 550)),
    "nestTables":     lambda p: build_nest_tables(p.get("w", 600), p.get("d", 600), p.get("h", 450)),
    "roundMeeting":   lambda p: build_round_meeting_table(p.get("w", 1000), p.get("d", 1000), p.get("h", 750)),
    "deskBench4":     lambda p: build_desk_bench4(p.get("w", 2400), p.get("d", 1400), p.get("h", 750)),

    "wardrobe2":      lambda p: build_wardrobe2(p.get("w", 1000), p.get("d", 600), p.get("h", 2200)),
    "wardrobe3":      lambda p: build_wardrobe3(p.get("w", 1500), p.get("d", 600), p.get("h", 2300)),
    "shoeCabinet":    lambda p: build_shoe_cabinet(p.get("w", 1200), p.get("d", 350), p.get("h", 1000)),
    "cabShoe":        lambda p: build_cab_shoe(p.get("w", 1200), p.get("d", 380), p.get("h", 2400)),
    "toyCabinet":     lambda p: build_toy_cabinet(p.get("w", 900), p.get("d", 350), p.get("h", 800)),
    "chest":          lambda p: build_chest(p.get("w", 900), p.get("d", 480), p.get("h", 1100)),
    # 【v6 补缺】语义错配修复后回落几何、但原先无 builder 的两项
    "dresser":        lambda p: build_dresser(p.get("w", 1000), p.get("d", 450), p.get("h", 750)),
    "bookshelf":      lambda p: build_bookshelf(p.get("w", 900), p.get("d", 350), p.get("h", 2000)),
    "lockers":        lambda p: build_lockers(p.get("w", 1200), p.get("d", 450), p.get("h", 1850)),
    "bathShelf":      lambda p: build_bath_shelf(p.get("w", 600), p.get("d", 250), p.get("h", 1600)),

    "deskLamp":       lambda p: build_desk_lamp(p.get("w", 250), p.get("d", 250), p.get("h", 450)),
    "wallTV":         lambda p: build_wall_tv(p.get("w", 1450), p.get("d", 60), p.get("h", 830)),
    "projScreen":     lambda p: build_proj_screen(p.get("w", 2400), p.get("d", 80), p.get("h", 1500)),
    "dayBed":         lambda p: build_day_bed(p.get("w", 1900), p.get("d", 800), p.get("h", 750)),
}

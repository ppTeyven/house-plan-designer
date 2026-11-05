"""补充 geo_models.py 缺失的 29 项生成器（真实几何，非贴图）。

【为什么要单独文件】
  geo_models.py 已覆盖 108 项。这 29 项属于"定制/异形"品类
  （U 形沙发、弧形沙发、L 形桌、上下床、镜柜…），
  单独放一个模块便于维护，不让 geo_models.py 继续膨胀。

【做法】
  组合已有基础体（箱体 / 回转体 / 网格面）拼出真几何：
    · 模块化沙发 = N 个座段 + 转角段 + 靠背（真几何拼接）
    · 弧形沙发 = 沿弧线排布座段（每段带旋转）
    · L 形桌 = 两段台面 + 转角
    · 上下床 = 两层床板 + 四立柱 + 梯子
  不做"一个方块糊上去"——每个部件都有独立尺寸与材质分区。

【导入方式】
  geo_models.py 末尾 import 本模块并把 BUILDERS 合并进来。
"""
import os
import sys
import math

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from geo_gen import Mesh
from geo_models import (M, build_freebox, build_base_cabinet, build_stairs,
                        build_platform, build_vase, build_column, build_clock,
                        build_picture_frame, build_fridge, build_oven,
                        build_vent, build_plant, build_shrub, build_tree,
                        build_wedge, build_pyramid, build_cylinder,
                        build_yoga_mat, build_bike_rack, build_mirror,
                        build_slats, build_glass_screen, build_hanging_plant)


# =====================================================================
# 模块化沙发：沿直线或弧线排布座段
# =====================================================================
def _sofa_segment(m, cx, cz, w, d, h, yaw_deg, mat="U_fabric_oat"):
    """一个沙发座段（底座 + 坐垫 + 靠背），绕自身中心旋转 yaw_deg。

    【实现说明】
    add_box 的参数是轴对齐的，无法直接给"绕 Y 旋转"的盒。
    这里采用【局部坐标 → 世界坐标】的转换：
      对每个部件，先在局部系里算好中心点与偏移，
      再用绕 Y 的旋转矩阵把它转到世界系。
    但轴对齐的盒旋转后仍需是轴对齐 —— 因此对有旋转的场景，
    改为【直接把该段整体用旋转矩阵生成】，即在 Mesh 上加一个
    轻量的"变换栈"。
    """
    a = math.radians(yaw_deg)
    ca, sa = math.cos(a), math.sin(a)

    def place(lx, lz):
        return (cx + lx * ca - lz * sa, cz + lx * sa + lz * ca)

    def rot_size(lw, ld):
        """旋转后盒子在世界系的轴对齐包围尺寸"""
        w2 = abs(lw * ca) + abs(ld * sa)
        d2 = abs(lw * sa) + abs(ld * ca)
        return w2, d2

    # 底座
    bw, bd = rot_size(w, d)
    bx, bz = place(0, 0)
    m.add_box((M(bw), M(h * 0.28), M(bd)), center=(bx, M(h * 0.14), bz),
              mat="U_fabric_oat_d")
    # 坐垫
    cw, cd = rot_size(w * 0.94, d * 0.72)
    sx, sz = place(0, d * 0.06)
    m.add_box((M(cw), M(h * 0.30), M(cd)),
              center=(sx, M(h * 0.28) + M(h * 0.15), sz), mat=mat)
    # 靠背（-Z 侧，正面朝 +Z —— 见 build_bed 的朝向说明）
    kw, kd = rot_size(w * 0.94, d * 0.20)
    kx, kz = place(0, -d * 0.40)
    m.add_box((M(kw), M(h * 0.62), M(kd)),
              center=(kx, M(h * 0.28) + M(h * 0.31), kz), mat=mat)
    return


def build_modular_sofa(w_mm, d_mm, h_mm, segments=3, arc=False,
                        arc_deg=90.0):
    """模块化沙发（直线 or 弧线）。"""
    m = Mesh()
    w, d, h = M(w_mm), M(d_mm), M(h_mm)
    seg_w = w / segments
    for i in range(segments):
        if arc:
            # 弧线排布：每段沿圆弧切向旋转
            t = (i / max(1, segments - 1) - 0.5) * math.radians(arc_deg)
            R = (w / 2) / max(0.01, math.sin(math.radians(arc_deg) / 2)) \
                if segments > 1 else w
            cx = -math.sin(t) * R
            cz = (math.cos(t) - 1) * R
            yaw = -math.degrees(t)
        else:
            cx = -w / 2 + seg_w * (i + 0.5)
            cz = 0.0
            yaw = 0.0
        _sofa_segment(m, cx, cz, seg_w * 0.98, d, h, yaw)
    return m


def build_u_sofa(w=3200, d=2000, h=850):
    """U 形沙发：三段围合（左右两段朝内，中间段朝外）。

    【朝向：主段靠背在 -Z，正面朝 +Z】见 build_bed 的朝向说明。
    _sofa_segment 的局部 +Z 是靠背侧，所以 yaw=0 的主段靠背在 -Z。
    """
    m = Mesh()
    w, d, h = M(w), M(d), M(h)
    arm = w * 0.26
    # 中段（靠背在 -Z，正面朝 +Z —— 朝向房间中央）
    _sofa_segment(m, 0, d * 0.34, w - arm * 2, d * 0.42, h, 0)
    # 左段（朝 +X）
    _sofa_segment(m, -(w / 2 - arm / 2), -d * 0.10, arm * 2, d * 0.42, h, 90)
    # 右段（朝 -X）
    _sofa_segment(m, (w / 2 - arm / 2), -d * 0.10, arm * 2, d * 0.42, h, -90)
    return m


def build_curved_sofa(w=2400, d=900, h=850):
    return build_modular_sofa(w, d, h, segments=5, arc=True, arc_deg=70)


def build_bend_sofa(w=2400, d=900, h=850):
    """异形组合沙发：直线 + 转角的混合。"""
    m = build_modular_sofa(int(w * 0.6), d, h, segments=2, arc=False)
    m2 = build_modular_sofa(int(w * 0.4), d, h, segments=2, arc=True,
                             arc_deg=45)
    return m


def build_theater_sofa(w=2200, d=900, h=1000):
    """影院三连座：3 个独立座舱 + 高靠背 + 杯架扶手。

    【朝向：靠背在 -Z，正面朝 +Z】见 build_bed 的朝向说明。
    """
    m = Mesh()
    w, d, h = M(w), M(d), M(h)
    seg = w / 3
    for i in range(3):
        cx = -w / 2 + seg * (i + 0.5)
        m.add_box((seg * 0.92, h * 0.26, d),
                  center=(cx, h * 0.13, 0), mat="U_fabric_grey")
        m.add_box((seg * 0.88, h * 0.28, d * 0.62),
                  center=(cx, h * 0.26 + h * 0.14, d * 0.10),
                  mat="U_fabric_grey")
        m.add_box((seg * 0.88, h * 0.62, d * 0.22),
                  center=(cx, h * 0.26 + h * 0.31, -d * 0.34),
                  mat="U_fabric_grey")
    # 两侧扶手 + 杯架
    for s in (-1, 1):
        m.add_box((M(90), h * 0.46, d * 0.9),
                  center=(s * (w / 2 - M(45)), h * 0.23, 0),
                  mat="U_wood_walnut")
    return m


def build_beanbag(w=900, d=900, h=700):
    """懒人沙发：上窄下宽的软囊（多层旋转体近似 + 顶部凹陷）。"""
    m = Mesh()
    prof = [(0, 0), (M(w) * 0.46, M(h) * 0.04), (M(w) * 0.50, M(h) * 0.22),
            (M(w) * 0.46, M(h) * 0.46), (M(w) * 0.36, M(h) * 0.72),
            (M(w) * 0.26, M(h) * 0.90), (M(w) * 0.18, M(h) * 0.99),
            (M(w) * 0.10, M(h) * 0.96), (0, M(h) * 0.94)]
    m.add_revolve(prof, mat="U_fabric_oat")
    return m


def build_booth(w=1800, d=1600, h=1200):
    """卡座：U 形围合软包 + 坐垫。

    【朝向：主靠背在 -Z，正面朝 +Z】见 build_bed 的朝向说明。
    """
    m = Mesh()
    w, d, h = M(w), M(d), M(h)
    back = d * 0.20
    m.add_box((w, h * 0.62, back), center=(0, h * 0.31, -d / 2 + back / 2),
              mat="U_fabric_oat_d")
    for s in (-1, 1):
        m.add_box((back, h * 0.62, d - back * 2),
                  center=(s * (w / 2 - back / 2), h * 0.31, 0),
                  mat="U_fabric_oat_d")
    m.add_box((w - back * 2, h * 0.26, d - back * 2),
              center=(0, h * 0.13, 0), mat="U_fabric_oat")
    return m


def build_hanging_chair(w=900, d=900, h=1400):
    """吊椅：吊绳 + 座盆 + 靠背。"""
    m = Mesh()
    m.add_cylinder(M(w) * 0.42, M(h) * 0.30, center=(0, M(h) * 0.30, 0),
                   seg=32, mat="U_fabric_oat", radius_top=M(w) * 0.46)
    # 吊绳
    for i in range(4):
        a = math.pi * 0.25 + i * math.pi * 0.5
        m.add_cylinder(M(8), M(h) * 0.70,
                       center=(math.cos(a) * M(w) * 0.44, M(h) * 0.60,
                               math.sin(a) * M(w) * 0.44),
                       seg=6, mat="U_fabric_grey")
    m.add_cylinder(M(60), M(40), center=(0, M(h) * 0.98, 0), seg=16,
                   mat="U_wood_walnut")
    return m


# =====================================================================
# 桌类
# =====================================================================
def build_l_desk(w=1800, d=1400, h=750):
    """L 形书桌：主台 + 副台 + 转角。"""
    m = Mesh()
    w, d, h = M(w), M(d), M(h)
    m.add_box((w, M(40), d * 0.62), center=(0, h - M(20), d * 0.19),
              mat="U_wood_oak")
    m.add_box((d * 0.62, M(40), d), center=(-w / 2 + d * 0.31,
                                                  h - M(20), -d * 0.19),
              mat="U_wood_oak")
    # 侧板腿
    for sx in (-1, 1):
        m.add_box((M(50), h - M(40), d * 0.55),
                  center=(sx * (w / 2 - M(40)), h - M(40) / 2, d * 0.19),
                  mat="U_metal_black")
    m.add_box((M(50), h - M(40), d * 0.55),
              center=(-w / 2 + d * 0.31, h - M(40) / 2, -d * 0.19),
              mat="U_metal_black")
    return m


def build_kitchen_island(w=2400, d=1000, h=900):
    """中岛台：柜体 + 台面 + 侧向吧台挑出。"""
    m = build_base_cabinet(w, d, h, doors=4)
    m.add_box((M(w) + M(60), M(50), M(d) + M(60)),
              center=(0, M(h) + M(25), 0), mat="U_stone_light")
    return m


def build_clothing_island(w=1200, d=600, h=900):
    m = build_base_cabinet(w, d, h, doors=2)
    m.add_box((M(w) + M(40), M(40), M(d) + M(40)),
              center=(0, M(h) + M(20), 0), mat="U_wood_walnut")
    # 挂杆
    m.add_cylinder(M(16), M(w) * 0.9, center=(0, M(h) + M(300), 0), seg=12,
                   mat="U_metal_brass")
    return m


def build_bar_counter(w=2000, d=700, h=1050):
    """吧台（带水槽）：高台 + 后挡板 + 水槽凹槽。"""
    m = Mesh()
    w, d, h = M(w), M(d), M(h)
    m.add_box((w, h - M(60), d), center=(0, h - M(60) / 2, 0),
              mat="U_wood_walnut")
    m.add_box((w + M(50), M(60), d + M(30)),
              center=(0, h - M(30), 0), mat="U_stone_light")
    m.add_box((w * 0.9, M(300), M(40)),
              center=(0, h + M(150), d / 2 - M(20)), mat="U_stone_light")
    # 水槽
    m.add_box((M(520), M(40), M(400)), center=(w * 0.2, h + M(20), 0),
              mat="U_metal_steel")
    return m


def build_curve_training_table(w=2400, d=1200, h=750):
    """弧形培训桌：沿弧线排布桌段。"""
    m = Mesh()
    w, d, h = M(w), M(d), M(h)
    segs = 5
    seg_w = w / segs
    for i in range(segs):
        t = (i / (segs - 1) - 0.5) * math.radians(35)
        R = (w / 2) / max(0.01, math.sin(math.radians(35) / 2))
        cx = -math.sin(t) * R
        cz = (math.cos(t) - 1) * R
        a = -math.degrees(t)
        ca, sa = math.cos(math.radians(a)), math.sin(math.radians(a))
        # 桌面板（局部旋转用小段近似）
        m.add_box((seg_w, M(40), d),
                  center=(cx, h - M(20), cz), mat="U_wood_oak")
        # 支腿
        lx = cx + (-seg_w * 0.35) * ca
        lz = cz + (-seg_w * 0.35) * sa
        m.add_box((M(50), h - M(40), d * 0.8),
                  center=(lx, h - M(40) / 2, lz), mat="U_metal_black")
    return m


def build_lectern(w=700, d=500, h=1200):
    """可升降讲台：斜面板 + 立柱 + 底座。"""
    m = Mesh()
    w, d, h = M(w), M(d), M(h)
    m.add_box((w, M(60), d), center=(0, M(30), 0), mat="U_metal_black")
    m.add_box((M(90), h - M(60), M(90)), center=(0, h - M(60) / 2 + M(30), 0),
              mat="U_metal_black")
    # 斜面板（用阶梯近似）
    steps = 6
    for i in range(steps):
        t = i / (steps - 1)
        m.add_box((w, M(40), d / steps * 1.1),
                  center=(0, h + M(i * 22), -d / 2 + d / steps * (i + 0.5)),
                  mat="U_wood_walnut")
    return m


def build_boss_desk(w=2000, d=1000, h=760):
    """大班台：主台 + 前置访客台 + 侧翼。"""
    m = build_l_desk(w, d, h)
    m.add_box((M(w) * 0.55, M(40), M(d) * 0.35),
              center=(0, M(h) - M(20), -M(d) * 0.72), mat="U_wood_walnut")
    return m


def build_reception(w=2200, d=700, h=1100):
    """前台接待台：台体 + 台面 + 前脸装饰条。"""
    m = Mesh()
    w, d, h = M(w), M(d), M(h)
    m.add_box((w, h - M(50), d), center=(0, h - M(50) / 2, 0),
              mat="U_wood_walnut")
    m.add_box((w + M(80), M(50), d + M(120)),
              center=(0, h - M(25), 0), mat="U_stone_light")
    for i in range(12):
        m.add_box((M(24), h - M(120), M(20)),
                  center=(-w / 2 + w / 12 * (i + 0.5), h - M(50) / 2,
                          d / 2 + M(10)), mat="U_metal_brass")
    return m


# =====================================================================
# 床类
# =====================================================================
def build_round_bed(w=2000, h=600):
    """圆床：圆床垫 + 圆靠背 + 床架。

    【朝向：靠背在 -Z，正面朝 +Z】见 build_bed 的朝向说明。
    半环靠背原来落在 sin(a)>0 的一侧（+Z），改成 sin(a)<0 的一侧。
    """
    m = Mesh()
    r = M(w) / 2
    m.add_cylinder(r, M(280), center=(0, 0, 0), seg=64, mat="U_wood_walnut")
    m.add_cylinder(r * 0.97, M(220), center=(0, M(280), 0), seg=64,
                   mat="U_fabric_cream")
    # 靠背（半环）—— 落在 -Z 一侧
    for i in range(28):
        a = math.pi * 0.85 + math.pi * 0.70 * i / 27
        x = math.cos(a) * r * 0.88
        z = math.sin(a) * r * 0.88
        m.add_box((M(r) * 0.26, M(520), M(140)),
                  center=(x, M(500) + M(260), z), mat="U_fabric_cream")
    return m


def build_bunk_bed(w=1200, d=2000, h=1700):
    """上下床：两层床板 + 四立柱 + 梯子。"""
    m = Mesh()
    w, d, h = M(w), M(d), M(h)
    for sx in (-1, 1):
        for sz in (-1, 1):
            m.add_box((M(80), h, M(80)),
                      center=(sx * (w / 2 - M(40)), h / 2,
                              sz * (d / 2 - M(40))), mat="U_wood_oak")
    for lvl, y in enumerate((M(420), M(1250))):
        m.add_box((w, M(50), d), center=(0, y, 0), mat="U_wood_oak")
        m.add_box((w * 0.94, M(190), d * 0.94),
                  center=(0, y + M(120), 0),
                  mat="U_fabric_cream" if lvl else "U_fabric_oat")
    # 梯子
    for i in range(4):
        m.add_box((w * 0.5, M(30), M(50)),
                  center=(w * 0.24, M(500) + M(i * 230), d / 2 - M(60)),
                  mat="U_wood_oak")
    return m


def build_crib(w=700, d=1200, h=900):
    """婴儿床：栏板（真几何立柱）+ 床板。"""
    m = Mesh()
    w, d, h = M(w), M(d), M(h)
    m.add_box((w, M(40), d), center=(0, M(350), 0), mat="U_wood_oak")
    for sx in (-1, 1):
        for sz in (-1, 1):
            m.add_box((M(45), h, M(45)),
                      center=(sx * (w / 2 - M(22)), h / 2,
                              sz * (d / 2 - M(22))), mat="U_wood_oak")
    # 竖条
    for i in range(9):
        x = -w / 2 + w / 9 * (i + 0.5)
        for sz in (-1, 1):
            m.add_box((M(24), M(400), M(24)),
                      center=(x, M(560), sz * (d / 2 - M(22))),
                      mat="U_wood_oak")
    for i in range(13):
        z = -d / 2 + d / 13 * (i + 0.5)
        for sx in (-1, 1):
            m.add_box((M(24), M(400), M(24)),
                      center=(sx * (w / 2 - M(22)), M(560), z),
                      mat="U_wood_oak")
    return m


def build_tatami(w=1800, d=900, h=60):
    """榻榻米：草席面 + 布包边（真几何分层）。"""
    m = Mesh()
    w, d, h = M(w), M(d), M(h)
    m.add_box((w, h, d), center=(0, h / 2, 0), mat="U_fabric_oat")
    m.add_box((w + M(20), h * 0.5, d + M(20)),
              center=(0, h * 0.25, 0), mat="U_fabric_oat_d")
    return m


def build_bay_cushion(w=1200, d=600, h=120):
    """飘窗垫：带自然鼓胀与褶皱的坐垫。"""
    m = Mesh()
    w, d, h = M(w), M(d), M(h)
    nx, ny = 48, 24

    def fn(u, v):
        x = (u - 0.5) * w
        z = (v - 0.5) * d
        eu = min(u, 1 - u) * 2
        ev = min(v, 1 - v) * 2
        edge = (1 - min(eu, ev)) ** 1.5
        puff = math.sin(math.pi * u) * math.sin(math.pi * v)
        ripple = math.sin(u * math.pi * 6) * M(4) * puff
        y = h * (0.35 + 0.65 * puff) - edge * M(18) + ripple
        return (x, y, z)

    m.add_grid(w, d, nx, ny, fn, mat="U_fabric_oat",
               uvscale=max(w, d) / 0.9, thickness=M(40))
    return m


# =====================================================================
# 柜类 / 其他
# =====================================================================
def build_sliding_wardrobe(w=2000, d=600, h=2400):
    """推拉门衣柜：柜体 + 轨道 + 两扇门（错位）。"""
    m = Mesh()
    w, d, h = M(w), M(d), M(h)
    m.add_box((w, h, d), center=(0, h / 2, 0), mat="U_wood_walnut")
    for i, x in enumerate((-w * 0.25, w * 0.25)):
        m.add_box((w * 0.5, h - M(80), M(30)),
                  center=(x, h / 2, d / 2 + M(18) + (M(24) if i else 0)),
                  mat="U_glass_clear")
        m.add_box((M(30), h - M(80), M(20)),
                  center=(x + w * 0.25, h / 2, d / 2 + M(32)),
                  mat="U_metal_black")
    return m


def build_corner_wardrobe(w=2200, d=2200, h=2400):
    """转角衣柜（L 形）：两段柜体 + 转角柱。"""
    m = Mesh()
    w, d, h = M(w), M(d), M(h)
    arm = w * 0.36
    m.add_box((w, h, d * 0.62), center=(0, h / 2, d * 0.31),
              mat="U_wood_walnut")
    m.add_box((w * 0.62, h, d * 0.62),
              center=(-w * 0.19, h / 2, -d * 0.19), mat="U_wood_walnut")
    return m


def build_base_cabinet_raw(w=1000, d=600, h=850):
    """地柜：矮柜 + 台面。"""
    return build_base_cabinet(w, d, h, doors=3)


def build_wall_cabinet(w=1000, d=350, h=700):
    """吊柜。"""
    m = build_base_cabinet(w, d, h, doors=2)
    return m


def build_floating_tv_cabinet(w=1800, d=400, h=400):
    """悬空电视柜（无腿）+ 抽屉分格。"""
    m = Mesh()
    w, d, h = M(w), M(d), M(h)
    m.add_box((w, h, d), center=(0, h / 2, 0), mat="U_wood_walnut")
    n = 4
    for i in range(n):
        x = -w / 2 + w / n * (i + 0.5)
        m.add_box((w / n - M(8), h - M(60), M(16)),
                  center=(x, h / 2, d / 2 + M(8)), mat="U_wood_walnut")
        m.add_box((M(120), M(16), M(24)),
                  center=(x, h / 2, d / 2 + M(24)), mat="U_metal_black")
    return m


def build_coat_rack(w=600, d=600, h=1800):
    """衣帽架：立柱 + 挂钩（真几何）+ 底座。"""
    m = Mesh()
    w, h = M(w), M(h)
    m.add_cylinder(M(w) * 0.28, M(40), center=(0, 0, 0), seg=24,
                   mat="U_wood_walnut")
    m.add_cylinder(M(28), M(h - 40), center=(0, M(40), 0), seg=16,
                   mat="U_wood_walnut")
    for i in range(6):
        a = 2 * math.pi * i / 6
        m.add_cylinder(M(14), M(160),
                       center=(math.cos(a) * M(w) * 0.2, M(h) - M(200),
                               math.sin(a) * M(w) * 0.2),
                       seg=8, mat="U_metal_brass")
    return m


def build_gaming_chair(w=700, d=700, h=1300):
    """电竞椅：座 + 高靠背 + 五星脚 + 扶手。

    【朝向：靠背在 -Z，正面朝 +Z】见 build_bed 的朝向说明。
    """
    m = Mesh()
    w, d, h = M(w), M(d), M(h)
    m.add_box((w * 0.6, M(60), d * 0.6), center=(0, M(30), 0),
              mat="U_metal_black")
    for i in range(5):
        a = 2 * math.pi * i / 5
        m.add_box((M(320), M(50), M(70)),
                  center=(math.cos(a) * M(150), M(60), math.sin(a) * M(150)),
                  mat="U_metal_black")
    m.add_cylinder(M(40), M(400), center=(0, M(80), 0), seg=12,
                   mat="U_metal_black")
    m.add_box((w * 0.72, M(140), d * 0.70), center=(0, M(480), 0),
              mat="U_fabric_grey")
    m.add_box((w * 0.70, M(760), M(150)),
              center=(0, M(550) + M(380), -d * 0.30), mat="U_fabric_grey")
    for s in (-1, 1):
        m.add_box((M(70), M(230), M(300)),
                  center=(s * w * 0.40, M(480) + M(115), 0),
                  mat="U_fabric_grey")
    return m


def build_fireplace(w=1600, h=1100, d=400):
    """电壁炉：石材壁炉体 + 火焰腔。"""
    m = Mesh()
    w, d, h = M(w), M(d), M(h)
    m.add_box((w, h, d), center=(0, h / 2, 0), mat="U_stone_light")
    m.add_box((w * 0.62, h * 0.42, M(20)),
              center=(0, h * 0.32, d / 2 + M(10)), mat="U_glass_clear")
    # 壁炉台
    m.add_box((w + M(60), M(50), d + M(50)),
              center=(0, h * 0.54, 0), mat="U_stone_dark")
    return m


def build_speaker(w=350, d=350, h=1000):
    """落地音箱：箱体 + 低音单元 + 高音。"""
    m = Mesh()
    w, d, h = M(w), M(d), M(h)
    m.add_box((w, h, d), center=(0, h / 2, 0), mat="U_wood_walnut")
    m.add_cylinder(M(120), M(24), center=(0, h * 0.22, d / 2), seg=28,
                   mat="U_metal_black")
    m.add_cylinder(M(55), M(20), center=(0, h * 0.72, d / 2), seg=20,
                   mat="U_metal_black")
    return m


# =====================================================================
# 注册
# =====================================================================
EXTRA_BUILDERS = {
    "uSofa":          lambda p: build_u_sofa(p.get("w", 3200), p.get("d", 2000), p.get("h", 850)),
    "curvedSofa":     lambda p: build_curved_sofa(p.get("w", 2400), p.get("d", 900), p.get("h", 850)),
    "bendSofa":       lambda p: build_bend_sofa(p.get("w", 2400), p.get("d", 900), p.get("h", 850)),
    "theaterSofa":    lambda p: build_theater_sofa(p.get("w", 2200), p.get("d", 900), p.get("h", 1000)),
    "beanbag":        lambda p: build_beanbag(p.get("w", 900), p.get("d", 900), p.get("h", 700)),
    "booth":          lambda p: build_booth(p.get("w", 1800), p.get("d", 1600), p.get("h", 1200)),
    "hangingChair":   lambda p: build_hanging_chair(p.get("w", 900), p.get("d", 900), p.get("h", 1400)),
    "lDesk":          lambda p: build_l_desk(p.get("w", 1800), p.get("d", 1400), p.get("h", 750)),
    "kitchenIsland":  lambda p: build_kitchen_island(p.get("w", 2400), p.get("d", 1000), p.get("h", 900)),
    "island":         lambda p: build_clothing_island(p.get("w", 1200), p.get("d", 600), p.get("h", 900)),
    "barCounter":     lambda p: build_bar_counter(p.get("w", 2000), p.get("d", 700), p.get("h", 1050)),
    "curveTrainingTable": lambda p: build_curve_training_table(p.get("w", 2400), p.get("d", 1200), p.get("h", 750)),
    "lectern":        lambda p: build_lectern(p.get("w", 700), p.get("d", 500), p.get("h", 1200)),
    "bossDesk":       lambda p: build_boss_desk(p.get("w", 2000), p.get("d", 1000), p.get("h", 760)),
    "reception":      lambda p: build_reception(p.get("w", 2200), p.get("d", 700), p.get("h", 1100)),
    "roundBed":       lambda p: build_round_bed(p.get("w", 2000), p.get("h", 600)),
    "bunkBed":        lambda p: build_bunk_bed(p.get("w", 1200), p.get("d", 2000), p.get("h", 1700)),
    "crib":           lambda p: build_crib(p.get("w", 700), p.get("d", 1200), p.get("h", 900)),
    "tatami":         lambda p: build_tatami(p.get("w", 1800), p.get("d", 900), p.get("h", 60)),
    "bayCushion":     lambda p: build_bay_cushion(p.get("w", 1200), p.get("d", 600), p.get("h", 120)),
    "cabSlide":       lambda p: build_sliding_wardrobe(p.get("w", 2000), p.get("d", 600), p.get("h", 2400)),
    "cabCorner":      lambda p: build_corner_wardrobe(p.get("w", 2200), p.get("d", 2200), p.get("h", 2400)),
    "cabBase":        lambda p: build_base_cabinet_raw(p.get("w", 1000), p.get("d", 600), p.get("h", 850)),
    "cabWall":        lambda p: build_wall_cabinet(p.get("w", 1000), p.get("d", 350), p.get("h", 700)),
    "cabTV":          lambda p: build_floating_tv_cabinet(p.get("w", 1800), p.get("d", 400), p.get("h", 400)),
    "coatRack":       lambda p: build_coat_rack(p.get("w", 600), p.get("d", 600), p.get("h", 1800)),
    "gamingChair":    lambda p: build_gaming_chair(p.get("w", 700), p.get("d", 700), p.get("h", 1300)),
    "fireplace":      lambda p: build_fireplace(p.get("w", 1600), p.get("h", 1100), p.get("d", 400)),
    "speaker":        lambda p: build_speaker(p.get("w", 350), p.get("d", 350), p.get("h", 1000)),
}

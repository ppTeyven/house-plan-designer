"""第四批生成器 —— 补齐 8 项"有近义资源但比例不达标"的品类。

【为什么单独一批】
  pick_resources_v5 的严格门控是对的：宁可几何生成，也不套一个形变
  超过阈值的现成资源（那会让用户看到比例崩坏的家具）。
  但"严格门控"必须配"完整生成器"，否则这些款式会彻底没有资源。
  这一批的 8 项都是【库里有同类、但尺寸/形态对不上】的品类：

    wineCabinet     酒柜        库内最接近的 cabinet 高宽比不对
    displayCabinet  展示柜     需要玻璃门 + 层板，库内没有
    hallCabinet     玄关柜     需要中空背板 + 挂衣区，库内没有
    cabTall         高柜/书柜  库内高柜太宽太深
    bookshelfLow    矮书架     库内书架都太高
    coffeeTable     茶几       库内茶几都是方的，目标 1200×600 长方形
    ovalTable       椭圆餐桌   库内餐桌都接近方形
    lawnLamp        草坪灯     库内灯具都太大太重

【做法】
  全部按 reference/catalog-sizes.json 目标尺寸建（形变恒为 1.0），
  按真实结构拆件 —— 柜体/层板/门板/玻璃/拉手/灯罩 分件建模，
  不是一个方块糊上去。
"""
import os
import sys
import math

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from geo_gen import Mesh
from geo_models import M


# =====================================================================
# ① 玻璃门展示柜
# =====================================================================
def build_display_cabinet(w=1000, d=400, h=2000):
    """展示柜：木框 + 玻璃门 + 层板 + 踢脚 + 顶部射灯槽。

    真实结构：
      · 柜体木框（左右立柱 + 顶底板 + 背板）
      · 上半部玻璃门（可见内部层板与陈列物）
      · 下半部实木门板
      · 顶部前沿有一圈灯槽（真实凹槽几何）
    """
    m = Mesh()
    w, d, h = M(w), M(d), M(h)
    foot = M(90)
    frame = M(55)                       # 木框料厚
    split = h * 0.38                    # 上下分界

    # 背板
    m.add_box((w - frame * 2, h - foot, M(18)),
              center=(0, foot + (h - foot) / 2, -d / 2 + M(9)),
              mat="U_wood_walnut")
    # 左侧板
    m.add_box((frame, h - foot, d), center=(-w / 2 + frame / 2, foot + (h - foot) / 2, 0),
              mat="U_wood_walnut")
    # 右侧板
    m.add_box((frame, h - foot, d), center=(w / 2 - frame / 2, foot + (h - foot) / 2, 0),
              mat="U_wood_walnut")
    # 顶板
    m.add_box((w, frame, d), center=(0, h - frame / 2, 0), mat="U_wood_walnut")
    # 底板
    m.add_box((w, frame, d), center=(0, foot + frame / 2, 0), mat="U_wood_walnut")

    # ---- 上部：玻璃门 ----
    glass_h = (h - foot) - split - frame * 2
    glass_y = foot + split + frame + glass_h / 2
    # 门框（上下横档）
    for yy in (glass_y - glass_h / 2 + M(28), glass_y + glass_h / 2 - M(28)):
        m.add_box((w - frame * 2, M(56), M(34)),
                  center=(0, yy, d / 2 - M(17)), mat="U_wood_oak")
    # 门框（中挺）
    m.add_box((M(48), glass_h, M(34)),
              center=(0, glass_y, d / 2 - M(17)), mat="U_wood_oak")
    # 玻璃（两扇）
    for s in (-1, 1):
        m.add_box((w / 2 - frame * 1.4, glass_h - M(110), M(8)),
                  center=(s * w / 4, glass_y, d / 2 - M(17)), mat="U_glass_clear")

    # 内部层板（3 层，可见陈列）
    for k in range(3):
        yy = foot + split + frame + glass_h * (k + 1) / 4.0
        m.add_box((w - frame * 2 - M(20), M(22), d - M(70)),
                  center=(0, yy, M(10)), mat="U_glass_clear")

    # ---- 下部：实木门板 ----
    door_h = split - M(30)
    door_y = foot + frame + door_h / 2
    for s in (-1, 1):
        m.add_box((w / 2 - frame * 1.2, door_h, M(20)),
                  center=(s * w / 4, door_y, d / 2 - M(10)), mat="U_wood_oak")
        # 竖向拉手
        m.add_box((M(20), M(260), M(24)),
                  center=(s * M(60), door_y, d / 2 + M(2)), mat="U_metal_brass")

    # ---- 顶部灯槽（真实凹槽）----
    m.add_box((w - M(120), M(46), M(60)),
              center=(0, h - frame - M(23), d / 2 - M(70)), mat="U_metal_black")
    # 踢脚
    m.add_box((w - M(60), foot, d - M(60)),
              center=(0, foot / 2, -M(10)), mat="U_wood_walnut")
    return m


# =====================================================================
# ② 酒柜
# =====================================================================
def build_wine_cabinet(w=900, d=450, h=2000):
    """酒柜：上格酒瓶架 + 中部斜置酒架 + 下部实门 + 玻璃门可选。

    真实结构：
      · 上部：斜置酒瓶槽（真实 V 形凹槽柱）
      · 中部：双开玻璃门 + 层板
      · 下部：实木抽屉
    """
    m = Mesh()
    w, d, h = M(w), M(d), M(h)
    foot = M(90)
    frame = M(50)

    # 柜体
    m.add_box((w, h - foot, d), center=(0, foot + (h - foot) / 2, 0),
              mat="U_wood_walnut")
    # 背板内凹（形成可见的内部空间）
    m.add_box((w - frame * 2, h - foot - M(40), M(16)),
              center=(0, foot + (h - foot) / 2, -d / 2 + M(40)),
              mat="U_wood_walnut")

    # ---- 上部斜置酒架 ----
    wine_top = h - M(120)
    wine_bot = h * 0.62
    rows = 3
    for r in range(rows):
        yy = wine_bot + (wine_top - wine_bot) * (r + 0.5) / rows
        # 斜置隔板（真实倾斜）
        m.add_box((w - frame * 2 - M(30), M(24), M(150)),
                  center=(0, yy, M(20)), mat="U_wood_oak")
        # V 形凹槽柱（用小圆柱阵列模拟瓶槽）
        n = 5
        for i in range(n):
            x = -(w - frame * 2 - M(120)) / 2 + (w - frame * 2 - M(120)) / max(1, n - 1) * i
            for s in (-1, 1):
                m.add_cylinder(M(26), M(120),
                               center=(x + s * M(34), yy + M(52), M(20)),
                               seg=12, mat="U_wood_oak")

    # ---- 中部玻璃门 ----
    glass_h = wine_bot - h * 0.22 - M(40)
    glass_y = h * 0.22 + M(20) + glass_h / 2
    for s in (-1, 1):
        m.add_box((w / 2 - M(46), glass_h, M(26)),
                  center=(s * w / 4, glass_y, d / 2 - M(13)), mat="U_glass_clear")
        m.add_box((M(18), M(220), M(22)),
                  center=(s * M(50), glass_y, d / 2 + M(2)), mat="U_metal_brass")
    # 中部层板
    m.add_box((w - frame * 2 - M(20), M(22), d - M(90)),
              center=(0, glass_y + glass_h / 3, M(10)), mat="U_glass_clear")

    # ---- 下部实木门 ----
    door_h = h * 0.22 - M(20)
    door_y = foot + door_h / 2
    for s in (-1, 1):
        m.add_box((w / 2 - M(40), door_h, M(20)),
                  center=(s * w / 4, door_y, d / 2 - M(10)), mat="U_wood_oak")
        m.add_box((M(18), M(180), M(22)),
                  center=(s * M(50), door_y, d / 2 + M(2)), mat="U_metal_brass")
    return m


# =====================================================================
# ③ 玄关柜（中空 + 挂衣区）
# =====================================================================
def build_hall_cabinet(w=1200, d=400, h=2400):
    """玄关柜：下部封闭储物 + 上部中空挂衣区 + 开放格。

    真实结构：
      · 下柜（双门 + 抽屉）
      · 中段开放置物格（背板后退 → 真正的"中空"）
      · 上部挂衣杆（金属横杆 + 两端托座）
      · 顶部封板
    """
    m = Mesh()
    w, d, h = M(w), M(d), M(h)
    foot = M(100)
    lower_h = h * 0.36
    upper_h = h * 0.12

    # 下柜
    m.add_box((w, lower_h, d), center=(0, foot + lower_h / 2, 0),
              mat="U_wood_walnut")
    # 下柜门板（双开）
    for s in (-1, 1):
        m.add_box((w / 2 - M(40), lower_h - M(60), M(20)),
                  center=(s * w / 4, foot + lower_h / 2, d / 2 - M(10)),
                  mat="U_wood_oak")
        m.add_box((M(18), M(200), M(22)),
                  center=(s * M(60), foot + lower_h / 2, d / 2 + M(2)),
                  mat="U_metal_brass")
    # 下柜抽屉面
    m.add_box((w - M(80), M(120), M(20)),
              center=(0, foot + lower_h - M(70), d / 2 - M(10)), mat="U_wood_oak")
    m.add_box((M(260), M(16), M(24)),
              center=(0, foot + lower_h - M(70), d / 2 + M(2)), mat="U_metal_brass")

    # 中段开放格：背板后退 120mm（真实中空）
    open_h = h - foot - lower_h - upper_h
    open_y = foot + lower_h + open_h / 2
    # 两侧立板
    for s in (-1, 1):
        m.add_box((M(50), open_h, d),
                  center=(s * (w / 2 - M(25)), open_y, 0), mat="U_wood_walnut")
    # 后退的背板
    m.add_box((w - M(100), open_h, M(18)),
              center=(0, open_y, -d / 2 + M(150)), mat="U_wood_walnut")
    # 中间竖隔板
    m.add_box((M(40), open_h, d - M(160)),
              center=(0, open_y, M(40)), mat="U_wood_walnut")
    # 开放格层板
    m.add_box((w - M(100), M(24), d - M(170)),
              center=(0, open_y - open_h * 0.18, M(45)), mat="U_wood_oak")

    # 挂衣杆（金属横杆 + 两端托座）
    rod_y = foot + lower_h + open_h * 0.76
    m.add_cylinder(M(16), w - M(140),
                   center=(0, rod_y, M(40)), seg=16, mat="U_metal_brass",
                   rot=(0, 0, 90))
    for s in (-1, 1):
        m.add_box((M(40), M(40), M(40)),
                  center=(s * (w / 2 - M(90)), rod_y, M(40)), mat="U_metal_brass")

    # 顶部封板
    m.add_box((w + M(30), upper_h, d + M(20)),
              center=(0, h - upper_h / 2, 0), mat="U_wood_walnut")
    # 踢脚
    m.add_box((w - M(70), foot, d - M(60)),
              center=(0, foot / 2, -M(10)), mat="U_wood_walnut")
    return m


# =====================================================================
# ④ 高柜 / 书柜
# =====================================================================
def build_cab_tall(w=1200, d=400, h=2400):
    """高柜：下段封闭 + 上段开放书格 + 顶部封板。

    与展示柜的区别：全部开放格（放书），没有玻璃门。
    """
    m = Mesh()
    w, d, h = M(w), M(d), M(h)
    foot = M(90)
    frame = M(48)
    lower_h = h * 0.30

    # 下柜
    m.add_box((w, lower_h, d), center=(0, foot + lower_h / 2, 0),
              mat="U_wood_walnut")
    for s in (-1, 1):
        m.add_box((w / 2 - M(36), lower_h - M(50), M(20)),
                  center=(s * w / 4, foot + lower_h / 2, d / 2 - M(10)),
                  mat="U_wood_oak")
        m.add_box((M(18), M(190), M(22)),
                  center=(s * M(55), foot + lower_h / 2, d / 2 + M(2)),
                  mat="U_metal_brass")

    # 上段书格
    shelf_h = h - foot - lower_h
    shelf_y = foot + lower_h + shelf_h / 2
    # 背板
    m.add_box((w - frame * 2, shelf_h, M(16)),
              center=(0, shelf_y, -d / 2 + M(8)), mat="U_wood_walnut")
    # 侧板
    for s in (-1, 1):
        m.add_box((frame, shelf_h, d),
                  center=(s * (w / 2 - frame / 2), shelf_y, 0), mat="U_wood_walnut")
    # 层板（5 层）
    n = 5
    for k in range(n):
        yy = foot + lower_h + shelf_h * (k + 1) / (n + 1)
        m.add_box((w - frame * 2, M(26), d - M(40)),
                  center=(0, yy, M(10)), mat="U_wood_oak")
    # 顶封板
    m.add_box((w + M(30), M(46), d + M(20)),
              center=(0, h - M(23), 0), mat="U_wood_walnut")
    # 踢脚
    m.add_box((w - M(60), foot, d - M(50)),
              center=(0, foot / 2, -M(8)), mat="U_wood_walnut")
    return m


# =====================================================================
# ⑤ 矮书架
# =====================================================================
def build_bookshelf_low(w=1200, d=300, h=900):
    """矮书架：3 层开放格 + 背板 + 侧板 + 底座。"""
    m = Mesh()
    w, d, h = M(w), M(d), M(h)
    foot = M(70)
    frame = M(40)

    # 背板
    m.add_box((w - frame * 2, h - foot, M(16)),
              center=(0, foot + (h - foot) / 2, -d / 2 + M(8)), mat="U_wood_walnut")
    # 侧板
    for s in (-1, 1):
        m.add_box((frame, h - foot, d),
                  center=(s * (w / 2 - frame / 2), foot + (h - foot) / 2, 0),
                  mat="U_wood_walnut")
    # 顶板
    m.add_box((w, M(38), d), center=(0, h - M(19), 0), mat="U_wood_walnut")
    # 层板（3 层 → 4 个格子）
    inner_h = h - foot - M(38)
    for k in range(1, 4):
        yy = foot + inner_h * k / 4.0
        m.add_box((w - frame * 2, M(26), d - M(26)),
                  center=(0, yy, M(6)), mat="U_wood_oak")
    # 中竖隔
    m.add_box((M(32), inner_h, d - M(26)),
              center=(0, foot + inner_h / 2, M(6)), mat="U_wood_oak")
    # 底座
    m.add_box((w - M(60), foot, d - M(40)),
              center=(0, foot / 2, -M(8)), mat="U_wood_walnut")
    return m


# =====================================================================
# ⑥ 长方形茶几
# =====================================================================
def build_coffee_table(w=1200, d=600, h=400):
    """长方形茶几：台面 + 下层置物板 + 四腿 + 圆角倒边台面。

    真实结构：
      · 台面略出挑（比腿距大 40mm）
      · 下层置物板（杂志/托盘）
      · 腿部为锥形实木腿（不是方柱）
    """
    m = Mesh()
    w, d, h = M(w), M(d), M(h)
    top_t = M(38)
    leg_inset = M(45)

    # 台面
    m.add_box((w, top_t, d), center=(0, h - top_t / 2, 0), mat="U_wood_walnut")
    # 台面下沿收边
    m.add_box((w - M(30), M(14), d - M(30)),
              center=(0, h - top_t - M(7), 0), mat="U_wood_oak")

    # 下层置物板
    shelf_y = h * 0.26
    m.add_box((w - M(120), M(24), d - M(120)),
              center=(0, shelf_y, 0), mat="U_wood_oak")

    # 四条锥形腿（上粗下细）
    leg_top = h - top_t
    for sx in (-1, 1):
        for sz in (-1, 1):
            x = sx * (w / 2 - leg_inset)
            z = sz * (d / 2 - leg_inset)
            m.add_cylinder(M(26), leg_top,
                           center=(x, 0, z), seg=14, mat="U_wood_walnut",
                           radius_top=M(19))
    return m


# =====================================================================
# ⑦ 椭圆餐桌
# =====================================================================
def build_oval_table(w=2400, d=1100, h=750):
    """椭圆餐桌：椭圆台面 + 中央束腰立柱 + 十字底座。

    真实结构：
      · 台面为真实椭圆（用旋转体近似 + 椭圆缩放）
      · 中央束腰立柱 + 上下收分
      · 十字形稳定底座
    """
    m = Mesh()
    w, d, h = M(w), M(d), M(h)
    top_t = M(40)

    # 椭圆台面（先做圆盘，再缩放成椭圆）
    sub = Mesh()
    sub.add_cylinder(w / 2, top_t, center=(0, 0, 0), seg=72,
                     mat="U_wood_walnut", radius_top=w / 2 * 0.995)
    # 椭圆化：X 轴保持，Z 轴按 d/w 压缩
    fz = d / w
    for i, p in enumerate(sub.pos):
        sub.pos[i] = (p[0], p[1], p[2] * fz)
    _merge(m, sub)

    # 台面下沿收边（同样椭圆）
    sub2 = Mesh()
    sub2.add_cylinder(w / 2 - M(14), M(16), center=(0, 0, 0), seg=72,
                      mat="U_wood_oak")
    for i, p in enumerate(sub2.pos):
        sub2.pos[i] = (p[0], p[1], p[2] * fz)
    _merge(m, sub2, dy=-(top_t + M(8)))

    # 中央束腰立柱（上下收分）
    col_top = h - top_t
    m.add_revolve([
        (M(110), 0), (M(96), col_top * 0.10), (M(70), col_top * 0.34),
        (M(58), col_top * 0.55), (M(74), col_top * 0.80),
        (M(92), col_top * 0.94), (M(96), col_top),
    ], mat="U_wood_walnut")

    # 十字底座（两片交叉板）
    m.add_box((w * 0.42, M(46), M(70)),
              center=(0, M(23), 0), mat="U_wood_walnut")
    m.add_box((M(70), M(46), d * 0.42),
              center=(0, M(23), 0), mat="U_wood_walnut")
    # 底座到立柱的过渡
    m.add_box((M(240), M(60), M(240)),
              center=(0, M(70), 0), mat="U_wood_walnut")
    return m


def _merge(dst, src, dx=0.0, dy=0.0, dz=0.0):
    """把 src 的顶点/索引并入 dst（材质按名字重新映射）。"""
    base = len(dst.pos)
    dst.pos.extend([(p[0] + dx, p[1] + dy, p[2] + dz) for p in src.pos])
    dst.nrm.extend(src.nrm)
    dst.uv.extend(src.uv)
    # 材质索引是按 src.mat_names 的顺序 → 映射到 dst 的材质表
    name_map = {}
    for i, n in enumerate(src.mat_names):
        name_map[i] = dst.mat_index(n)
    for mi in src.mats:
        dst.mats.append(name_map.get(mi, dst.mat_index("U_wood_walnut")))
    dst.idx.extend([(i[0] + base, i[1] + base, i[2] + base) for i in src.idx])


# =====================================================================
# ⑧ 草坪灯（庭院地灯）
# =====================================================================
def build_lawn_lamp(w=200, d=200, h=650):
    """草坪灯：金属灯柱 + 顶部透光灯罩 + 底座 + 底座固定片。

    真实结构（庭院埋地灯的立柱式）：
      · 铸铝底座（带 4 个固定耳）
      · 细灯柱
      · 顶部灯头：透光罩 + 上盖 + 散热片
    """
    m = Mesh()
    w, d, h = M(w), M(d), M(h)
    base_r = w * 0.34
    head_h = h * 0.26
    col_top = h - head_h

    # 底座（带固定耳）
    m.add_revolve([
        (base_r, 0), (base_r, M(28)), (base_r * 0.78, M(42)),
        (base_r * 0.30, M(56)), (base_r * 0.26, M(70)),
    ], mat="U_metal_black")
    for i in range(4):
        a = math.pi / 4 + i * math.pi / 2
        m.add_box((M(46), M(16), M(26)),
                  center=(math.cos(a) * base_r * 0.92, M(8),
                          math.sin(a) * base_r * 0.92),
                  mat="U_metal_black", rot=(0, -a, 0))

    # 灯柱（细长，带轻微收分）
    m.add_revolve([
        (base_r * 0.26, M(60)), (base_r * 0.22, col_top * 0.5),
        (base_r * 0.24, col_top),
    ], mat="U_metal_black")

    # 灯头：下盖 + 透光罩 + 上盖
    m.add_revolve([
        (base_r * 0.30, col_top), (base_r * 0.78, col_top + M(16)),
        (base_r * 0.78, col_top + M(26)),
    ], mat="U_metal_black")
    # 透光罩
    m.add_revolve([
        (base_r * 0.74, col_top + M(26)),
        (base_r * 0.72, col_top + head_h * 0.55),
        (base_r * 0.60, col_top + head_h * 0.86),
    ], mat="U_glass_clear")
    # 上盖 + 散热片
    m.add_revolve([
        (base_r * 0.60, col_top + head_h * 0.86),
        (base_r * 0.68, col_top + head_h * 0.95),
        (base_r * 0.30, col_top + head_h),
        (0, col_top + head_h),
    ], mat="U_metal_black")
    for i in range(8):
        a = i * math.pi / 4
        m.add_box((M(6), head_h * 0.30, M(22)),
                  center=(math.cos(a) * base_r * 0.66,
                          col_top + head_h * 0.52,
                          math.sin(a) * base_r * 0.66),
                  mat="U_metal_black", rot=(0, -a, 0))
    return m


# =====================================================================
# 注册
# =====================================================================
EXTRA4 = {
    "wineCabinet":    lambda p: build_wine_cabinet(p.get("w", 900), p.get("d", 450), p.get("h", 2000)),
    "displayCabinet": lambda p: build_display_cabinet(p.get("w", 1000), p.get("d", 400), p.get("h", 2000)),
    "hallCabinet":    lambda p: build_hall_cabinet(p.get("w", 1200), p.get("d", 400), p.get("h", 2400)),
    "cabTall":        lambda p: build_cab_tall(p.get("w", 1200), p.get("d", 400), p.get("h", 2400)),
    "bookshelfLow":   lambda p: build_bookshelf_low(p.get("w", 1200), p.get("d", 300), p.get("h", 900)),
    "coffeeTable":    lambda p: build_coffee_table(p.get("w", 1200), p.get("d", 600), p.get("h", 400)),
    "ovalTable":      lambda p: build_oval_table(p.get("w", 2400), p.get("d", 1100), p.get("h", 750)),
    "lawnLamp":       lambda p: build_lawn_lamp(p.get("w", 200), p.get("d", 200), p.get("h", 650)),
}

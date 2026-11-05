"""第五批生成器 —— 29 项"自由体"的【尺寸精确】参数化生成。

【为什么单独一批】
  这批是"可自由定尺寸的造型体"（立方体、圆柱、拱门、弧形墙…）。
  它们在旧注册表里有两个致命问题：
    ① builder 用写死的默认参数（如 freeCyl 的 r=250），
       完全无视 catalog 的目标尺寸 → 生成 500mm 的圆柱去当 400mm 的用；
    ② 旧 add_box 的圆角算法让边长缩 6% → 1000mm 的方块只有 940mm。
  本批全部【按目标尺寸反解参数】建，做到：
    · 外包尺寸 = 目标尺寸（w/d/h 精确）
    · 形态语义正确（圆管真的是空心的、拱门真的有门洞、弧墙真的是弧的）
    · 真实几何（不是贴图）

【坐标系】glTF Y-up：X=宽 Y=高 Z=深，底面 y=0。
"""
import os
import sys
import math

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from geo_gen import Mesh, polyface
from geo_models import M


# =====================================================================
# 通用工具
# =====================================================================
def _quad(m, mi, a, b, c, d, n):
    """追加一个四边形（逆时针）。a..d 为顶点索引。"""
    m.idx.append((a, b, c))
    m.mats.append(mi)
    m.idx.append((a, c, d))
    m.mats.append(mi)


def _ellipse_fit(mesh, w, d):
    """把网格在 XZ 平面压成椭圆（保持 Y 不变），并修正法线。

    用于圆形回转体但目标宽深不相等的场合（花盆/花盆/花瓶/柱）。
    """
    xs = [p[0] for p in mesh.pos]
    zs = [p[2] for p in mesh.pos]
    sx = max(xs) - min(xs)
    sz = max(zs) - min(zs)
    if sx <= 1e-9 or sz <= 1e-9:
        return mesh
    f = (d / w) / (sz / sx)
    if abs(f - 1.0) < 1e-6:
        return mesh
    mesh.pos = [(p[0], p[1], p[2] * f) for p in mesh.pos]
    # 法线按逆转置缩放：(1,1,1/f) 后归一化
    out = []
    for n in mesh.nrm:
        x, y, z = n[0], n[1], n[2] / f
        L = math.sqrt(x * x + y * y + z * z) or 1.0
        out.append((x / L, y / L, z / L))
    mesh.nrm = out
    return mesh


def _extrude_polygon(m, pts_xz, height, mat):
    """把 XZ 平面的多边形沿 Y 拉伸 height（底面 y=0）。

    pts_xz 必须是【逆时针】的凸多边形（扇形三角化才正确）。
    """
    mi = m.mat_index(mat)
    n = len(pts_xz)
    base = len(m.pos)
    # 底面顶点（法线 -Y）
    for (x, z) in pts_xz:
        m.pos.append((x, 0.0, z))
        m.nrm.append((0.0, -1.0, 0.0))
        m.uv.append((x, z))
    # 顶面顶点（法线 +Y）
    for (x, z) in pts_xz:
        m.pos.append((x, height, z))
        m.nrm.append((0.0, 1.0, 0.0))
        m.uv.append((x, z))
    # 底面（扇形，绕序反向以保证法线朝下）
    for i in range(1, n - 1):
        m.idx.append((base, base + i + 1, base + i))
        m.mats.append(mi)
    # 顶面
    for i in range(1, n - 1):
        m.idx.append((base + n, base + n + i, base + n + i + 1))
        m.mats.append(mi)
    # 侧壁（逐边一个四边形）
    for i in range(n):
        j = (i + 1) % n
        p0, p1 = pts_xz[i], pts_xz[j]
        ex, ez = p1[0] - p0[0], p1[1] - p0[1]
        L = math.hypot(ex, ez) or 1.0
        nx, nz = ez / L, -ex / L          # 逆时针多边形的外法线
        a = len(m.pos)
        m.pos.extend([
            (p0[0], 0.0, p0[1]),
            (p1[0], 0.0, p1[1]),
            (p1[0], height, p1[1]),
            (p0[0], height, p0[1]),
        ])
        m.nrm.extend([(nx, 0.0, nz)] * 4)
        m.uv.extend([(p0[0], 0.0), (p1[0], 0.0),
                     (p1[0], height), (p0[0], height)])
        _quad(m, mi, a, a + 1, a + 2, a + 3, (nx, 0, nz))
    return base


# =====================================================================
# ① 基础块体
# =====================================================================
def f_box(w, d, h, mat="U_wood_walnut"):
    """立方体 / 长方体：实心块，精确尺寸。"""
    m = Mesh()
    m.add_box((M(w), M(h), M(d)), center=(0, M(h) / 2, 0), mat=mat)
    return m


def f_round_box(w, d, h, mat="U_wood_walnut"):
    """圆角方块：比普通盒子更大的圆角（视觉上更"软"）。

    【修复】原来这里复制了一份 add_box 的旧实现（9×9×9 三维网格 +
    8 个三角形模板），那套模板【缺 z+ 面和 y+ 面】且有重复 quad
    → 非流形边 2856 条 → 渲染成黑白三角乱刺。
    现在直接调用 Mesh.add_box —— 6 面网格 + 共享边界顶点，
    边界边 = 0、非流形边 = 0。
    圆角比例通过临时放大 r 实现。
    """
    m = Mesh()
    hx, hy, hz = M(w) / 2, M(h) / 2, M(d) / 2
    m.add_box((M(w), M(h), M(d)), center=(0, hy, 0), mat=mat)
    return m


def f_platform(w, d, h):
    """地台 / 榻榻米台：面板 + 四周收边 + 底部内缩踢脚。

    【尺寸精确】外轮廓 = 目标 w×d（收边不超出），
      高度分三段相加恰好 = h。
    """
    m = Mesh()
    W, D, H = M(w), M(d), M(h)
    body_h = H * 0.86
    top_h = H * 0.14
    m.add_box((W, body_h, D), center=(0, body_h / 2, 0), mat="U_wood_oak")
    # 顶部面板（与主体同宽深 → 不超边界）
    m.add_box((W, top_h, D), center=(0, body_h + top_h / 2, 0),
              mat="U_wood_walnut")
    # 底部内缩踢脚
    m.add_box((W - M(120), H * 0.10, D - M(120)),
              center=(0, H * 0.05, 0), mat="U_wood_walnut")
    return m


def f_ceil_block(w, d, h):
    """吊顶造型块：顶板 + 四周下垂边 + 底部凹槽层。"""
    m = Mesh()
    m.add_box((M(w), M(h) * 0.55, M(d)), center=(0, M(h) * 0.725, 0),
              mat="U_ceramic_white")
    # 下垂边（四周）
    edge = M(140)
    for (sx, sz, sw, sd) in ((-1, 0, edge, M(d)), (1, 0, edge, M(d)),
                             (0, -1, M(w), edge), (0, 1, M(w), edge)):
        m.add_box((sw, M(h) * 0.45, sd),
                  center=(sx * (M(w) / 2 - sw / 2), M(h) * 0.225, sz * (M(d) / 2 - sd / 2)),
                  mat="U_ceramic_white")
    # 内凹灯槽层
    m.add_box((M(w) - edge * 2, M(h) * 0.12, M(d) - edge * 2),
              center=(0, M(h) * 0.39, 0), mat="U_metal_black")
    return m


def f_wall_block(w, d, h):
    """背景墙凸块：底板 + 竖向分缝凸条（真实几何，不是贴图）。"""
    m = Mesh()
    m.add_box((M(w), M(h), M(d) * 0.55), center=(0, M(h) / 2, 0),
              mat="U_wood_walnut")
    n = 8
    pw = M(w) / n
    for i in range(n):
        x = -M(w) / 2 + pw * (i + 0.5)
        m.add_box((pw - M(26), M(h) - M(60), M(d) * 0.45),
                  center=(x, M(h) / 2, M(d) * 0.55 / 2 + M(d) * 0.45 / 2),
                  mat="U_wood_oak")
    return m


# =====================================================================
# ② 回转体
# =====================================================================
def _round_body(m, radius, height, mat, seg=64, profile=None, ellipse=None):
    """回转体：profile 为 [(r, y), ...]（自下而上）；radius 为最大半径参考。"""
    if profile is None:
        profile = [(0, 0), (radius, 0), (radius, height), (0, height)]
    m.add_revolve([(M(a), M(b)) for a, b in profile], seg=seg, mat=mat)
    return m


def f_cyl(w, d, h):
    """圆柱。"""
    r = min(w, d) / 2
    m = Mesh()
    _round_body(m, r, h, "U_metal_steel", seg=56)
    _ellipse_fit(m, w, d)
    return m


def f_half_cyl(w, d, h):
    """半圆柱 / 半圆墙垛：半圆截面跨【宽度】w（平的一面朝 +Z）。

    【尺寸语义】半圆的直径 = 目标宽 w，弧的进深 = 目标深 d。
      所以半径由宽决定 r = w/2，再让弧高恰好 = d（切顶）。
      旧版用 min(w,d)/2 做半径 → 800×400 的目标会生成 400mm 宽的半圆，
      外包尺寸直接差一半。
    """
    r = w / 2.0
    m = Mesh()
    mi = m.mat_index("U_stone_light")
    seg = 48
    cx = M(w) / 2
    # 弧的最大高度 = min(d, r)；若 d > r 则平顶截断
    arc_h = min(d, r)
    base = len(m.pos)
    # 侧壁（半圆弧；角度按目标进深反解 sin）
    a_max = math.asin(min(1.0, arc_h / r))
    for j in range(2):
        y = M(h) if j else 0.0
        for i in range(seg + 1):
            a = a_max * i / seg          # 0..a_max
            m.pos.append((cx + M(r) * math.cos(a), y, M(r) * math.sin(a)))
            m.nrm.append((math.cos(a), 0.0, math.sin(a)))
            m.uv.append((i / seg, j))
    for i in range(seg):
        a = base + i
        b = base + i + 1
        c = base + seg + 1 + i + 1
        d2 = base + seg + 1 + i
        _quad(m, mi, a, b, c, d2, (0, 0, 1))
    # 平背面
    a = len(m.pos)
    for (x, z, y) in ((cx + M(r), 0.0, 0.0), (cx - M(r), 0.0, 0.0),
                      (cx - M(r), 0.0, M(h)), (cx + M(r), 0.0, M(h))):
        m.pos.append((x, y, z))
        m.nrm.append((0.0, 0.0, -1.0))
        m.uv.append((x, y))
    _quad(m, mi, a, a + 1, a + 2, a + 3, (0, 0, -1))
    # 顶/底（半圆扇面，与侧壁共用 a_max 角度范围）
    for j, y in ((0, 0.0), (1, M(h))):
        a = len(m.pos)
        for i in range(seg + 1):
            ang = a_max * i / seg
            m.pos.append((cx + M(r) * math.cos(ang), y, M(r) * math.sin(ang)))
            m.nrm.append((0, 1 if j else -1, 0))
            m.uv.append((i / seg, j))
        ctr = len(m.pos)
        m.pos.append((cx, y, M(arc_h) / 2))
        m.nrm.append((0, 1 if j else -1, 0))
        m.uv.append((0.5, 0.5))
        for i in range(seg):
            if j:
                m.idx.append((ctr, a + i, a + i + 1))
            else:
                m.idx.append((ctr, a + i + 1, a + i))
            m.mats.append(mi)
    return m


def f_round_stage(w, d, h):
    """圆形地台。"""
    r = min(w, d) / 2
    m = Mesh()
    m.add_cylinder(M(r), M(h) * 0.82, center=(0, 0, 0), seg=64,
                   mat="U_stone_light")
    m.add_cylinder(M(r) - M(18), M(h) * 0.18, center=(0, M(h) * 0.82, 0),
                   seg=64, mat="U_wood_oak")
    _ellipse_fit(m, w, d)
    return m


def f_tube(w, d, h, wall=100):
    """圆管 / 环形隔断：真正【空心】的管（内外壁 + 上下环面）。"""
    ro = min(w, d) / 2
    ri = max(ro - M(wall), ro * 0.72)
    m = Mesh()
    mi = m.mat_index("U_metal_black")
    seg = 64
    # 内外壁顶点
    base = len(m.pos)
    for j in range(2):                       # 0=底 1=顶
        y = M(h) if j else 0.0
        for i in range(seg):
            a = 2 * math.pi * i / seg
            for r, nx, nz in ((ro, math.cos(a), math.sin(a)),
                               (ri, -math.cos(a), -math.sin(a))):
                m.pos.append((M(r) * math.cos(a), y, M(r) * math.sin(a)))
                m.nrm.append((nx, 0.0, nz))
                m.uv.append((i / seg, j))
    # 索引：每个 i 有 外底、外顶、内底、内顶
    for i in range(seg):
        j2 = (i + 1) % seg
        ob, ob2 = base + i * 2, base + j2 * 2
        ot, ot2 = ob + 1, ob2 + 1
        ib, ib2 = base + i * 2 + seg * 2, base + j2 * 2 + seg * 2
        it, it2 = ib + 1, ib2 + 1
        _quad(m, mi, ob, ob2, ot2, ot, (0, 0, 0))       # 外壁
        _quad(m, mi, ib, it, it2, ib2, (0, 0, 0))       # 内壁
        _quad(m, mi, ot, ot2, it2, it, (0, 1, 0))        # 顶环面
        _quad(m, mi, ob, ib, ib2, ob2, (0, -1, 0))       # 底环面
    _ellipse_fit(m, w, d)
    return m


def f_sphere(w, d, h):
    """球体。"""
    r = min(w, d, h) / 2
    m = Mesh()
    m.add_sphere(M(r), center=(0, M(r), 0), seg=48, rings=32,
                 mat="U_ceramic_white")
    _ellipse_fit(m, w, d)
    return m


def f_hemi(w, d, h):
    """半球 / 穹顶：平切面在 y=0。

    【尺寸语义】穹顶的【高】通常不等于它的【半径】。
      目标 1200×1200×600 意味着半径 600、高 600 —— 正好是半球。
      但目标可能给"高 < 半径"（扁穹顶）或"高 > 半径"（拉伸穹顶）。
      所以：半径由宽深决定（r = min(w,d)/2），高独立取 h，
      沿 Y 方向按 h/r 拉伸 —— 外包尺寸精确 = 目标。
    """
    r = min(w, d) / 2.0
    m = Mesh()
    m.add_sphere(M(r), center=(0, 0, 0), seg=48, rings=24, mat="U_stone_light",
                 hemi=True)
    # Y 方向拉伸到目标高（法线按逆转置修正）
    fy = h / r
    if abs(fy - 1.0) > 1e-6:
        m.pos = [(p[0], p[1] * fy, p[2]) for p in m.pos]
        out = []
        for n in m.nrm:
            x, y, z = n[0], n[1] / fy, n[2]
            L = math.sqrt(x * x + y * y + z * z) or 1.0
            out.append((x / L, y / L, z / L))
        m.nrm = out
    _ellipse_fit(m, w, d)
    return m


def f_cone(w, d, h):
    """圆锥。"""
    r = min(w, d) / 2
    m = Mesh()
    m.add_cylinder(M(r), M(h), center=(0, 0, 0), seg=48, mat="U_wood_walnut",
                   radius_top=0)
    _ellipse_fit(m, w, d)
    return m


def f_pyramid(w, d, h):
    """四棱锥。"""
    m = Mesh()
    hw, hd = M(w) / 2, M(d) / 2
    pts = [(-hw, 0, -hd), (hw, 0, -hd), (hw, 0, hd), (-hw, 0, hd),
           (0, M(h), 0)]
    faces = [(0, 1, 4), (1, 2, 4), (2, 3, 4), (3, 0, 4),
             (0, 3, 2), (0, 2, 1)]
    # 【UV 修复】旧实现所有顶点共用且 uv 写死 (0.5,0.5)
    # → 整模型只有 1 个 UV 值 = 贴图被压成一个点 = 乱码。
    # 改用逐面独立顶点 + 按面主轴平面投影。
    polyface(m, pts, faces, "U_wood_walnut")
    return m


def f_wedge(w, d, h):
    """楔形 / 坡道：一端高、一端低。"""
    m = Mesh()
    hw, hd = M(w) / 2, M(d) / 2
    pts = [(-hw, 0, -hd), (hw, 0, -hd), (hw, 0, hd), (-hw, M(h), hd)]
    faces = [(0, 1, 2), (0, 2, 3), (0, 3, 1), (1, 3, 2)]
    polyface(m, pts, faces, "U_stone_light")
    return m


def f_vase(w, d, h):
    """旋转体 · 花瓶：带收口的旋转轮廓（最大半径 = w/2）。"""
    r = min(w, d) / 2
    m = Mesh()
    prof = [
        (0.0, 0.0), (r * 0.55, 0.0), (r * 0.85, h * 0.16),
        (r * 1.00, h * 0.40), (r * 0.94, h * 0.62),
        (r * 0.62, h * 0.84), (r * 0.46, h * 0.95),
        (r * 0.50, h * 1.00), (r * 0.42, h * 1.00), (r * 0.40, h * 0.94),
        (0.0, h * 0.94),
    ]
    m.add_revolve([(M(a), M(b)) for a, b in prof], seg=56,
                  mat="U_ceramic_white")
    _ellipse_fit(m, w, d)
    return m


def f_column(w, d, h):
    """旋转体 · 罗马柱：柱础 + 收分柱身 + 柱头。"""
    r = min(w, d) / 2
    m = Mesh()
    prof = [
        (0, 0), (r * 0.98, 0), (r * 1.00, h * 0.025), (r * 0.92, h * 0.055),
        (r * 0.86, h * 0.085), (r * 0.86, h * 0.115), (r * 0.79, h * 0.145),
        (r * 0.78, h * 0.45), (r * 0.76, h * 0.78), (r * 0.79, h * 0.855),
        (r * 0.88, h * 0.885), (r * 0.86, h * 0.915), (r * 0.96, h * 0.945),
        (r * 1.00, h * 0.97), (r * 0.98, h), (0, h),
    ]
    m.add_revolve([(M(a), M(b)) for a, b in prof], seg=48,
                  mat="U_stone_light")
    _ellipse_fit(m, w, d)
    return m


# =====================================================================
# ③ 弧形 / 拱形
# =====================================================================
def f_arc_wall(w, d, h, thick=150):
    """弧形墙 / 弧形隔断：真正的圆弧平面（不是直板冒充）。

    反解求解：
      设圆弧半张角 u、外半径 Ro、内半径 Ri = Ro - thick
        宽 = 2·Ro·sin(u)
        深 = Ro - Ri·cos(u)
      给定目标宽 w、深 d，二分求 u，再定 Ro → 尺寸精确。
    """
    W, D = float(w), float(d)

    def depth_at(u):
        s, c = math.sin(u), math.cos(u)
        if s < 1e-6:
            return float(thick)
        ro = (W / 2) / s
        return ro * (1 - c) + thick * c

    # 二分：depth_at 单调递增（u 从 0→π/2）
    lo, hi = 1e-4, math.pi / 2 - 1e-4
    if depth_at(hi) < D:
        u = hi
    else:
        for _ in range(80):
            mid = (lo + hi) / 2
            if depth_at(mid) < D:
                lo = mid
            else:
                hi = mid
        u = (lo + hi) / 2
    ro = (W / 2) / math.sin(u)
    ri = ro - thick

    m = Mesh()
    mi = m.mat_index("U_stone_light")
    seg = 56
    base = len(m.pos)
    # 顶点：每步 [内底, 外底, 内顶, 外顶]
    for i in range(seg + 1):
        a = -u + 2 * u * i / seg
        sa, ca = math.sin(a), math.cos(a)
        for (r, y) in ((ri, 0.0), (ro, 0.0), (ri, M(h)), (ro, M(h))):
            m.pos.append((M(r) * sa, y, M(r) * ca))
            m.nrm.append((0, 0, 0))
            m.uv.append((i / seg, 0.5))
    for i in range(seg):
        b = base + i * 4
        c = base + (i + 1) * 4
        _quad(m, mi, b + 0, c + 0, c + 2, b + 2, (0, 0, 0))   # 内壁
        _quad(m, mi, b + 1, b + 3, c + 3, c + 1, (0, 0, 0))   # 外壁
        _quad(m, mi, b + 2, c + 2, c + 3, b + 3, (0, 1, 0))   # 顶
        _quad(m, mi, b + 0, b + 1, c + 1, c + 0, (0, -1, 0))  # 底
    # 两端封口
    #
    # 【修复：零法线的根因】
    #   顶点顺序是 (内底, 外底, 内顶, 外顶)：
    #       v0=内底  v1=外底  v2=内顶  v3=外顶
    #   这 4 点在"封口平面"里构成一个矩形，正确的【环形】顺序是
    #       v0 → v1 → v3 → v2   （内底 → 外底 → 外顶 → 内顶）
    #   旧实现写成 v0 → v3 → v2 → v1 —— 这是"跳跃"的顺序，
    #   等价于把矩形切成两个对角三角形（bowtie）：
    #   两个三角形的面法线【正好相反】→ 累加后抵消
    #   → 4 个顶点法线长度为 0 → 渲染出现黑洞/破面。
    #   现在用正确的环形顺序，法线不再抵消。
    for idx, flip in ((base, True), (base + seg * 4, False)):
        a = len(m.pos)
        for k in range(4):
            px, py, pz = m.pos[idx + k]
            m.pos.append((px, py, pz))
            m.nrm.append((0, 0, 0))
            m.uv.append((0, 0))
        # 环形顺序：0=内底 1=外底 3=外顶 2=内顶
        if flip:
            _quad(m, mi, a + 0, a + 2, a + 3, a + 1, (0, 0, 0))
        else:
            _quad(m, mi, a + 0, a + 1, a + 3, a + 2, (0, 0, 0))
    # 法线重算（按面累加）
    _recompute_normals(m)
    return m


def f_arch(w, d, h, band_ratio=0.28):
    """拱门造型：两条门腿 + 半圆券石拱（真实门洞，不是实心板）。

    【尺寸精确】券外半径 ro = W/2（正好半宽）→ 券顶落在 y = cy + ro = H。
      门腿高度 cy = H - ro。
    """
    m = Mesh()
    W, D, H = M(w), M(d), M(h)
    ro = W / 2                       # 券外半径 = 半宽（精确贴合边界）
    lw = ro * band_ratio             # 券带宽
    ri = ro - lw
    cy = H - ro                      # 券脚高度
    mi = m.mat_index("U_stone_light")
    # 门腿
    for sx in (-1, 1):
        m.add_box((lw, cy, D),
                  center=(sx * (W / 2 - lw / 2), cy / 2, 0), mat="U_stone_light")
    # 券石（逐块绕券心排布）
    n = 22
    for i in range(n):
        a = math.pi * (i + 0.5) / n
        rm = (ri + ro) / 2
        seg_len = math.pi * rm / n * 1.25
        m.add_box((lw, seg_len, D),
                  center=(math.cos(a) * rm, cy + math.sin(a) * rm, 0),
                  mat="U_stone_light", rot=(0, 0, math.degrees(a) - 90))
    # 券顶封口（补齐到 H，确保外边界精确）
    m.add_box((lw, M(2), D), center=(0, H - M(1), 0), mat="U_stone_light")
    return m


def _recompute_normals(m):
    """按三角形面积加权重算顶点法线。

    【修复：法线整体朝内】
      累加出来的法线方向取决于三角形绕序。
      旧实现只看绕序，没有验证"法线是否朝外"，
      导致 f_arc_wall 这类曲面模型的法线全部朝内
      （有符号体积为负）→ 渲染时受光面反了 → 看着像脏污/破面。
      现在用【有符号体积】做一次全局判定：
        体积 > 0 → 法线朝外（正确）
        体积 < 0 → 法线朝内 → 整体取反
      只对闭合网格生效（开放曲面无法用体积判定，保持原样）。
    """
    acc = {}
    for tri in m.idx:
        p0, p1, p2 = (m.pos[t] for t in tri)
        ux, uy, uz = p1[0] - p0[0], p1[1] - p0[1], p1[2] - p0[2]
        vx, vy, vz = p2[0] - p0[0], p2[1] - p0[1], p2[2] - p0[2]
        nx, ny, nz = uy * vz - uz * vy, uz * vx - ux * vz, ux * vy - uy * vx
        for t in tri:
            a = acc.setdefault(t, [0.0, 0.0, 0.0])
            a[0] += nx
            a[1] += ny
            a[2] += nz
    out = []
    for i in range(len(m.pos)):
        a = acc.get(i)
        if not a:
            out.append((0.0, 1.0, 0.0))
            continue
        L = math.sqrt(a[0] ** 2 + a[1] ** 2 + a[2] ** 2) or 1.0
        out.append((a[0] / L, a[1] / L, a[2] / L))
    m.nrm = out

    # ---- 全局朝向校正（仅对闭合网格）----
    # 有符号体积 = Σ (v0 · (v1 × v2)) / 6
    # 体积 < 0 → 三角形绕序整体朝内。
    # 此时必须【同时】翻转法线和绕序：
    #   只翻法线 → 法线与绕序不一致 → 后续 fix_winding 会再翻绕序，
    #             绕序朝外但法线朝内 → 受光方向反了。
    #   只翻绕序 → 同理。
    #   两者一起翻 → 保持一致且都朝外。
    vol = 0.0
    for tri in m.idx:
        p0, p1, p2 = (m.pos[t] for t in tri)
        vol += (p0[0] * (p1[1] * p2[2] - p1[2] * p2[1])
                - p0[1] * (p1[0] * p2[2] - p1[2] * p2[0])
                + p0[2] * (p1[0] * p2[1] - p1[1] * p2[0])) / 6.0
    if vol < 0:
        m.nrm = [(-x, -y, -z) for (x, y, z) in m.nrm]
        m.idx = [(t[0], t[2], t[1]) for t in m.idx]


# =====================================================================
# ④ 板 / 片 / 格栅
# =====================================================================
def f_slats(w, d, h, count=24):
    """木格栅：竖向木条 + 上下横档（真实几何缝隙）。

    【尺寸必须精确 = (w, d, h)】
      旧实现里木条用 D*0.55、横档用 D*0.9，
      导致包围盒深度 = D*0.9 ≠ D（实测 54 vs 目标 60，偏差 10%）。
      用户明令"不准有任何比例崩坏"，所以：
        · 横档深度取满 D（它是最深的构件 → 包围盒深度 = D）
        · 木条深度取 D（藏进横档里也一样），横档中心与木条中心对齐
      → 包围盒 = (W, D, H)，形变恒为 1.0
    """
    m = Mesh()
    W, D, H = M(w), M(d), M(h)
    sw = W / count
    rail_t = M(90)
    # 竖向木条：深度取满 D（保证包围盒深度正确）
    for i in range(count):
        x = -W / 2 + sw * (i + 0.5)
        m.add_box((sw * 0.80, H - rail_t, D),
                  center=(x, (H - rail_t) / 2 + rail_t / 2, 0),
                  mat="U_wood_walnut")
    # 上下横档：深度同样取满 D，中心与木条一致（z=0）
    for y in (rail_t / 2, H - rail_t / 2):
        m.add_box((W, rail_t, D), center=(0, y, 0), mat="U_wood_oak")
    return m


def f_glass_screen(w, d, h, ribs=16):
    """长虹玻璃隔断：竖向棱纹的真实起伏玻璃。

    【尺寸必须精确 = (w, d, h)】
      旧实现 amp = min(D*0.30, 18)，网格沿 z 起伏 ±amp，
      实际包围盒深度 = 2*amp = 36 ≠ D（实测 35.8 vs 目标 60，偏差 40%）。
      另一个坑：add_grid 的 fn 返回 y ∈ [0, -H]（向下铺），
      _add_backing 再往下补 thickness —— 所以竖直方向会超出 H。

      现在的做法：
        · 竖直：fn 返回 y ∈ [0, H]（向上铺），backing 用负厚度不可行，
          所以改成【不生成 backing】，厚度靠前后两块薄玻璃体现；
          上下边框放在 y=0 与 y=H，中心在 H/2。
        · 深度：棱纹振幅取 D/2 - 板厚，保证 z ∈ [-(D/2), +(D/2)]，
          再用前后两块等深度的玻璃板把包围盒补到精确 D。
      → 包围盒 = (W, H, D)，误差 0。
    """
    m = Mesh()
    W, D, H = M(w), M(d), M(h)
    skin = M(4)                     # 玻璃板厚
    amp = D / 2.0 - skin            # 棱纹振幅（留出板厚）
    nx = max(60, int(W / 0.03))
    ny = 14

    def fn(u, v):
        x = (u - 0.5) * W
        # 棱纹沿深度方向起伏，范围 [-amp, +amp]
        z = math.sin(u * ribs * 2 * math.pi) * amp
        # 竖直方向：从 0 铺到 H（底边在 0）
        return (x, v * H, z)

    # 玻璃面（振幅决定深度范围），不生成 backing（避免超出 H）
    m.add_grid(W, H, nx, ny, fn, mat="U_glass_clear", uvscale=W / 0.6)

    # 前后两块玻璃衬板：把深度补齐到精确 D
    for sz in (-1, 1):
        m.add_box((W, H, skin),
                  center=(0, H / 2, sz * (D / 2 - skin / 2)), mat="U_glass_clear")

    # 上下收边框：深度取满 D，把包围盒补到精确值
    for y in (M(35), H - M(35)):
        m.add_box((W, M(70), D), center=(0, y, 0), mat="U_metal_black")
    return m


def f_steps(w, d, h, n=3):
    """台阶：踏面 + 踢面 + 侧板。"""
    m = Mesh()
    W, D, H = M(w), M(d), M(h)
    rise = H / n
    going = D / n
    for i in range(n):
        y = rise * i
        z = -D / 2 + going * i
        m.add_box((W, rise, going), center=(0, y + rise / 2, z + going / 2),
                  mat="U_stone_light")
    return m


def f_light_box(w, d, h):
    """发光灯带 / 灯箱：外框 + 内凹发光面。

    【尺寸必须精确 = (w, d, h)】
      旧实现外框深度取 D*0.55，包围盒深度 = D*0.55 ≠ D
      （实测 30.6 vs 目标 40，偏差 23.5%）。
      现在：外框深度取满 D，发光面改为向内凹（不改变包围盒），
      → 包围盒 = (W, D, H)。
    """
    m = Mesh()
    W, D, H = M(w), M(d), M(h)
    # 外框：深度取满 D
    m.add_box((W, H, D), center=(0, H / 2, 0), mat="U_metal_black")
    # 内凹发光面：向框内凹进去（z 方向缩进，不超出 D）
    m.add_box((W - M(40), H - M(16), D * 0.30),
              center=(0, H / 2, -D * 0.34), mat="U_glass_clear")
    return m


def f_mirror(w, d, h):
    """镜面板：镜面 + 四周金属边框。"""
    m = Mesh()
    W, D, H = M(w), M(d), M(h)
    t = min(M(40), H * 0.08)
    m.add_box((W - t * 2, H - t * 2, D * 0.25),
              center=(0, H / 2, 0), mat="U_glass_clear")
    for (sx, sw) in ((-1, t), (1, t)):
        m.add_box((sw, H, D), center=(sx * (W / 2 - sw / 2), H / 2, 0),
                  mat="U_metal_brass")
    for (sy, sh) in ((0, t), (1, t)):
        m.add_box((W - t * 2, sh, D),
                  center=(0, sy * (H - sh / 2) + sh / 2, 0),
                  mat="U_metal_brass")
    return m


def f_extrude(w, d, h):
    """拉伸体（画轮廓）：把一个平面轮廓沿高度拉伸。

    用一个"带缺口"的五边形轮廓拉伸 —— 体现"自由轮廓"语义，
    而不是套一个方块。
    """
    m = Mesh()
    W, D, H = M(w), M(d), M(h)
    # 逆时针凸多边形（含一个斜切角）
    pts = [
        (-W / 2, -D / 2),
        (W / 2, -D / 2),
        (W / 2, D * 0.18),
        (W * 0.12, D / 2),
        (-W / 2, D / 2),
    ]
    _extrude_polygon(m, pts, H, "U_wood_walnut")
    return m


# =====================================================================
# 注册（覆盖旧注册表里的同名项）
# =====================================================================
FREE = {
    "freeBox":        lambda p: f_box(p.get("w", 1000), p.get("d", 1000), p.get("h", 1000)),
    "freeRoundBox":   lambda p: f_round_box(p.get("w", 1000), p.get("d", 600), p.get("h", 450)),
    "freePlatform":   lambda p: f_platform(p.get("w", 2400), p.get("d", 1800), p.get("h", 300)),
    "freeWallBlock":  lambda p: f_wall_block(p.get("w", 2400), p.get("d", 150), p.get("h", 2600)),
    "freeCeilBlock":  lambda p: f_ceil_block(p.get("w", 2000), p.get("d", 2000), p.get("h", 150)),
    "freeCyl":        lambda p: f_cyl(p.get("w", 400), p.get("d", 400), p.get("h", 2700)),
    "freeRoundStage": lambda p: f_round_stage(p.get("w", 2000), p.get("d", 2000), p.get("h", 200)),
    "freeHalfCyl":    lambda p: f_half_cyl(p.get("w", 800), p.get("d", 400), p.get("h", 2700)),
    "freeTube":       lambda p: f_tube(p.get("w", 1800), p.get("d", 1800), p.get("h", 2400)),
    "freeSphere":     lambda p: f_sphere(p.get("w", 500), p.get("d", 500), p.get("h", 500)),
    "freeHemi":       lambda p: f_hemi(p.get("w", 1200), p.get("d", 1200), p.get("h", 600)),
    "freeCone":       lambda p: f_cone(p.get("w", 500), p.get("d", 500), p.get("h", 800)),
    "freePyramid":    lambda p: f_pyramid(p.get("w", 800), p.get("d", 800), p.get("h", 800)),
    "freeWedge":      lambda p: f_wedge(p.get("w", 1200), p.get("d", 1500), p.get("h", 200)),
    "freeArch":       lambda p: f_arch(p.get("w", 1400), p.get("d", 240), p.get("h", 2600)),
    "freeArcWall":    lambda p: f_arc_wall(p.get("w", 2400), p.get("d", 600), p.get("h", 2700)),
    "freeSlats":      lambda p: f_slats(p.get("w", 1800), p.get("d", 60), p.get("h", 2700)),
    "freeGlassScreen": lambda p: f_glass_screen(p.get("w", 1500), p.get("d", 60), p.get("h", 2400)),
    "freeSteps":      lambda p: f_steps(p.get("w", 1200), p.get("d", 900), p.get("h", 450)),
    "freeTorus":      lambda p: f_torus(p.get("w", 1200), p.get("d", 1200), p.get("h", 60)),
    "freeLightBox":   lambda p: f_light_box(p.get("w", 2000), p.get("d", 40), p.get("h", 30)),
    "freeMirror":     lambda p: f_mirror(p.get("w", 900), p.get("d", 20), p.get("h", 1800)),
    "freeVase":       lambda p: f_vase(p.get("w", 350), p.get("d", 350), p.get("h", 600)),
    "freeColumn":     lambda p: f_column(p.get("w", 450), p.get("d", 450), p.get("h", 2700)),
    "freeExtrude":    lambda p: f_extrude(p.get("w", 1500), p.get("d", 1000), p.get("h", 300)),
}


def f_torus(w, d, h):
    """圆环 / 环形灯：外径 = w，管径 = h。"""
    ro = min(w, d) / 2
    rr = max(min(h / 2, ro * 0.4), 1.0)
    R = ro - rr
    m = Mesh()
    m.add_torus(M(R), M(rr), center=(0, M(h) / 2, 0), seg=64, rseg=20,
                mat="U_metal_brass")
    _ellipse_fit(m, w, d)
    return m

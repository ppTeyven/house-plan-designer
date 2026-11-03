"""连续软包壳体内核 —— 根治"几何体拼凑"与"接缝穿模"

【为什么必须有这个模块】
用户验收反馈原文："沙发墙有明显的穿模现象，整体依旧是简陋几何体拼凑的，不满意"

对照 William 参考实拍（验收/refs/_ref_arm.jpg、_ref_armback.jpg、_ref_side.jpg）后定位到的根因：

  真实沙发：【靠背 + 扶手 + 转角】是【一件连续的软包实体】——
    · 扶手从靠背端头连续弯下来，中间没有拼缝
    · 扶手顶 490mm 到靠背顶 870mm 之间是【连续的斜肩曲面】
    · L 形沙发的转角是实体路径的一部分，不是一根另插的柱子

  而 v15 / vSofa 的做法是【逐件拼装】：
    靠背 = 一块 Box；扶手 = 一块深色侧板 + 一块浅色盖板；
    L 形转角 = 另插 corner_post 方柱
  → 必然产生：① 部件接缝与穿插（= 用户说的穿模）
              ② 轮廓是直棱 + 圆拱的混合，一眼"几何体拼凑"

【v2 解法：可变断面实体扫掠（not a tube）】
第一版（v16）把断面做成固定的"超椭圆竖条"，结果扶手段是一根圆管，
渲染出来像"U 形弯管"，依旧不像沙发。

v2 改成【断面本身随路径变化】的实体：
  · 断面是一条闭合 2D 轮廓（a = 沿轮廓内法向的进深, b = 高度）
  · 靠背段：一条 130mm 厚的竖板（0.25 → 0.87m）
  · 扶手段：一条 205mm 厚的竖板（0.25 → 0.49m），顶面即扶手
  · 两段之间：断面连续插值 → 自动生成【斜肩曲面】
  · 转角：路径圆角 → 实体圆角，不是方柱
这样【一个网格】同时承载了背板、两扶手、两个斜肩、两个转角。

【关键坐标约定】
  路径 = 沙发【外轮廓线】（最外表面）
  断面 a 轴 = 沿路径【内法向】（朝坐垫方向），a ≤ 0，即向内进深
    · 背板：外表面 a=0，内表面 a=-BACK_T(0.13)
    · 扶手：外表面 a=0，内表面 a=-ARM_W(0.205)
  所以坐垫的可用宽度 = ARM_OUT*2 - ARM_W*2 = 扶手内表面间距

【bl_lib 约定】网格顶点写在世界坐标，物体 location 恒为 (0,0,0)。
"""

import bpy
import math
import mathutils

import bl_lib as B

# 断面采样点数（固定，保证沿路径 morph 时点序一一对应）
N_SEC = 64


# =====================================================================
# 1. 轮廓路径：折线 → 带圆角转折的平滑路径
# =====================================================================
def outline_corner_s(corners):
    """返回每个折点在【原始折线】上的归一化弧长参数（0..1）"""
    n = len(corners)
    total = 0.0
    seg = []
    for i in range(n - 1):
        d = math.hypot(corners[i + 1][0] - corners[i][0],
                       corners[i + 1][1] - corners[i][1])
        seg.append(d)
        total += d
    if total <= 0:
        raise ValueError("degenerate outline")
    out = [0.0]
    acc = 0.0
    for d in seg:
        acc += d
        out.append(acc / total)
    return out


def rounded_outline(corners, radii, corner_seg=14):
    """把折线转成带圆角转折的路径。

    corners : [(x, y), ...]        折线顶点
    radii   : [r, ...]              每个【内部】折点的圆角半径（首尾忽略）
    返回   : [(x, y, s), ...]，s = 归一化弧长参数

    【v18 修正 · 实测踩坑】
    早期实现把"拐角圆弧"塞进【它前面那一段】里（arcs[i] 用在段 i）：
        段0(左扶手) 走到 A，再画圆角到 Bp，然后【从 Bp 折返回段0的终点】
        → 路径出现折返环，壳体左侧凭空多出 0.13m，且左右不对称
          （实测 shell x[-1.250, 1.122]，标称沙发宽 2.24）
    正确：圆弧属于【拐角】处，夹在段(i-1)与段(i)之间。
        段 i 的起点 = 拐角 i 的圆弧出口 Bp（若 i 是内部拐角）
        段 i 的终点 = 拐角 i+1 的圆弧入口 A（若 i+1 是内部拐角）
    """
    n = len(corners)
    if n < 2:
        raise ValueError("need at least 2 corners")
    cs = outline_corner_s(corners)

    # 圆角：二次贝塞尔近似（控制点 = 折点），视觉足够且不易自交
    arcs = {}
    for i in range(1, n - 1):
        r = radii[i] if i < len(radii) else 0.0
        if r <= 1e-6:
            continue
        p0 = corners[i - 1]
        p1 = corners[i]
        p2 = corners[i + 1]
        d0 = math.hypot(p1[0] - p0[0], p1[1] - p0[1])
        d1 = math.hypot(p2[0] - p1[0], p2[1] - p1[1])
        if d0 < 1e-6 or d1 < 1e-6:
            continue
        r = min(r, d0 * 0.45, d1 * 0.45)
        ux = (p0[0] - p1[0]) / d0
        uy = (p0[1] - p1[1]) / d0
        vx = (p2[0] - p1[0]) / d1
        vy = (p2[1] - p1[1]) / d1
        arcs[i] = ((p1[0] + ux * r, p1[1] + uy * r), p1,
                   (p1[0] + vx * r, p1[1] + vy * r))

    pts = []

    def push(x, y, s):
        if pts and abs(x - pts[-1][0]) < 1e-9 and abs(y - pts[-1][1]) < 1e-9:
            return
        pts.append((x, y, s))

    # 起点：段0 的起点
    seg0_start = arcs[0][2] if 0 in arcs else corners[0]
    push(seg0_start[0], seg0_start[1], cs[0])

    for i in range(n - 1):
        s0, s1 = cs[i], cs[i + 1]
        # 段 i 的实际起止（可能被相邻圆弧裁短）
        if i in arcs:
            A_i, ctrl_i, B_i = arcs[i]
            start = B_i
        else:
            start = corners[i]
        if (i + 1) in arcs:
            A_next = arcs[i + 1][0]
            end = A_next
        else:
            end = corners[i + 1]

        # 直线段
        seg_len = math.hypot(end[0] - start[0], end[1] - start[1])
        nsteps = max(2, int(seg_len / 0.035))
        for k in range(1, nsteps + 1):
            t = k / float(nsteps)
            push(start[0] + (end[0] - start[0]) * t,
                 start[1] + (end[1] - start[1]) * t,
                 s0 + (s1 - s0) * t)

        # 段末尾的圆弧（拐角 i+1）
        if (i + 1) in arcs:
            A, ctrl, Bp = arcs[i + 1]
            for k in range(1, corner_seg + 1):
                t = k / float(corner_seg)
                mt = 1.0 - t
                x = mt * mt * A[0] + 2 * mt * t * ctrl[0] + t * t * Bp[0]
                y = mt * mt * A[1] + 2 * mt * t * ctrl[1] + t * t * Bp[1]
                push(x, y, 0.0)      # s 稍后按实际弧长统一计算
    # ---- s 按【实际弧长】归一化 ----
    # 【v18 修正】早期用原始折线的参数 s，圆弧处会与直线段对不上，
    # 导致断面参数（高度/厚度）在拐角处插值错位。
    # 现在统一按真实弧长算 s —— 与断面状态锚点（STATES）的物理位置一致。
    al = arc_len_param([(p[0], p[1]) for p in pts])
    total = max(1e-9, al[-1])
    pts = [(p[0], p[1], al[i] / total) for i, p in enumerate(pts)]
    return pts


def arc_len_param(pts):
    """返回每个路径点的累计弧长（米）"""
    out = [0.0]
    for i in range(1, len(pts)):
        d = math.hypot(pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1])
        out.append(out[-1] + d)
    return out


# =====================================================================
# 2. 断面：圆角多边形 + 等弧长重采样
# =====================================================================
def _fillet_polygon(corners, radii):
    """把带圆角半径的凸多边形转成【圆角化后的折线点列】。

    corners : [(a, b, r), ...]  闭合多边形的顶点（逆时针）
    返回    : [(a, b), ...]  去掉直边内部点后的"折点 + 圆弧采样"
    """
    n = len(corners)
    out = []
    for i in range(n):
        c = corners[i]
        p = corners[(i - 1) % n]
        q = corners[(i + 1) % n]
        ca = (c[0], c[1])
        va = (p[0] - ca[0], p[1] - ca[1])
        vb = (q[0] - ca[0], q[1] - ca[1])
        la = math.hypot(*va)
        lb = math.hypot(*vb)
        if la < 1e-9 or lb < 1e-9:
            out.append(ca)
            continue
        ua = (va[0] / la, va[1] / la)
        ub = (vb[0] / lb, vb[1] / lb)
        cosang = max(-1.0, min(1.0, ua[0] * ub[0] + ua[1] * ub[1]))
        ang = math.acos(cosang)
        if ang < 1e-3 or abs(math.pi - ang) < 1e-3:
            out.append(ca)
            continue
        r = min(c[2], la * 0.42, lb * 0.42)
        t = r / math.tan(ang / 2.0)
        t = min(t, la * 0.45, lb * 0.45)
        r = t * math.tan(ang / 2.0)
        A = (ca[0] + ua[0] * t, ca[1] + ua[1] * t)
        Bp = (ca[0] + ub[0] * t, ca[1] + ub[1] * t)
        # 圆弧：从 A 绕 C 到 Bp，走【内侧】短弧
        a0 = math.atan2(A[1] - ca[1], A[0] - ca[0])
        a1 = math.atan2(Bp[1] - ca[1], Bp[0] - ca[0])
        da = a1 - a0
        while da <= -math.pi:
            da += 2 * math.pi
        while da > math.pi:
            da -= 2 * math.pi
        steps = max(2, int(abs(da) / (math.pi / 8)) + 1)
        for k in range(steps + 1):
            a = a0 + da * k / steps
            out.append((ca[0] + r * math.cos(a), ca[1] + r * math.sin(a)))
    return out


def resample_closed(poly, n):
    """闭合折线按弧长等距重采样为 n 个点"""
    m = len(poly)
    segs = []
    total = 0.0
    for i in range(m):
        a = poly[i]
        b = poly[(i + 1) % m]
        d = math.hypot(b[0] - a[0], b[1] - a[1])
        segs.append(d)
        total += d
    if total <= 1e-12:
        raise ValueError("degenerate polygon")
    out = []
    step = total / n
    acc = 0.0
    si = 0
    used = 0.0
    for k in range(n):
        target = k * step
        while si < m and used + segs[si] < target - 1e-12:
            used += segs[si]
            si += 1
        si = si % m
        a = poly[si]
        b = poly[(si + 1) % m]
        rem = segs[si] if segs[si] > 1e-12 else 1e-12
        t = min(1.0, max(0.0, (target - used) / rem))
        out.append((a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t))
    return out


def profile_section(T, z_bot, z_wall, z_top, radii=None, n=N_SEC):
    """软包实体断面（2D，a ≤ 0 向内进深，b = 世界高度）。

    轮廓（逆时针）：
        (0, z_bot) → (-T, z_bot) → (-T, z_wall) → (-T, z_top) → (0, z_top)
    z_wall 是【内侧立面】的顶端：扶手段 z_wall=0.39、z_top=0.49，
    两点之间那 100mm 就是扶手内侧的立面；靠背段 z_wall≈z_top，退化成竖板。
    """
    z_wall = min(z_wall, z_top - 0.006)
    z_wall = max(z_wall, z_bot + 0.004)
    if radii is None:
        radii = (0.008, 0.012, 0.018, 0.022, 0.016)
    corners = [
        (0.0, z_bot, radii[0]),
        (-T, z_bot, radii[1]),
        (-T, z_wall, radii[2]),
        (-T, z_top, radii[3]),
        (0.0, z_top, radii[4]),
    ]
    poly = _fillet_polygon(corners, [c[2] for c in corners])
    return resample_closed(poly, n)


def box_section(T, z_bot, z_top, r=0.010, n=N_SEC):
    """直边圆角矩形断面（用于底座框这类硬结构）"""
    return profile_section(T, z_bot, z_top, z_top - 0.004,
                           radii=(r, r, r, r, r), n=n)


# =====================================================================
# 3. 壳体生成
# =====================================================================
def _interp_states(states, s):
    """states: [(s, T, z_bot, z_wall, z_top), ...]  s 递增；各字段平滑插值"""
    if s <= states[0][0]:
        return states[0][1:]
    if s >= states[-1][0]:
        return states[-1][1:]
    for i in range(len(states) - 1):
        s0 = states[i][0]
        s1 = states[i + 1][0]
        if s0 <= s <= s1:
            f = 0.0 if s1 - s0 < 1e-12 else (s - s0) / (s1 - s0)
            f = f * f * (3 - 2 * f)      # smoothstep → 斜肩无折角
            a = states[i][1:]
            b = states[i + 1][1:]
            return tuple(a[k] + (b[k] - a[k]) * f for k in range(len(a)))
    return states[-1][1:]


def build_shell(name, path, states, material, cap_len=0.055, uv=True,
                section_fn=None, end_scale=1.0):
    """沿轮廓路径扫掠【可变断面】 → 连续软包实体。

    path    : [(x, y, s), ...]
    states  : [(s, T, z_bot, z_wall, z_top), ...]  断面参数
    cap_len : 端头收缩长度（米）—— 末端断面略收，模拟扶手前端包边收口
    """
    P = len(path)
    if P < 3:
        raise ValueError("path too short")
    al = arc_len_param([(p[0], p[1]) for p in path])
    L = al[-1]
    if L <= 1e-6:
        raise ValueError("degenerate path")

    # 每个路径点的断面参数
    params = []
    for i in range(P):
        T, zb, zw, zt = _interp_states(states, path[i][2])
        if cap_len > 1e-6:
            d = min(al[i], L - al[i])
            if d < cap_len:
                u = d / cap_len
                k = math.sqrt(max(0.0, 1.0 - (1.0 - u) ** 2))
                cz = (zb + zt) * 0.5
                hh = (zt - zb) * 0.5
                T *= (0.90 + 0.10 * k)
                zb = cz - hh * (0.94 + 0.06 * k)
                zt = cz + hh * (0.94 + 0.06 * k)
        # 端头整体略收（扶手前端的收口）
        if end_scale != 1.0:
            d = min(al[i], L - al[i])
            if d < 0.012:
                k = d / 0.012
                T *= (end_scale + (1 - end_scale) * k)
        params.append((T, zb, zw, zt))

    # 切向 + 内法向
    frames = []
    for i in range(P):
        if i == 0:
            tx = path[1][0] - path[0][0]
            ty = path[1][1] - path[0][1]
        elif i == P - 1:
            tx = path[-1][0] - path[-2][0]
            ty = path[-1][1] - path[-2][1]
        else:
            tx = path[i + 1][0] - path[i - 1][0]
            ty = path[i + 1][1] - path[i - 1][1]
        tl = math.hypot(tx, ty)
        if tl < 1e-12:
            tx, ty, tl = 1.0, 0.0, 1.0
        tx /= tl
        ty /= tl
        # 【方向约定 · v18 最终修正】
        # 路径：左扶手前 → 左扶手后 → 右扶手后 → 右扶手前
        #   · 靠背段：切向 +X，内侧（朝座位）= +Y
        #   · 左扶手段：切向 -Y，内侧（朝中心）= +X
        # 两者都满足【右法向 n = (ty, -tx)】：
        #   靠背段 (ty,-tx) = (0,-1) → 实体从 y=-0.42 长到 y=-0.29 ✓（朝座位）
        #   左扶手段 (ty,-tx) = (-1,0) → 实体从 x=-1.12 长到 x=-0.899 ✓（朝中心）
        # 断面里 a ≤ 0 表示"向内进深"，与右法向配合后实体正好朝内生长。
        #
        # 【踩坑记录】中途误试左法向 (-ty,tx)：实体朝外长，
        # 沙发宽度从 2.24 涨到 2.68（实测 bbox x[-1.342, 1.342]），已回退。
        frames.append((tx, ty, ty, -tx))

    # 顶点
    verts = []
    sects = []
    sf = section_fn or (lambda T, zb, zw, zt: profile_section(T, zb, zw, zt))
    for i in range(P):
        T, zb, zw, zt = params[i]
        sec = sf(T, zb, zw, zt)
        # 【v18】断面点序【保持】profile_section 给出的逆时针序。
        # 内法向改成右法向 (ty,-tx) 后，法线朝向由【侧壁面绕序】决定，
        # 与断面点序无关 —— 所以这里不动点序，只在下面反转侧壁绕序。
        sects.append(sec)
        _, _, nx, ny = frames[i]
        px, py = path[i][0], path[i][1]
        for (a, b) in sec:
            verts.append((px + nx * a, py + ny * a, b))

    faces = []
    for i in range(P - 1):
        for j in range(N_SEC):
            j2 = (j + 1) % N_SEC
            # 内法向 = 右法向 (ty,-tx) 时，侧壁绕序需反向才对应"法线朝外"
            # （实测：绕序不反 → 整片侧壁法线朝内 → 背面剔除 →
            #   从外面只看见靠背顶边与扶手端盖的"细条"）。
            faces.append((i * N_SEC + j, (i + 1) * N_SEC + j,
                          (i + 1) * N_SEC + j2, i * N_SEC + j2))

    # 端盖：用断面多边形扇形三角化（断面是凸的）
    def cap(i, flip):
        sec = sects[i]
        _, _, nx, ny = frames[i]
        px, py = path[i][0], path[i][1]
        ca = sum(p[0] for p in sec) / len(sec)
        cb = sum(p[1] for p in sec) / len(sec)
        base = len(verts)
        verts.append((px + nx * ca, py + ny * ca, cb))
        for (a, b) in sec:
            verts.append((px + nx * a, py + ny * a, b))
        for j in range(len(sec)):
            j2 = (j + 1) % len(sec)
            if flip:
                faces.append((base, base + 1 + j, base + 1 + j2))
            else:
                faces.append((base, base + 1 + j2, base + 1 + j))

    cap(0, True)
    cap(P - 1, False)

    me = bpy.data.meshes.new(name + "_me")
    me.from_pydata(verts, [], faces)
    me.update()
    for p in me.polygons:
        p.use_smooth = True
    ob = bpy.data.objects.new(name, me)
    B.link(ob)
    if material is not None:
        ob.data.materials.append(material)
    ob.location = (0, 0, 0)
    # 【v18 关键修正 · 不再调用 recalc_normals】
    # recalc_face_normals 对【开口的 U 形壳体】无法判断"朝外"该朝哪边，
    # 会把已经正确的绕序重新翻掉 —— 实测：加了 recalc 后，
    # 背板朝向座位的那一面（法线应指向 +Y）被翻成 -Y，
    # 实体着色背面剔除 → 从正面看进去整片空心，只剩深色内部。
    # 现在改为完全依赖 build_shell 里显式设置的绕序（侧壁 + 端盖已配对反向）。
    _ensure_outward(ob)

    if uv:
        uvl = me.uv_layers.new(name="UVMap")
        for poly in me.polygons:
            for li in poly.loop_indices:
                vi = me.loops[li].vertex_index
                if vi < P * N_SEC:
                    i = vi // N_SEC
                    j = vi % N_SEC
                    uvl.data[li].uv = (al[i] / L * 6.0, j / float(N_SEC))
                else:
                    uvl.data[li].uv = (0.5, 0.5)
    return ob, params, sects, frames


def _ensure_outward(ob):
    """保证法线整体朝外（自动纠正，替代人工推理断面绕序）

    【为什么需要】
    扫掠体的法线朝向取决于【断面点绕序】与【路径内法向方向】的组合。
    这两个只要有一个被改动（比如把内法向从左法向换成右法向），
    整片侧壁的法线就会朝内 —— 实体着色下背面剔除，
    从外面看模型只剩深色内部（实测 v18：shell 16512 面里 5995 面朝内）。

    【判据：散度定理的有向体积】
    V = (1/6) Σ_tri (a × b) · c   （a,b,c 为三角形三个顶点）
    闭合曲面法线一致朝外 → V > 0；朝内 → V < 0。
    比"离中心距离"判据可靠得多：外壳是【U 形中空】体，
    几何中心落在空腔里，用中心距离判断必然出错（实测踩坑）。

    【判据：外侧面的法线必须朝外】
    沙发壳体的形状是【U 形开口】：靠背在 -Y，两扶手在 ±X。
    有向体积对开口体不可靠（≈0），"离中心距离"也误判
    （几何中心落在空腔里，扶手【内侧立面】本就该朝内，会被误判为"翻转"）。
    唯一无歧义的判据：【扶手外侧面】—— |x| 最大的那些面，
    它们的法线必须指向 ±X 的外侧（与该面顶点 x 的符号一致）。
    这条判据与"内/外"定义直接对应，零歧义。
    """
    import mathutils
    me = ob.data
    if not me.polygons:
        return ob

    # 找 |x| 最大的顶点集合
    max_abs_x = 0.0
    for v in me.vertices:
        max_abs_x = max(max_abs_x, abs(v.co.x))
    if max_abs_x < 1e-6:
        return ob

    agree = 0
    disagree = 0
    for p in me.polygons:
        vs = [me.vertices[i].co for i in p.vertices]
        if not vs:
            continue
        mx = sum(v.x for v in vs) / len(vs)
        if abs(mx) < max_abs_x - 0.010:
            continue          # 只看最外侧那 10mm 的一圈
        # 该面的法线 x 分量应与面所在侧的 x 符号一致
        if mx * p.normal.x > 0:
            agree += 1
        else:
            disagree += 1

    if disagree > agree:
        import bmesh
        bm = bmesh.new()
        bm.from_mesh(me)
        bmesh.ops.reverse_faces(bm, faces=bm.faces)
        bm.to_mesh(me)
        bm.free()
        me.update()
        print("[sofa_shell] flipped faces (outer sides were inward): "
              "agree=%d disagree=%d" % (agree, disagree))

    # 【v23 · 底面朝向修正】
    # 实测（diag_seam_rev.py）：shell 有 130 处法线反向，
    # 全部集中在 z ≈ 0.145（= 壳体最低点 z_bot）那一圈底面带。
    # 原因：_ensure_outward 只用"扶手外侧面"判据（|x| 最大的那圈），
    # 底面不在判据范围内 → 底面的绕序若与侧壁相反就会反向。
    #
    # 补一个判据：找出【最低的一圈顶点】（z 接近 z_min），
    # 它们的法线必须朝下（z 分量 < 0）。若相反则翻转该批面。
    import bmesh
    zmin = min(v.co.z for v in me.vertices)
    zmax = max(v.co.z for v in me.vertices)
    band = zmax - zmin
    if band > 1e-6:
        thr = zmin + band * 0.02
        bot_faces = []
        for p in me.polygons:
            zs = [me.vertices[i].co.z for i in p.vertices]
            if max(zs) <= thr:
                bot_faces.append(p)
        if bot_faces:
            up = sum(1 for p in bot_faces if p.normal.z > 0)
            down = len(bot_faces) - up
            if up > down:
                bm = bmesh.new()
                bm.from_mesh(me)
                bmesh.ops.reverse_faces(
                    bm, faces=[bm.faces[p.index] for p in bot_faces])
                bm.to_mesh(me)
                bm.free()
                me.update()
                print("[sofa_shell] flipped bottom faces (were up): "
                      "up=%d down=%d" % (up, down))
    return ob


def recalc_normals(ob):
    """重算法线（扫掠体的绕序不一定一致，统一朝外）"""
    import bmesh
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(ob.data)
    bm.free()
    ob.data.update()
    return ob


# =====================================================================
# 4. 端头包边（扶手前端的滚边，沿断面轮廓走）
# =====================================================================
def cap_welt_points(path_pt, normal, sec, inset=0.004, z_shift=0.0):
    """端盖断面轮廓的滚边路径点（世界坐标）"""
    pts = []
    cx = sum(p[0] for p in sec) / len(sec)
    cz = sum(p[1] for p in sec) / len(sec)
    for (a, b) in sec:
        dx = a - cx
        dz = b - cz
        k = math.hypot(dx, dz)
        if k > 1e-9:
            a -= dx / k * inset
            b -= dz / k * inset
        pts.append((path_pt[0] + normal[0] * a,
                    path_pt[1] + normal[1] * a,
                    b + z_shift))
    pts.append(pts[0])
    return pts


# =====================================================================
# 5. 布料松弛褶皱
# =====================================================================
def _vnoise3(x, y, z, seed=0):
    """3D 值噪声（三线性插值的 hash 噪声）—— 各向同性。

    【为什么要自己写】
    之前 cloth_relax 用 sin 的线性组合，其中有一项是
    `sin(v.co.z * freq * 3.3)` —— 只依赖 z。
    在靠背/扶手这类【竖直面】上，它就变成一排排水平条纹，
    渲染出来像瓦楞板/抽屉拉手（实测 v19 渲染图上非常明显）。
    换成各向同性的 3D 值噪声后，褶皱在各个方向上分布均匀。
    """
    def _h(i, j, k):
        n = (i * 374761393 + j * 668265263 + k * 2147483647
             + seed * 1274126177) & 0xFFFFFFFF
        n = (n ^ (n >> 13)) * 1274126177 & 0xFFFFFFFF
        n = n ^ (n >> 16)
        return (n & 0xFFFFFF) / 0xFFFFFF * 2.0 - 1.0

    xi, yi, zi = math.floor(x), math.floor(y), math.floor(z)
    xf, yf, zf = x - xi, y - yi, z - zi
    u = xf * xf * (3 - 2 * xf)
    v = yf * yf * (3 - 2 * yf)
    w = zf * zf * (3 - 2 * zf)
    c000 = _h(int(xi), int(yi), int(zi))
    c100 = _h(int(xi) + 1, int(yi), int(zi))
    c010 = _h(int(xi), int(yi) + 1, int(zi))
    c110 = _h(int(xi) + 1, int(yi) + 1, int(zi))
    c001 = _h(int(xi), int(yi), int(zi) + 1)
    c101 = _h(int(xi) + 1, int(yi), int(zi) + 1)
    c011 = _h(int(xi), int(yi) + 1, int(zi) + 1)
    c111 = _h(int(xi) + 1, int(yi) + 1, int(zi) + 1)
    x00 = c000 + (c100 - c000) * u
    x10 = c010 + (c110 - c010) * u
    x01 = c001 + (c101 - c001) * u
    x11 = c011 + (c111 - c011) * u
    y0 = x00 + (x10 - x00) * v
    y1 = x01 + (x11 - x01) * v
    return y0 + (y1 - y0) * w


def cloth_relax(o, amp=0.0045, freq=13.0, seed=0, edge_bias=0.55,
                down_weight=0.35, center=None, radial=None):
    """沿法线方向的【各向同性】噪声 —— 模拟布料被坐压后的松弛。

    center / radial（软包顶面用）：
      真实坐垫【顶面中央是平整的】（被压实了），褶皱集中在边缘和侧壁。
      传入后 w 再乘一个"离中心越远越皱"的因子，
      否则顶面会出现整条整条的深沟（实测 v16 渲染出来像抽屉拉手）。

    【v19】改用 3D 值噪声（各向同性）。
      旧实现是 sin 的线性组合，含 `sin(z * freq * 3.3)` 这种只依赖 z 的项，
      在竖直面上形成规则水平条纹（渲染图上像瓦楞板）。
    """
    nrm = [v.normal.copy() for v in o.data.vertices]
    zmin = min(v.co.z for v in o.data.vertices)
    zmax = max(v.co.z for v in o.data.vertices)
    span = max(1e-6, zmax - zmin)

    for i, v in enumerate(o.data.vertices):
        t = (v.co.z - zmin) / span
        w = down_weight + (1.0 - down_weight) * t
        if center is not None and radial is not None:
            rr = min(1.0, math.hypot((v.co.x - center[0]) / radial[0],
                                      (v.co.y - center[1]) / radial[1]))
            w *= (1.0 - edge_bias + edge_bias * rr)
        # 三个不同尺度的各向同性噪声叠加：大褶 + 中褶 + 细褶
        d = _vnoise3(v.co.x * freq, v.co.y * freq, v.co.z * freq, seed) * 1.0
        d += _vnoise3(v.co.x * freq * 2.3, v.co.y * freq * 2.3,
                      v.co.z * freq * 2.3, seed + 17) * 0.45
        d += _vnoise3(v.co.x * freq * 5.1, v.co.y * freq * 5.1,
                      v.co.z * freq * 5.1, seed + 53) * 0.22
        v.co += nrm[i] * (d * amp * w)

    o.data.update()
    return o

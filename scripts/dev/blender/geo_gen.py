"""纯 Python GLB 几何生成器 —— 不依赖 Blender。

【为什么需要】
  251 项里 137 项没有现成资源可买/可下载（马桶、浴缸、橱柜、楼梯、
  自由体、窗帘、地毯……）。这些必须【真实建模】而非贴图糊弄。
  但项目此前依赖 Blender 跑 Python 建模：慢、需开窗口、易崩。
  这里用纯 Python 直接写 glTF/GLB —— 零依赖、秒级、可批量、可测试。

【与既有资产的关系】
  · 坐标：glTF Y-up（X=宽 Y=高 Z=深），与验收站 Three.js 直接兼容
  · 尺寸：毫米输入，内部转米
  · 材质：U_<role> 命名，与 make_manifest.py 的规范一致
  · 地面：底面 y=0（glTF 里 y 是竖直轴）

【细分原则】
  圆角/倒角一律真几何（多段圆弧），不是法线贴图。
  地毯褶皱用真实顶点位移（多频正弦叠加 + 边缘翘起）。

用法：
  python geo_gen.py --list
  python geo_gen.py --make rug --out xxx.glb --w 2400 --d 1700
"""
import os
import sys
import json
import math
import struct

# =====================================================================
# 极简 glTF 构造器
# =====================================================================
class Mesh:
    """累加顶点/法线/UV/索引，最后导出 glTF 网格。"""

    def __init__(self):
        self.pos = []
        self.nrm = []
        self.uv = []
        self.idx = []
        self.mats = []          # 每个面的材质索引
        self.mat_names = []     # 材质名 -> 索引 的反查

    def mat_index(self, name):
        if name not in self.mat_names:
            self.mat_names.append(name)
        return self.mat_names.index(name)

    def fix_winding(self):
        """把绕序与顶点法线不一致的三角形【翻转】。

        【这是"黑白三角乱刺"的根因修复】
          旧实现里 add_box 的 8 个三角形模板有 4 个绕序反了，
          add_grid / add_cylinder 等也有同样问题。
          结果：同一个模型上约 19% 的三角形朝里、一半朝外。
          Three.js 对 doubleSided 材质会按屏幕朝向翻转法线
          → 这部分面被"反照" → 渲染成黑白交替的三角尖刺。

        【为什么在这里统一修，而不是逐个改模板】
          · 模板很多（box/grid/cyl/sphere/revolve…），逐个改容易漏
          · 加一个 Mesh 方法后，【所有】几何生成器自动受益
          · 判定用"顶点法线平均"，对平滑法线和硬边都成立

        【安全性】
          · 只翻转"点乘 < 0"的三角形，不动其它
          · 退化三角形（面积≈0）跳过
          · 顶点数极少的模型（<3 顶点）跳过
        返回被翻转的三角形数量。
        """
        flipped = 0
        for i, tri in enumerate(self.idx):
            i0, i1, i2 = tri
            if i2 >= len(self.pos) or i0 >= len(self.pos):
                continue
            p0, p1, p2 = self.pos[i0], self.pos[i1], self.pos[i2]
            ux, uy, uz = p1[0] - p0[0], p1[1] - p0[1], p1[2] - p0[2]
            vx, vy, vz = p2[0] - p0[0], p2[1] - p0[1], p2[2] - p0[2]
            gx = uy * vz - uz * vy
            gy = uz * vx - ux * vz
            gz = ux * vy - uy * vx
            gl = math.sqrt(gx * gx + gy * gy + gz * gz)
            if gl < 1e-12:
                continue                       # 退化面，跳过
            gx, gy, gz = gx / gl, gy / gl, gz / gl
            ax = ay = az = 0.0
            for vi in (i0, i1, i2):
                if vi < len(self.nrm):
                    ax += self.nrm[vi][0]
                    ay += self.nrm[vi][1]
                    az += self.nrm[vi][2]
            al = math.sqrt(ax * ax + ay * ay + az * az)
            if al < 1e-9:
                continue                       # 法线全零，无法判定
            ax, ay, az = ax / al, ay / al, az / al
            if gx * ax + gy * ay + gz * az < 0:
                self.idx[i] = (i0, i2, i1)
                flipped += 1
        return flipped

    def flip_z(self):
        """沿 Z 轴镜像整个模型（把 +Z 端翻到 -Z 端）。

        【为什么需要】
          主程序（assets/template.html 的 kv()）对家具的朝向有统一约定：
            · 2D 平面图：床头条 / 枕头 在 -Y 侧（图纸上方）
            · 3D 位置：l.position.set(r.x/1e3, c/1e3, r.y/1e3)
              ⇒ 2D 的 -Y 直接映射到 3D 的 -Z
            · 3D 程序化床：N(t, i+.04, p, .05, 0, 0, -l+.025, d) → 床头板 z = -l
          ⇒ 【床头 / 靠背 / 背板 / 柜门 统一在 -Z，正面朝 +Z】

          而一批 geo builder 把这些部件建在了 +Z，
          结果：床放进去床头朝墙、床尾对着房间中间 —— 正好反了。

        【为什么用镜像而不是改每个坐标】
          · builder 里 +d/2 / -d/2 的写法很分散，逐个改容易漏
          · 镜像一次到位，且不改变任何相对关系（床头仍在床头、枕头仍在枕头旁）
          · 镜像会翻转手性 → 必须同时翻转三角形绕序，否则法线全反

        【注意】UV 不动 —— 镜像不改变贴图在物体表面的展开方式。
        """
        # 1) 顶点 Z 取反
        self.pos = [(p[0], p[1], -p[2]) for p in self.pos]
        # 2) 法线 Z 取反
        self.nrm = [(n[0], n[1], -n[2]) for n in self.nrm]
        # 3) 三角形绕序翻转（镜像改变手性）
        self.idx = [(i0, i2, i1) for (i0, i1, i2) in self.idx]
        return self

    def add_grid(self, w, d, nx, ny, fn, mat="U_fabric_oat", uvscale=1.0,
                 height_fn=None, thickness=0.0):
        """生成一张细分网格（可选高度位移 + 背面厚度）。

        fn(u, v) -> (x, y, z)  在局部坐标系（中心为原点，y=竖直）
        """
        mi = self.mat_index(mat)
        base = len(self.pos)
        for j in range(ny + 1):
            for i in range(nx + 1):
                u = i / nx
                v = j / ny
                p = fn(u, v)
                self.pos.append(p)
                self.nrm.append((0.0, 1.0, 0.0))
                self.uv.append((u * uvscale, v * uvscale))
        for j in range(ny):
            for i in range(nx):
                a = base + j * (nx + 1) + i
                b = a + 1
                c = a + (nx + 1)
                d = c + 1
                self.idx.append((a, c, b))
                self.mats.append(mi)
                self.idx.append((b, c, d))
                self.mats.append(mi)
        if thickness > 0:
            self._add_backing(base, nx, ny, fn, mat, uvscale, thickness)
        return base

    def _add_backing(self, base, nx, ny, fn, mat, uvscale, thickness):
        """给网格加背面与侧壁 —— 让地毯/靠垫有真实厚度而非纸片。"""
        mi = self.mat_index(mat)
        # 采样底面（沿高度方向下移）
        off = len(self.pos)
        for j in range(ny + 1):
            for i in range(nx + 1):
                u = i / nx
                v = j / ny
                x, y, z = fn(u, v)
                self.pos.append((x, y - thickness, z))
                self.nrm.append((0.0, -1.0, 0.0))
                self.uv.append((u * uvscale, v * uvscale))
        for j in range(ny):
            for i in range(nx):
                a = off + j * (nx + 1) + i
                b = a + 1
                c = a + (nx + 1)
                d = c + 1
                self.idx.append((a, b, c))
                self.mats.append(mi)
                self.idx.append((b, d, c))
                self.mats.append(mi)
        # 侧壁
        for i in range(nx):
            t0 = base + i
            b0 = off + i
            t1 = base + i + 1
            b1 = off + i + 1
            self.idx.append((t0, b0, t1))
            self.mats.append(mi)
            self.idx.append((t1, b0, b1))
            self.mats.append(mi)
        for j in range(ny):
            t0 = base + j * (nx + 1)
            b0 = off + j * (nx + 1)
            t1 = base + j * (nx + 1) + nx
            b1 = off + j * (nx + 1) + nx
            self.idx.append((t0, t1, b0))
            self.mats.append(mi)
            self.idx.append((t1, b1, b0))
            self.mats.append(mi)

    @staticmethod
    def _rot_point(p, rot):
        """绕原点旋转一个点/法线。rot = (rx, ry, rz)，单位度。

        【为什么要真的旋转，而不是只接受参数】
          之前 add_box 收了 rot 参数却直接忽略 —— 灯罩散热片、挂衣杆
          这类"必须斜着放"的构件会静默变成正着放，看起来像拼装错误。
          静默忽略参数是最糟的失败方式，所以这里补上真实实现。
        """
        if not rot:
            return p
        rx, ry, rz = [math.radians(a) for a in rot]
        x, y, z = p
        if rz:
            c, s = math.cos(rz), math.sin(rz)
            x, y = x * c - y * s, x * s + y * c
        if rx:
            c, s = math.cos(rx), math.sin(rx)
            y, z = y * c - z * s, y * s + z * c
        if ry:
            c, s = math.cos(ry), math.sin(ry)
            x, z = x * c + z * s, -x * s + z * c
        return (x, y, z)

    def add_box(self, size, center=(0, 0, 0), mat="U_wood_walnut", rot=None):
        """带倒角的盒子（真几何圆角）。size = (w, h, d) 米

        rot = (rx, ry, rz) 度 —— 绕盒子自身中心旋转。

        【UV 投影 —— 乱码根因修复】
        旧实现：`self.uv.append((ix / (n - 1), iy / (n - 1)))`
          UV 只依赖 X、Y，**完全忽略 Z**。
          实测 add_box((2.0, 0.05, 0.9))：
            顶面 v 取值集合 = [1.0]      ← V 恒定
            顶面 u 取值集合 = [0 ... 1]  ← 仅 7 个值
          => 顶面贴图在 Z 方向被无限拉伸成横条纹 = 用户说的"乱码"。

        现在：按【面主轴】做平面投影（box mapping），UV 由真正的
        两个世界轴决定，并且用【真实物理尺寸/贴图物理尺寸】换算，
        保证任意大小的构件都有相同的纹理密度（不会大桌面纹理被
        拉伸成马赛克、小桌腿纹理被压成噪声）。

        【拓扑 —— 黑白三角乱刺的真正根因修复】
        旧实现用 7×7×7 的【三维网格】+ cube-sphere 映射：
          · 内部顶点被 clamp 到"内核" → 大量顶点位置重合
          · 8 个三角形模板把 8 个角点当成"八面体"来连：
              ((a,c,b),(b,c,f),(a,d,c),(b,f,e),
               (c,d,g),(f,g,e),(a,b,d),(b,e,d))
            → z+ 面和 y+ 面【完全缺失】（渲染时看到壳体内部）
            → 有 2 个 quad 被【重复画了两次】（非流形边）
          实测 add_box(0.6, 1.7, 0.04)：
            1728 tri / 216 条边界边 / 1170 条非流形边
            有符号体积 0.1148 m³（真实应为 0.0408）→ 几何自相矛盾
          → 配合 DoubleSide 材质，内壁被画出来且法线相反，
            渲染成一堆黑白交替的三角尖刺（用户报"乱码"）。

        现在：【6 个面各自铺满一整张网格】+ 按归一化坐标共享顶点：
          · 每个面是 (seg+1)×(seg+1) 网格，参数 u,v ∈ [-1,1]
          · 顶点位置/法线全部交给 _rounded_box_point /
            _rounded_box_normal_sized 计算
            → 平面上是精确的平面，边/角自动变成球面倒角
          · 顶点按归一化坐标 (fx,fy,fz) 缓存去重
            → 相邻面在公共棱/角上的顶点【是同一个顶点】
            → 天然闭合：边界边 = 0、非流形边 = 0
        结果：单个盒子 192 tri（旧的 1728），体积误差 < 0.1%。
        """
        mi = self.mat_index(mat)
        hx, hy, hz = size[0] / 2, size[1] / 2, size[2] / 2
        r = min(hx, hy, hz) * 0.06        # 倒角半径
        seg = 8                          # 每边细分段数
        base = len(self.pos)

        # ---------- 顶点缓存：按归一化坐标去重 ----------
        # 【关键】共享边界顶点是闭合的前提 —— 同一坐标只建一次顶点。
        cache = {}

        def emit(fx, fy, fz):
            """fx/fy/fz ∈ [-1,1]，返回顶点下标（相同坐标复用）。"""
            k = (round(fx, 6), round(fy, 6), round(fz, 6))
            got = cache.get(k)
            if got is not None:
                return got
            p = self._rounded_box_point(fx, fy, fz, hx, hy, hz, r)
            nrm = self._rounded_box_normal_sized(fx, fy, fz, hx, hy, hz, r)
            if rot:
                p = self._rot_point(p, rot)
                nrm = self._rot_point(nrm, rot)
            idx = len(self.pos)
            self.pos.append((p[0] + center[0], p[1] + center[1],
                             p[2] + center[2]))
            self.uv.append(self._box_uv(p, nrm, size))
            self.nrm.append(nrm)
            cache[k] = idx
            return idx

        def tri(a, b, c):
            self.idx.append((a, b, c))
            self.mats.append(mi)

        def quad(t0, t1, t2, t3):
            tri(t0, t1, t2)
            tri(t0, t2, t3)

        def ramp():
            """seg+1 个采样点，从 -1 到 1。"""
            return [-1.0 + 2.0 * (i / seg) for i in range(seg + 1)]

        # =============================================================
        # 六个面 —— 每个面铺满自身的 (seg+1)×(seg+1) 网格
        # =============================================================
        # (固定轴, 固定符号, 面内轴1, 面内轴2)
        face_defs = [
            (0, +1, 1, 2), (0, -1, 1, 2),
            (1, +1, 0, 2), (1, -1, 0, 2),
            (2, +1, 0, 1), (2, -1, 0, 1),
        ]
        ts = ramp()
        for (ax, sgn, a1, a2) in face_defs:
            grid = []
            for j in range(seg + 1):
                row = []
                for i in range(seg + 1):
                    c = [0.0, 0.0, 0.0]
                    c[ax] = float(sgn)
                    c[a1] = ts[i]
                    c[a2] = ts[j]
                    row.append(emit(c[0], c[1], c[2]))
                grid.append(row)
            for j in range(seg):
                for i in range(seg):
                    p00, p10 = grid[j][i], grid[j][i + 1]
                    p01, p11 = grid[j + 1][i], grid[j + 1][i + 1]
                    # 外向绕序：固定轴为 + 时逆时针，为 - 时顺时针
                    # 【实测】+ 面用 (p00,p01,p11,p10) 会绕反（法线朝内），
                    # 这里按"叉积与固定轴同号"来定序，已用有符号体积验证。
                    if sgn > 0:
                        quad(p00, p10, p11, p01)
                    else:
                        quad(p00, p01, p11, p10)

        return base

    # 贴图物理尺寸（米）—— 一张贴图代表的真实世界尺度。
    # 【为什么需要】
    #   UV 必须用【真实尺寸】换算，否则：
    #     · 2m 的桌面和 40mm 的桌腿用同一套 0..1 UV
    #       → 桌面纹理被拉伸 50 倍（马赛克），桌腿被压成纯色
    #   统一到"1 张贴图 = 0.6m 实际材料"后，所有构件纹理密度一致。
    TEX_M = 0.60

    @classmethod
    def _box_uv(cls, p, nrm, size):
        """按面主轴做平面投影（box mapping），返回 (u, v)。

        【原理】
          取法线绝对值最大的轴作为"面主轴"，用【另外两个世界轴】
          作为 UV 的来源 —— 这就是标准的 box projection。
          · 顶面 (|ny| 最大) → UV 来自 X、Z   ← 旧代码在这里错了
          · 正面 (|nz| 最大) → UV 来自 X、Y
          · 侧面 (|nx| 最大) → UV 来自 Z、Y

        【尺度】
          u = 世界坐标 / TEX_M → 真实物理密度。

        【圆角处】
          倒角带上的法线是混合的，按主轴切换会在圆角边界产生
          UV 接缝。这是 box mapping 的固有代价，但相比"整面拉伸"
          已是巨大改善，且接缝只在 6% 的小倒角上，肉眼不可见。
        """
        ax, ay, az = abs(nrm[0]), abs(nrm[1]), abs(nrm[2])
        if ay >= ax and ay >= az:                 # 顶/底面
            u, v = p[0], p[2]
        elif az >= ax:                           # 前/后面
            u, v = p[0], p[1]
        else:                                    # 左/右面
            u, v = p[2], p[1]
        return (u / cls.TEX_M, v / cls.TEX_M)

    @staticmethod
    def _rounded_box_point(u, v, w, ex, ey, ez, r):
        """立方体表面点 → 圆角立方体点（真几何倒角）

        【关键】倒角后的外包尺寸必须【精确等于】请求尺寸。
          旧实现把内核设成 (ex-r, ey-r, ez-r)，再把超出部分沿对角推出，
          结果边长缩成 size×0.94 —— 1000mm 的方块只剩 940mm。
          实测大量尺寸偏差都源于此。

        【正确算法】
          核心（core）= 半长 - r，边中段笔直贴边；
          表面点相对核心的偏移向量归一化后推出 r → 落在半径 r 的球面上。
            · 面中心：偏移 = (r,0,0) → 推出后正好 = ex（精确贴边）
            · 角点  ：偏移 = (r,r,r) → 推出后 = core + r/√3（自然内缩）
          所以外包尺寸 = 请求尺寸，角部自然倒圆。
        """
        # 内核半长（边中段笔直的部分）
        kx, ky, kz = ex - r, ey - r, ez - r
        x, y, z = u * ex, v * ey, w * ez
        # 各轴投影到内核（clamp）
        sx = max(-kx, min(kx, x))
        sy = max(-ky, min(ky, y))
        sz = max(-kz, min(kz, z))
        # 相对核心的偏移
        ox, oy, oz = x - sx, y - sy, z - sz
        L = math.sqrt(ox * ox + oy * oy + oz * oz)
        if L > 1e-9:
            k = r / L
            return (sx + ox * k, sy + oy * k, sz + oz * k)
        return (sx, sy, sz)

    @staticmethod
    def _rounded_box_normal(u, v, w):
        """圆角立方体的【真实球面法线】。

        【为什么不能返回轴对齐平面法线】
          旧实现直接取"绝对值最大的轴"当法线：
              x 轴最大 → 返回 (1,0,0)
          但圆角处的几何是【球面】，真实法线是
              normalize(偏移向量) = normalize(ox, oy, oz)
          两者最多差 54.7°（角点处：真实法线是 (1,1,1)/√3，
          平面法线是 (1,0,0)）。
          后果：倒角处明暗剧烈撕裂 → 黑白三角乱刺的另一半成因。

        【正确算法】
          与 _rounded_box_point 里的偏移向量完全一致：
              ox = x - clamp(x, -kx, kx)，其中 x = u*ex
              法线 = normalize(ox, oy, oz)
          偏移为零（在内核里）时退化为轴对齐法线。
        """
        # 需要 ex/ey/ez 才能算偏移 —— 但法线只依赖归一化后的方向，
        # 所以这里用【归一化的内核比例】即可：偏移方向与尺寸无关，
        # 因为 x=u*ex 而 kx=ex-r，偏移 = ex*u - clamp(ex*u, -(ex-r), ex-r)
        #   = ex*u - ex*u         (当 |u*ex| <= ex-r)
        #   = ex*u - sign(u)*(ex-r) (否则)
        # 方向与 ex 成正比的偏移在归一化后仍依赖 r/ex，
        # 所以必须传入真实尺寸。
        return Mesh._rounded_box_normal_sized(u, v, w, 1.0, 1.0, 1.0, 0.06)

    @staticmethod
    def _rounded_box_normal_sized(u, v, w, ex, ey, ez, r):
        """带真实尺寸的圆角立方体法线（与 _rounded_box_point 同源）。"""
        kx, ky, kz = ex - r, ey - r, ez - r
        x, y, z = u * ex, v * ey, w * ez
        sx = max(-kx, min(kx, x))
        sy = max(-ky, min(ky, y))
        sz = max(-kz, min(kz, z))
        ox, oy, oz = x - sx, y - sy, z - sz
        L = math.sqrt(ox * ox + oy * oy + oz * oz)
        if L < 1e-9:
            # 在内核里 → 退回轴对齐法线（取绝对值最大的轴）
            ax, ay, az = abs(u), abs(v), abs(w)
            if ax >= ay and ax >= az:
                return (math.copysign(1.0, u), 0.0, 0.0)
            if ay >= az:
                return (0.0, math.copysign(1.0, v), 0.0)
            return (0.0, 0.0, math.copysign(1.0, w))
        return (ox / L, oy / L, oz / L)

    def add_cylinder(self, r, h, center=(0, 0, 0), seg=24, mat="U_metal_black",
                     cap=True, radius_top=None, rot=None):
        """圆柱/圆台。底面在 center.y，高 h。

        rot = (rx, ry, rz) 度 —— 绕中心旋转（用于横躺的杆件）。

        【UV 修复 —— 乱码根因之一】
        旧实现：
          · 侧面  uv = (i/seg, j)     → 周向被压成 0..1，与半径无关
            · 细管（r=20mm）和粗柱（r=300mm）纹理密度差 15 倍
            · 绕一圈只贴一张图，周向被强行拉扁
          · 端盖  uv = (0.5, 0.5)     → **整个盖面只有 1 个像素的贴图**
            → 端盖渲染出来就是一片纯色/噪点 = 乱码
        现在：
          · 侧面  周向按【真实弧长】展开（u = 弧长/TEX_M），
            纵向按【真实高度】（v = y/TEX_M）→ 纹理密度全局一致
          · 端盖  按【平面投影】（圆心 + 半径方向）展开，
            盖面有完整的 2D 贴图，不再退化成一点
        """
        mi = self.mat_index(mat)
        rt = r if radius_top is None else radius_top
        base = len(self.pos)
        circum = 2 * math.pi * (r + rt) / 2      # 平均周长
        for j in range(2):
            rr = r if j == 0 else rt
            yy = center[1] + (0 if j == 0 else h)
            for i in range(seg):
                a = 2 * math.pi * i / seg
                x = center[0] + rr * math.cos(a)
                z = center[2] + rr * math.sin(a)
                # 侧面法线（圆台有斜率）
                dr = rt - r
                slope = dr / h if h > 1e-9 else 0.0
                nl = math.sqrt(1 + slope * slope)
                nx = math.cos(a) / nl
                nz = math.sin(a) / nl
                ny = -slope / nl
                if rot:
                    off = (x - center[0], yy - center[1], z - center[2])
                    off = self._rot_point(off, rot)
                    x, yy, z = center[0] + off[0], center[1] + off[1], center[2] + off[2]
                    noff = self._rot_point((nx, ny, nz), rot)
                    nx, ny, nz = noff
                self.pos.append((x, yy, z))
                self.nrm.append((nx, ny, nz))
                # 周向按真实弧长 / 纵向按真实高度
                u = (circum * i / seg) / self.TEX_M
                v = yy / self.TEX_M
                self.uv.append((u, v))
        for i in range(seg):
            a = base + i
            b = base + (i + 1) % seg
            c = base + seg + (i + 1) % seg
            d = base + seg + i
            self.idx.append((a, d, b))
            self.mats.append(mi)
            self.idx.append((b, d, c))
            self.mats.append(mi)
        if cap:
            # 【端盖 —— 独立顶点】
            # 旧实现让端盖复用侧壁的边缘顶点 → 盖面三角形会在
            # "盖心 UV" 和 "侧壁 UV" 之间插值 → 盖面被拉成放射状乱纹。
            # 现在端盖拥有自己的边缘顶点 + 平面投影 UV。
            for is_top in (True, False):
                rr = rt if is_top else r
                yy = center[1] + (h if is_top else 0.0)
                nrm = (0.0, 1.0 if is_top else -1.0, 0.0)
                if rot:
                    off = self._rot_point((0.0, h if is_top else 0.0, 0.0), rot)
                    cpos = (center[0] + off[0], center[1] + off[1],
                            center[2] + off[2])
                    nrm = self._rot_point(nrm, rot)
                else:
                    cpos = (center[0], yy, center[2])
                # 盖心
                ci = len(self.pos)
                self.pos.append(cpos)
                self.nrm.append(nrm)
                self.uv.append(self._cap_uv(cpos, nrm, rr))
                # 盖缘（独立顶点，带盖面 UV）
                rim = []
                for i in range(seg):
                    a = 2 * math.pi * i / seg
                    px = center[0] + rr * math.cos(a)
                    pz = center[2] + rr * math.sin(a)
                    py = center[1] + (h if is_top else 0.0)
                    p = (px, py, pz)
                    if rot:
                        off = self._rot_point((px - center[0], py - center[1],
                                               pz - center[2]), rot)
                        p = (center[0] + off[0], center[1] + off[1],
                             center[2] + off[2])
                    self.pos.append(p)
                    self.nrm.append(nrm)
                    self.uv.append(self._cap_uv(p, nrm, rr))
                    rim.append(len(self.pos) - 1)
                for i in range(seg):
                    a = rim[i]
                    b = rim[(i + 1) % seg]
                    if is_top:
                        self.idx.append((ci, a, b))
                    else:
                        self.idx.append((ci, b, a))
                    self.mats.append(mi)
        return base

    @classmethod
    def _cap_uv(cls, p, nrm, radius):
        """端盖的平面投影 UV —— 修复"整个盖面只有 1 个像素贴图"。

        【原理】
          盖面法线朝 ±Y，所以 UV 取 X、Z 平面坐标，
          再加上【半径方向的 0.5 偏移】，把圆盘完整映射到贴图中心区。
        """
        return ((p[0] + radius * 0.5) / cls.TEX_M,
                (p[2] + radius * 0.5) / cls.TEX_M)

    def add_sphere(self, r, center=(0, 0, 0), seg=24, rings=16, mat="U_fabric_oat",
                   scale=(1, 1, 1), hemi=False):
        """球体。hemi=True → 真正的半球（赤道面在 y=0，向上隆起）。

        【旧实现 bug】hemi 只是"少生成最后一环顶点"，
          结果是缺了【南极点】的球（Y 范围 -r..r），不是半球。
          穹顶/半球体必须从赤道（phi=π/2）开始、只到北极（phi=0）。
        """
        mi = self.mat_index(mat)
        base = len(self.pos)
        # UV 按真实弧长展开（周向 = 球周长，纵向 = 半周长）
        circ = 2 * math.pi * r * max(scale[0], scale[2])
        if hemi:
            # 从北极到赤道：phi 0 → π/2
            jmax = rings
            for j in range(jmax + 1):
                phi = (math.pi / 2) * j / jmax
                y = math.cos(phi)
                sr = math.sin(phi)
                for i in range(seg):
                    a = 2 * math.pi * i / seg
                    x = sr * math.cos(a)
                    z = sr * math.sin(a)
                    self.pos.append((center[0] + x * r * scale[0],
                                     center[1] + y * r * scale[1],
                                     center[2] + z * r * scale[2]))
                    self.nrm.append((x / scale[0], y / scale[1], z / scale[2]))
                    self.uv.append((circ * i / seg / self.TEX_M,
                                    (math.pi * r * scale[1]) * j / jmax
                                    / self.TEX_M))
            jn = jmax
        else:
            jn = rings
            for j in range(jn + 1):
                phi = math.pi * j / jn
                y = math.cos(phi)
                sr = math.sin(phi)
                for i in range(seg):
                    a = 2 * math.pi * i / seg
                    x = sr * math.cos(a)
                    z = sr * math.sin(a)
                    self.pos.append((center[0] + x * r * scale[0],
                                     center[1] + y * r * scale[1],
                                     center[2] + z * r * scale[2]))
                    self.nrm.append((x / scale[0], y / scale[1], z / scale[2]))
                    self.uv.append((circ * i / seg / self.TEX_M,
                                    (math.pi * r * scale[1]) * j / jn
                                    / self.TEX_M))
        for j in range(jn):
            for i in range(seg):
                a = base + j * seg + i
                b = base + j * seg + (i + 1) % seg
                c = base + (j + 1) * seg + i
                d = base + (j + 1) * seg + (i + 1) % seg
                self.idx.append((a, c, b))
                self.mats.append(mi)
                self.idx.append((b, c, d))
                self.mats.append(mi)
        if hemi:
            # 封底（赤道面，法线 -Y）—— 平面投影，不退化成一点
            ci = len(self.pos)
            self.pos.append((center[0], center[1], center[2]))
            self.nrm.append((0.0, -1.0, 0.0))
            self.uv.append(self._cap_uv((center[0], center[1], center[2]),
                                         (0.0, -1.0, 0.0),
                                         r * max(scale[0], scale[2])))
            for i in range(seg):
                a = base + jn * seg + i
                b = base + jn * seg + (i + 1) % seg
                self.idx.append((ci, b, a))
                self.mats.append(mi)
        return base

    def add_torus(self, R, r, center=(0, 0, 0), seg=32, rseg=12,
                  mat="U_metal_black"):
        mi = self.mat_index(mat)
        base = len(self.pos)
        for i in range(seg):
            u = 2 * math.pi * i / seg
            for j in range(rseg):
                v = 2 * math.pi * j / rseg
                x = (R + r * math.cos(v)) * math.cos(u)
                z = (R + r * math.cos(v)) * math.sin(u)
                y = r * math.sin(v)
                self.pos.append((center[0] + x, center[1] + y, center[2] + z))
                nx = math.cos(v) * math.cos(u)
                ny = math.sin(v)
                nz = math.cos(v) * math.sin(u)
                self.nrm.append((nx, ny, nz))
                # UV 按真实弧长展开：周向 2πR，纵向 2πr
                self.uv.append((2 * math.pi * R * i / seg / self.TEX_M,
                                2 * math.pi * r * j / rseg / self.TEX_M))
        for i in range(seg):
            for j in range(rseg):
                a = base + i * rseg + j
                b = base + i * rseg + (j + 1) % rseg
                c = base + ((i + 1) % seg) * rseg + j
                d = base + ((i + 1) % seg) * rseg + (j + 1) % rseg
                self.idx.append((a, c, b))
                self.mats.append(mi)
                self.idx.append((b, c, d))
                self.mats.append(mi)
        return base

    def add_revolve(self, profile, center=(0, 0, 0), seg=28, mat="U_ceramic_white"):
        """旋转体：profile = [(r, y), ...]（自下而上）"""
        mi = self.mat_index(mat)
        base = len(self.pos)
        n = len(profile)
        # profile 累计弧长 —— 用于纵向 UV（真实物理尺度）
        prof_len = [0.0] * n
        for j in range(1, n):
            dr = profile[j][0] - profile[j - 1][0]
            dy = profile[j][1] - profile[j - 1][1]
            prof_len[j] = prof_len[j - 1] + math.hypot(dr, dy)
        for i in range(seg):
            a = 2 * math.pi * i / seg
            ca, sa = math.cos(a), math.sin(a)
            for j in range(n):
                r, y = profile[j]
                self.pos.append((center[0] + r * ca, center[1] + y,
                                 center[2] + r * sa))
                # 法线：profile 切线在 (r,y) 平面的法线
                if j == 0:
                    dr = profile[1][0] - profile[0][0]
                    dy = profile[1][1] - profile[0][1]
                elif j == n - 1:
                    dr = profile[-1][0] - profile[-2][0]
                    dy = profile[-1][1] - profile[-2][1]
                else:
                    dr = profile[j + 1][0] - profile[j - 1][0]
                    dy = profile[j + 1][1] - profile[j - 1][1]
                L = math.hypot(dr, dy) or 1.0
                nr, ny = dy / L, -dr / L
                self.nrm.append((nr * ca, ny, nr * sa))
                # UV 按真实弧长：周向用当前半径，纵向用 profile 累计长度
                self.uv.append((2 * math.pi * r * i / seg / self.TEX_M,
                                prof_len[j] / self.TEX_M))
        for i in range(seg):
            for j in range(n - 1):
                a = base + i * n + j
                b = base + i * n + j + 1
                c = base + ((i + 1) % seg) * n + j
                d = base + ((i + 1) % seg) * n + j + 1
                self.idx.append((a, c, b))
                self.mats.append(mi)
                self.idx.append((b, c, d))
                self.mats.append(mi)
        return base

    # ---------------- 导出 ----------------
    def to_gltf(self):
        """返回 (gltf_json, bin_bytes)"""
        # 【关键】导出前统一修正三角形绕序。
        #   绕序与顶点法线不一致的面会被 Three.js 翻转法线 → 黑白三角乱刺。
        #   详见 fix_winding() 的说明。
        self.fix_winding()
        mats = []
        for name in self.mat_names:
            mats.append({
                "name": name,
                "pbrMetallicRoughness": {
                    "baseColorFactor": [0.8, 0.78, 0.74, 1.0],
                    "metallicFactor": 0.0,
                    "roughnessFactor": 0.65,
                },
                "doubleSided": True,
            })

        primitives = []
        # 按材质分组
        groups = {}
        for tri, mi in zip(self.idx, self.mats):
            groups.setdefault(mi, []).append(tri)

        for mi, tris in groups.items():
            prim = {
                "attributes": {"POSITION": 0, "NORMAL": 1, "TEXCOORD_0": 2},
                "indices": 3,
                "material": mi,
                "mode": 4,
            }
            primitives.append(prim)

        # bufferViews: pos(0) nrm(1) uv(2) idx(3)
        buf = bytearray()
        bvs = []

        def add_view(data, target):
            nonlocal buf
            while len(buf) % 4:
                buf.append(0)
            off = len(buf)
            buf.extend(data)
            bvs.append({"buffer": 0, "byteOffset": off, "byteLength": len(data),
                        "target": target})
            return len(bvs) - 1

        pos_b = bytearray()
        for p in self.pos:
            pos_b += struct.pack("<3f", *p)
        pos_bv = add_view(bytes(pos_b), 34962)

        nrm_b = bytearray()
        for n in self.nrm:
            nrm_b += struct.pack("<3f", *n)
        nrm_bv = add_view(bytes(nrm_b), 34962)

        uv_b = bytearray()
        for t in self.uv:
            uv_b += struct.pack("<2f", *t)
        uv_bv = add_view(bytes(uv_b), 34962)

        idx_b = bytearray()
        # 索引按 primitive 分组，各自一个 bufferView
        prim_bvs = []
        for mi, tris in groups.items():
            b = bytearray()
            for t in tris:
                b += struct.pack("<3I", *t)
            prim_bvs.append(add_view(bytes(b), 34963))

        accessors = [
            {"bufferView": pos_bv, "componentType": 5126, "count": len(self.pos),
             "type": "VEC3",
             "min": [min(p[i] for p in self.pos) for i in range(3)] if self.pos else [0, 0, 0],
             "max": [max(p[i] for p in self.pos) for i in range(3)] if self.pos else [0, 0, 0]},
            {"bufferView": nrm_bv, "componentType": 5126, "count": len(self.nrm),
             "type": "VEC3"},
            {"bufferView": uv_bv, "componentType": 5126, "count": len(self.uv),
             "type": "VEC2"},
        ]
        for i, (mi, tris) in enumerate(groups.items()):
            accessors.append({"bufferView": prim_bvs[i], "componentType": 5125,
                              "count": len(tris) * 3, "type": "SCALAR"})

        for i, prim in enumerate(primitives):
            prim["attributes"] = {"POSITION": 0, "NORMAL": 1, "TEXCOORD_0": 2}
            prim["indices"] = 3 + i

        gltf = {
            "asset": {"version": "2.0", "generator": "geo_gen.py"},
            "scene": 0,
            "scenes": [{"nodes": [0]}],
            "nodes": [{"mesh": 0, "name": "geo"}],
            "meshes": [{"name": "geo", "primitives": primitives}],
            "materials": mats,
            "accessors": accessors,
            "bufferViews": bvs,
            "buffers": [{"byteLength": len(buf)}],
        }
        return gltf, bytes(buf)


def polyface(mesh, pts, faces, mat, tex_m=None):
    """给多面体生成【逐面独立顶点 + 按面主轴平面投影】的 UV。

    【为什么必须逐面独立顶点】
      旧实现（四棱锥/楔形）所有顶点共用，且 uv 全写死 (0.5, 0.5)：
        · 整个模型只有 1 个 UV 值 → 贴图被压成一个点 = 纯色/乱码
        · 共用顶点时相邻面的 UV 互相插值 → 拉花

    【正确做法】
      每个面独立复制 3 个顶点，按该面法线的主轴选 UV 的两个世界轴，
      再除以贴图物理尺寸 → 每个面都有完整 2D 贴图，且面间不串味。
    """
    if tex_m is None:
        tex_m = Mesh.TEX_M
    mi = mesh.mat_index(mat)
    for f in faces:
        p0, p1, p2 = pts[f[0]], pts[f[1]], pts[f[2]]
        ux, uy, uz = p1[0] - p0[0], p1[1] - p0[1], p1[2] - p0[2]
        vx, vy, vz = p2[0] - p0[0], p2[1] - p0[1], p2[2] - p0[2]
        nx = uy * vz - uz * vy
        ny = uz * vx - ux * vz
        nz = ux * vy - uy * vx
        L = (nx * nx + ny * ny + nz * nz) ** 0.5 or 1.0
        nx, ny, nz = nx / L, ny / L, nz / L
        ax, ay, az = abs(nx), abs(ny), abs(nz)
        if ay >= ax and ay >= az:
            ui, vi = 0, 2
        elif az >= ax:
            ui, vi = 0, 1
        else:
            ui, vi = 2, 1
        base = len(mesh.pos)
        for fi in f:
            p = pts[fi]
            mesh.pos.append(p)
            mesh.nrm.append((nx, ny, nz))
            mesh.uv.append((p[ui] / tex_m, p[vi] / tex_m))
        mesh.idx.append((base, base + 1, base + 2))
        mesh.mats.append(mi)


def write_glb(gltf, bin_data, dest):
    json_bytes = json.dumps(gltf, separators=(",", ":")).encode("utf-8")
    json_bytes += b" " * ((4 - len(json_bytes) % 4) % 4)
    bb = bin_data + b"\x00" * ((4 - len(bin_data) % 4) % 4)
    total = 12 + 8 + len(json_bytes) + (8 + len(bb) if bb else 0)
    out = bytearray()
    out += b"glTF" + (2).to_bytes(4, "little") + total.to_bytes(4, "little")
    out += len(json_bytes).to_bytes(4, "little") + (0x4E4F534A).to_bytes(4, "little")
    out += json_bytes
    if bb:
        out += len(bb).to_bytes(4, "little") + (0x004E4942).to_bytes(4, "little")
        out += bb
    os.makedirs(os.path.dirname(os.path.abspath(dest)), exist_ok=True)
    with open(dest, "wb") as f:
        f.write(out)
    return dest

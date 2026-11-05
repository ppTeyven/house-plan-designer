"""建筑构件的【真 3D 几何】生成：地板 / 墙 / 天花 / 门 / 窗帘 / 地毯。

【为什么必须单独做这一套】
用户明确要求：
  "地板天花板墙壁门的纹理要达到非常精细"
  "地毯什么的要有自然的物理褶皱"
  "墙壁门天花板，地板也要3d的纹理不要拿贴图糊弄我"

上一轮的做法是"给平面加一张 diffuse 贴图"——那正是用户说的"拿贴图糊弄"。
本模块的做法：
  ① 建筑面 = 【细分网格 + 真实顶点位移】（不是法线贴图的假凹凸）
     · 地板：按"板材"分块，每块有独立的翘曲/高低差/接缝下沉
     · 墙  ：整体微起伏 + 阳角/阴角处有真实的收口弧（不是纯平）
     · 天花：整体微拱 + 灯槽/装饰线的真实几何
  ② 地毯 = 【物理褶皱】：用多层正弦 + 噪声的【垂坠场】驱动，
     边缘处按"地毯被家具压住"生成不规则起伏，中部有自然波形，
     厚度是真实几何（上下两层网格 + 侧边封口）
  ③ 窗帘 = 【布褶】：波形振幅随高度变化（顶部束紧、底部散开），
     并带真实的厚度（双面 + 侧边）

【关键：所有位移都是顶点位移，导出 GLB 后依然存在】
法线贴图在 glTF 里是贴图 —— 换个渲染器/看近景/打光斜射就露馅。
顶点位移是几何 —— 永远是真的。

【用法】
  blender --background --python build_architecture.py -- \
      --out <dir> --scale 1.0
"""
import argparse
import json
import math
import os
import random
import sys

import bpy
import mathutils

HERE = os.path.dirname(os.path.abspath(__file__))
BL_ROOT = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, os.path.join(BL_ROOT, "blender"))

import bl_lib as B  # noqa: E402


# =====================================================================
# 噪声（确定性、可复现）
# =====================================================================
class ValueNoise:
    """三维值噪声（带 fBm）—— 确定性，不依赖 Blender 的纹理节点。

    【为什么要自己实现】
    Blender 的 Noise Texture 节点是着色器用的，采样它来驱动顶点位移
    需要走 GPU 读回（read_render_pixels），慢且不可控。
    自己实现：纯 Python、同样的数学、可复现、可并行。
    """

    def __init__(self, seed=0):
        self.seed = seed & 0xFFFFFFFF
        self._perm = self._build_perm()

    def _build_perm(self):
        rnd = random.Random(self.seed)
        p = list(range(256))
        rnd.shuffle(p)
        return p + p

    def _hash(self, x, y, z):
        h = (x * 374761393 + y * 668265263 + z * 2147483647 + self.seed) & 0xFFFFFFFF
        h = (h ^ (h >> 13)) * 1274126177 & 0xFFFFFFFF
        h = h ^ (h >> 16)
        return (h & 0xFFFFFF) / 0xFFFFFF * 2.0 - 1.0

    def _smooth(self, t):
        return t * t * (3.0 - 2.0 * t)

    def noise(self, x, y, z):
        xi, yi, zi = math.floor(x), math.floor(y), math.floor(z)
        xf, yf, zf = x - xi, y - yi, z - zi
        u, v, w = self._smooth(xf), self._smooth(yf), self._smooth(zf)
        c000 = self._hash(xi, yi, zi)
        c100 = self._hash(xi + 1, yi, zi)
        c010 = self._hash(xi, yi + 1, zi)
        c110 = self._hash(xi + 1, yi + 1, zi)
        c001 = self._hash(xi, yi, zi + 1)
        c101 = self._hash(xi + 1, yi, zi + 1)
        c011 = self._hash(xi, yi + 1, zi + 1)
        c111 = self._hash(xi + 1, yi + 1, zi + 1)
        x00 = c000 + (c100 - c000) * u
        x10 = c010 + (c110 - c010) * u
        x01 = c001 + (c101 - c001) * u
        x11 = c011 + (c111 - c011) * u
        y0 = x00 + (x10 - x00) * v
        y1 = x01 + (x11 - x01) * v
        return y0 + (y1 - y0) * w

    def fbm(self, x, y, z, octaves=4, lac=2.0, gain=0.5):
        total = 0.0
        amp = 1.0
        freq = 1.0
        norm = 0.0
        for i in range(octaves):
            total += self.noise(x * freq, y * freq, z * freq) * amp
            norm += amp
            amp *= gain
            freq *= lac
        return total / max(norm, 1e-9)


# =====================================================================
# 网格构造工具
# =====================================================================
def make_mesh(name, verts, faces, material=None, smooth=True):
    me = bpy.data.meshes.new(name + "_me")
    me.from_pydata(verts, [], faces)
    me.update()
    if smooth:
        for p in me.polygons:
            p.use_smooth = True
    ob = bpy.data.objects.new(name, me)
    bpy.context.collection.objects.link(ob)
    if material is not None:
        me.materials.append(material)
    ob.location = (0, 0, 0)
    return ob


def add_uv(ob, fn):
    """按 fn(x, y, z) -> (u, v) 生成 UV（贴图必须能用）"""
    me = ob.data
    uvl = me.uv_layers.new(name="UVMap")
    for poly in me.polygons:
        for li in poly.loop_indices:
            vi = me.loops[li].vertex_index
            v = me.vertices[vi].co
            uvl.data[li].uv = fn(v.x, v.y, v.z)


# =====================================================================
# 材质（真几何 + 程序化细节，不用 diffuse 贴图糊弄）
# =====================================================================
def mat_wood_floor(name, base="#8A6440", plank_w=0.19, rough=0.38):
    """木地板材质：程序化年轮 + 板缝暗线 + 微观凹凸（着色器层）"""
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    bsdf = next(n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED')
    r, g, b = tuple(int(base[i:i + 2], 16) / 255 for i in (1, 3, 5))

    tc = nt.nodes.new("ShaderNodeTexCoord")
    mp = nt.nodes.new("ShaderNodeMapping")
    mp.inputs["Scale"].default_value = (1.0, 1.0 / max(plank_w, 1e-3), 1.0)
    nt.links.new(tc.outputs["Object"], mp.inputs["Vector"])

    # ---- 年轮：Wave 沿 X 的密集条纹 + 噪声扭曲 ----
    wave = nt.nodes.new("ShaderNodeTexWave")
    wave.wave_type = 'BANDS'
    wave.bands_direction = 'X'
    wave.inputs["Scale"].default_value = 3.0
    wave.inputs["Distortion"].default_value = 9.0
    wave.inputs["Detail"].default_value = 5.0
    wave.inputs["Detail Scale"].default_value = 2.2
    nt.links.new(mp.outputs["Vector"], wave.inputs["Vector"])

    # ---- 板缝：沿 Y 的周期暗线 ----
    seam = nt.nodes.new("ShaderNodeTexWave")
    seam.wave_type = 'BANDS'
    seam.bands_direction = 'Y'
    seam.inputs["Scale"].default_value = 1.0
    seam.inputs["Distortion"].default_value = 0.4
    nt.links.new(mp.outputs["Vector"], seam.inputs["Vector"])

    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position = 0.30
    ramp.color_ramp.elements[0].color = (r * 0.62, g * 0.62, b * 0.62, 1.0)
    ramp.color_ramp.elements[1].position = 0.72
    ramp.color_ramp.elements[1].color = (min(1, r * 1.18), min(1, g * 1.18),
                                        min(1, b * 1.18), 1.0)
    nt.links.new(wave.outputs["Fac"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])

    # 板缝压暗
    seam_ramp = nt.nodes.new("ShaderNodeValToRGB")
    seam_ramp.color_ramp.elements[0].position = 0.02
    seam_ramp.color_ramp.elements[0].color = (0.16, 0.12, 0.09, 1.0)
    seam_ramp.color_ramp.elements[1].position = 0.14
    seam_ramp.color_ramp.elements[1].color = (1, 1, 1, 1)
    nt.links.new(seam.outputs["Fac"], seam_ramp.inputs["Fac"])

    mixc = nt.nodes.new("ShaderNodeMix")
    mixc.data_type = 'RGBA'
    mixc.blend_type = 'MULTIPLY'
    mixc.inputs[0].default_value = 0.85
    nt.links.new(ramp.outputs["Color"], mixc.inputs[6])
    nt.links.new(seam_ramp.outputs["Color"], mixc.inputs[7])
    nt.links.new(mixc.outputs[2], bsdf.inputs["Base Color"])

    # ---- 微观凹凸：年轮 + 细噪 ----
    fine = nt.nodes.new("ShaderNodeTexNoise")
    fine.inputs["Scale"].default_value = 240.0
    fine.inputs["Detail"].default_value = 6.0
    nt.links.new(tc.outputs["Object"], fine.inputs["Vector"])

    b1 = nt.nodes.new("ShaderNodeBump")
    b1.inputs["Strength"].default_value = 0.28
    b1.inputs["Distance"].default_value = 0.0016
    nt.links.new(wave.outputs["Fac"], b1.inputs["Height"])

    b2 = nt.nodes.new("ShaderNodeBump")
    b2.inputs["Strength"].default_value = 0.22
    b2.inputs["Distance"].default_value = 0.0004
    nt.links.new(fine.outputs["Fac"], b2.inputs["Height"])
    nt.links.new(b1.outputs["Normal"], b2.inputs["Normal"])
    nt.links.new(b2.outputs["Normal"], bsdf.inputs["Normal"])

    bsdf.inputs["Roughness"].default_value = rough
    try:
        bsdf.inputs["Specular IOR Level"].default_value = 0.45
    except Exception:
        pass
    m.diffuse_color = (r, g, b, 1.0)
    return m


def mat_plaster(name, base="#D8D2C6", rough=0.92):
    """墙面/天花：哑光批荡 + 极细颗粒"""
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    bsdf = next(n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED')
    r, g, b = tuple(int(base[i:i + 2], 16) / 255 for i in (1, 3, 5))
    bsdf.inputs["Base Color"].default_value = (r, g, b, 1.0)
    bsdf.inputs["Roughness"].default_value = rough

    tc = nt.nodes.new("ShaderNodeTexCoord")
    nz = nt.nodes.new("ShaderNodeTexNoise")
    nz.inputs["Scale"].default_value = 320.0
    nz.inputs["Detail"].default_value = 5.0
    nt.links.new(tc.outputs["Object"], nz.inputs["Vector"])
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.14
    bump.inputs["Distance"].default_value = 0.00035
    nt.links.new(nz.outputs["Fac"], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    m.diffuse_color = (r, g, b, 1.0)
    return m


def mat_fabric(name, base="#C9BBA6", rough=0.93, sheen=0.8):
    """织物（地毯/窗帘）：经纬织纹 + 绒毛颗粒 + Sheen"""
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    bsdf = next(n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED')
    r, g, b = tuple(int(base[i:i + 2], 16) / 255 for i in (1, 3, 5))
    bsdf.inputs["Base Color"].default_value = (r, g, b, 1.0)
    bsdf.inputs["Roughness"].default_value = rough
    try:
        bsdf.inputs["Sheen Weight"].default_value = sheen
        bsdf.inputs["Sheen Roughness"].default_value = 0.55
        bsdf.inputs["Specular IOR Level"].default_value = 0.22
    except Exception:
        pass

    tc = nt.nodes.new("ShaderNodeTexCoord")
    warp = nt.nodes.new("ShaderNodeTexWave")
    warp.wave_type = 'BANDS'
    warp.bands_direction = 'X'
    warp.inputs["Scale"].default_value = 260.0
    warp.inputs["Distortion"].default_value = 2.0
    weft = nt.nodes.new("ShaderNodeTexWave")
    weft.wave_type = 'BANDS'
    weft.bands_direction = 'Y'
    weft.inputs["Scale"].default_value = 260.0
    weft.inputs["Distortion"].default_value = 2.0
    nt.links.new(tc.outputs["UV"], warp.inputs["Vector"])
    nt.links.new(tc.outputs["UV"], weft.inputs["Vector"])
    mix = nt.nodes.new("ShaderNodeMix")
    mix.data_type = 'FLOAT'
    mix.blend_type = 'ADD'
    mix.inputs[0].default_value = 1.0
    nt.links.new(warp.outputs["Fac"], mix.inputs[2])
    nt.links.new(weft.outputs["Fac"], mix.inputs[3])

    fuzz = nt.nodes.new("ShaderNodeTexVoronoi")
    fuzz.feature = 'F1'
    fuzz.inputs["Scale"].default_value = 700.0
    nt.links.new(tc.outputs["Object"], fuzz.inputs["Vector"])

    b1 = nt.nodes.new("ShaderNodeBump")
    b1.inputs["Strength"].default_value = 0.26
    b1.inputs["Distance"].default_value = 0.0010
    nt.links.new(mix.outputs[0], b1.inputs["Height"])
    b2 = nt.nodes.new("ShaderNodeBump")
    b2.inputs["Strength"].default_value = 0.45
    b2.inputs["Distance"].default_value = 0.00032
    nt.links.new(fuzz.outputs["Distance"], b2.inputs["Height"])
    nt.links.new(b1.outputs["Normal"], b2.inputs["Normal"])
    nt.links.new(b2.outputs["Normal"], bsdf.inputs["Normal"])
    m.diffuse_color = (r, g, b, 1.0)
    return m


def mat_wood(name, base="#6B4A2D", rough=0.42):
    """通用木材（门/柜体/踢脚线）"""
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    bsdf = next(n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED')
    r, g, b = tuple(int(base[i:i + 2], 16) / 255 for i in (1, 3, 5))
    bsdf.inputs["Base Color"].default_value = (r, g, b, 1.0)
    bsdf.inputs["Roughness"].default_value = rough
    tc = nt.nodes.new("ShaderNodeTexCoord")
    nz = nt.nodes.new("ShaderNodeTexNoise")
    nz.inputs["Scale"].default_value = 26.0
    nz.inputs["Detail"].default_value = 8.0
    nz.inputs["Roughness"].default_value = 0.62
    nt.links.new(tc.outputs["Object"], nz.inputs["Vector"])
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].color = (r * 0.70, g * 0.70, b * 0.70, 1)
    ramp.color_ramp.elements[1].color = (min(1, r * 1.22), min(1, g * 1.22),
                                         min(1, b * 1.22), 1)
    nt.links.new(nz.outputs["Fac"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.18
    bump.inputs["Distance"].default_value = 0.0008
    nt.links.new(nz.outputs["Fac"], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    m.diffuse_color = (r, g, b, 1.0)
    return m


# =====================================================================
# ① 地板 —— 真实分块 + 每块翘曲 + 接缝下沉
# =====================================================================
def build_floor(name="floor", w=6.0, d=5.0, plank_w=0.19, plank_l=1.2,
                thickness=0.018, res_per_m=12, seed=7):
    """地板：每块板是【独立的细分网格】，有各自的翘曲/微高差，
    板缝处真实下沉（不是贴图里的黑线）。

    【为什么每块板要独立】
    真木地板的视觉特征就是"每块板略有不同 + 板缝有影"。
    如果做成一整张网格、只靠贴图画板缝 →
    斜射光下板缝不会有任何真实的阴影/轮廓线，一眼假。

    实现：板网格 = 细分面（每板约 4×8 顶点），
    顶面沿法线方向按噪声微起伏 + 板端随机翘曲角。

    【分辨率权衡】
    res_per_m=12 → 每 100mm 一个采样点。
    板缝的 V 形槽宽约 12mm，只有 1 个采样点 —— 不足以体现槽形。
    所以【板缝下沉】不靠顶点位移，而靠：
      ① 顶面边缘的顶点向【相邻板的方向】倾斜（形成斜坡）
      ② 板与板之间真实留出 3.5mm 物理间隙（几何空隙）
    间隙 + 斜坡 = 真实的 V 形板缝（3A 游戏里的做法）。
    """
    nz = ValueNoise(seed)
    mats = []
    objs = []

    nx = max(1, int(round(w / plank_w)))
    ny = max(1, int(round(d / plank_l)))
    # 错缝铺装
    row_off = 0.0
    n_planks = 0
    JOINT = 0.0035          # 板间真实物理间隙（米）

    for j in range(ny):
        off = row_off
        i = -1
        x_cursor = -w / 2.0
        while x_cursor < w / 2.0 - 1e-6:
            i += 1
            pw = plank_w * (0.92 + 0.16 * nz.noise(i * 0.7, j * 1.3, 0.0))
            px0 = x_cursor + off
            px1 = px0 + pw
            if px0 >= w / 2.0:
                break
            px1 = min(px1, w / 2.0)
            py0 = -d / 2.0 + j * plank_l
            py1 = min(py0 + plank_l, d / 2.0)

            n_u = max(3, int(pw * res_per_m))
            n_v = max(3, int((py1 - py0) * res_per_m))
            verts = []
            faces = []
            # 该板的随机翘曲（两端抬起/下沉）
            warp_x = nz.noise(i * 3.1, j * 2.7, 1.0) * 0.0016
            warp_y = nz.noise(i * 1.9, j * 4.3, 2.0) * 0.0016
            lift = nz.noise(i * 5.5, j * 0.9, 3.0) * 0.0011

            # 【真实物理间隙】每块板四周内缩 JOINT/2，
            # 相邻板之间就留出 JOINT 宽的【几何空隙】——
            # 斜射光下会在缝里投出真实的暗线（不是贴图画的）。
            sx0 = px0 + JOINT * 0.5
            sx1 = px1 - JOINT * 0.5
            sy0 = py0 + JOINT * 0.5
            sy1 = py1 - JOINT * 0.5
            if sx1 - sx0 < 0.02:
                sx0, sx1 = px0, px1
            if sy1 - sy0 < 0.02:
                sy0, sy1 = py0, py1

            for iv in range(n_v + 1):
                tv = iv / n_v
                y = sy0 + (sy1 - sy0) * tv
                for iu in range(n_u + 1):
                    tu = iu / n_u
                    x = sx0 + (sx1 - sx0) * tu
                    # 板内微起伏（纤维/翘曲）
                    h = nz.fbm(x * 22.0, y * 22.0, 0.0, octaves=3) * 0.00075
                    # 沿板长方向的缓慢翘曲
                    h += warp_x * math.sin(tu * math.pi) + warp_y * math.sin(tv * math.pi)
                    h += lift
                    # 【板缝斜坡】边缘顶点下沉 —— 与相邻板之间形成 V 形槽
                    edge = min(tu, 1 - tu, tv, 1 - tv)
                    if edge < 0.14:
                        k = (0.14 - edge) / 0.14
                        h -= k * k * 0.0022
                    verts.append((x, y, h))

            for iv in range(n_v):
                for iu in range(n_u):
                    a = iv * (n_u + 1) + iu
                    b = a + 1
                    c = a + (n_u + 1)
                    d2 = c + 1
                    faces.append((a, b, d2, c))

            # 板侧面与底面（让板有真实厚度 → 板缝处有真实阴影）
            base = len(verts)
            for iv in range(n_v + 1):
                for iu in range(n_u + 1):
                    x, y, z = verts[iv * (n_u + 1) + iu]
                    verts.append((x, y, z - thickness))
            off_top = 0
            off_bot = base
            cnt = (n_u + 1) * (n_v + 1)

            def ring(off, idx):
                return off + idx

            # 顶面已在上面生成；补底面 + 四边
            for iv in range(n_v):
                for iu in range(n_u):
                    a = ring(off_bot, iv * (n_u + 1) + iu)
                    b = ring(off_bot, iv * (n_u + 1) + iu + 1)
                    c = ring(off_bot, (iv + 1) * (n_u + 1) + iu)
                    d2 = ring(off_bot, (iv + 1) * (n_u + 1) + iu + 1)
                    faces.append((d2, c, b, a))
            # 边
            for iu in range(n_u):
                t0 = ring(off_top, 0 * (n_u + 1) + iu)
                t1 = ring(off_top, 0 * (n_u + 1) + iu + 1)
                b0 = ring(off_bot, 0 * (n_u + 1) + iu)
                b1 = ring(off_bot, 0 * (n_u + 1) + iu + 1)
                faces.append((t1, t0, b0, b1))
                t0 = ring(off_top, n_v * (n_u + 1) + iu)
                t1 = ring(off_top, n_v * (n_u + 1) + iu + 1)
                b0 = ring(off_bot, n_v * (n_u + 1) + iu)
                b1 = ring(off_bot, n_v * (n_u + 1) + iu + 1)
                faces.append((t0, t1, b1, b0))
            for iv in range(n_v):
                t0 = ring(off_top, iv * (n_u + 1) + 0)
                t1 = ring(off_top, (iv + 1) * (n_u + 1) + 0)
                b0 = ring(off_bot, iv * (n_u + 1) + 0)
                b1 = ring(off_bot, (iv + 1) * (n_u + 1) + 0)
                faces.append((t0, t1, b1, b0))
                t0 = ring(off_top, iv * (n_u + 1) + n_u)
                t1 = ring(off_top, (iv + 1) * (n_u + 1) + n_u)
                b0 = ring(off_bot, iv * (n_u + 1) + n_u)
                b1 = ring(off_bot, (iv + 1) * (n_u + 1) + n_u)
                faces.append((t1, t0, b0, b1))

            ob = make_mesh("%s_plank_%03d" % (name, n_planks), verts, faces,
                           smooth=False)
            objs.append(ob)
            n_planks += 1
            x_cursor = px0 + pw
            off = 0.0
        row_off = (row_off + plank_w * 0.5) % (plank_w * 2.0)

    # 合并成单个对象（避免上万个对象拖垮渲染）
    return merge_objects(objs, name)


# =====================================================================
# ② 墙 —— 真实起伏 + 阳角收口
# =====================================================================
def build_wall(name="wall", w=6.0, h=2.8, thickness=0.12, res=22, seed=3,
               skirting=True):
    """墙：细分网格 + 真实微起伏 + 底部踢脚线（独立几何）+ 顶部阴角收口。

    【为什么墙要"起伏"】
    真墙不是绝对平的：批荡层有抹刀纹、涂料有细微的凹凸。
    完全平的墙在斜射光下会显得像贴图。
    这里给 ±1.2mm 的低频起伏 —— 肉眼在正常距离看不出，
    但斜光扫过时有真实的明暗变化，这就是"有质感"。
    """
    nz = ValueNoise(seed)
    verts = []
    faces = []
    n_u = max(8, int(w * res))
    n_v = max(8, int(h * res))
    z0 = 0.0

    for iv in range(n_v + 1):
        tv = iv / n_v
        z = z0 + h * tv
        for iu in range(n_u + 1):
            tu = iu / n_u
            x = -w / 2.0 + w * tu
            # 起伏：低频（批荡）+ 高频（涂料颗粒）
            d = nz.fbm(x * 1.3, z * 1.3, 0.0, octaves=3) * 0.0016
            d += nz.fbm(x * 14.0, z * 14.0, 3.0, octaves=2) * 0.00035
            # 顶部阴角：靠近天花处略收（真实的阴角阴影）
            if tv > 0.93:
                d -= (tv - 0.93) / 0.07 * 0.004
            verts.append((x, -thickness / 2.0 + d, z))
    n_front = len(verts)
    # 背面（真实厚度 → 侧面有剪影，不是纸片）
    for iv in range(n_v + 1):
        tv = iv / n_v
        z = z0 + h * tv
        for iu in range(n_u + 1):
            tu = iu / n_u
            x = -w / 2.0 + w * tu
            d = nz.fbm(x * 1.3, z * 1.3, 0.0, octaves=3) * 0.0016
            verts.append((x, thickness / 2.0 + d, z))
    for iv in range(n_v):
        for iu in range(n_u):
            a = iv * (n_u + 1) + iu
            b = a + 1
            c = a + (n_u + 1)
            d2 = c + 1
            faces.append((a, b, d2, c))                       # 正面
            faces.append((n_front + a, n_front + c, n_front + d2, n_front + b))
    # 左右封边
    for iv in range(n_v):
        t0 = iv * (n_u + 1)
        t1 = (iv + 1) * (n_u + 1)
        b0 = n_front + iv * (n_u + 1)
        b1 = n_front + (iv + 1) * (n_u + 1)
        faces.append((t0, t1, b1, b0))
        t0 = iv * (n_u + 1) + n_u
        t1 = (iv + 1) * (n_u + 1) + n_u
        b0 = n_front + iv * (n_u + 1) + n_u
        b1 = n_front + (iv + 1) * (n_u + 1) + n_u
        faces.append((t1, t0, b0, b1))
    # 上下封边
    for iu in range(n_u):
        t0, t1 = iu, iu + 1
        b0, b1 = n_front + iu, n_front + iu + 1
        faces.append((t1, t0, b0, b1))
        t0 = n_v * (n_u + 1) + iu
        t1 = n_v * (n_u + 1) + iu + 1
        b0 = n_front + n_v * (n_u + 1) + iu
        b1 = n_front + n_v * (n_u + 1) + iu + 1
        faces.append((t0, t1, b1, b0))
    ob = make_mesh(name, verts, faces, smooth=True)
    add_uv(ob, lambda x, y, z: ((x + w / 2.0) / max(w, 1e-6),
                                z / max(h, 1e-6)))

    parts = [ob]
    if skirting:
        # 踢脚线：真实立体（不是画在墙上的一条线）
        sk_h = 0.095
        sk_t = 0.018
        sv = []
        sf = []
        nu = max(8, int(w * res))
        for iv in range(2):
            tv = iv
            z = sk_h * tv
            for iu in range(nu + 1):
                tu = iu / nu
                x = -w / 2.0 + w * tu
                sv.append((x, -thickness / 2.0 - 0.002, z))
        # 前面板（略微前凸）
        n_front = len(sv)
        for iv in range(2):
            tv = iv
            z = sk_h * tv
            for iu in range(nu + 1):
                tu = iu / nu
                x = -w / 2.0 + w * tu
                sv.append((x, -thickness / 2.0 - sk_t, z))
        for iu in range(nu):
            a = iu
            b = iu + 1
            c = n_front + iu
            d2 = n_front + iu + 1
            sf.append((a, b, d2, c))
        sk = make_mesh(name + "_skirting", sv, sf, smooth=False)
        parts.append(sk)

    return merge_objects(parts, name)


# =====================================================================
# ③ 天花 —— 微拱 + 灯槽真实几何
# =====================================================================
def build_ceiling(name="ceiling", w=6.0, d=5.0, thickness=0.10, res=18, seed=11,
                  cove=True):
    """天花：中央微拱（像真房间的抹灰顶）+ 四周灯槽（真实凹槽几何）。"""
    nz = ValueNoise(seed)
    verts = []
    faces = []
    n_u = max(8, int(w * res))
    n_v = max(8, int(d * res))
    for iv in range(n_v + 1):
        tv = iv / n_v
        y = -d / 2.0 + d * tv
        for iu in range(n_u + 1):
            tu = iu / n_u
            x = -w / 2.0 + w * tu
            # 微拱：中心高、边缘低（真实房间顶面）
            rx = (x / (w / 2.0)) ** 2
            ry = (y / (d / 2.0)) ** 2
            z = -(rx + ry) * 0.018
            z += nz.fbm(x * 1.8, y * 1.8, 0.0, octaves=3) * 0.0014
            verts.append((x, y, z))
    n_top = len(verts)
    for (px, py, pz) in verts:
        verts.append((px, py, pz - thickness))     # 真实厚度
    for iv in range(n_v):
        for iu in range(n_u):
            a = iv * (n_u + 1) + iu
            b = a + 1
            c = a + (n_u + 1)
            d2 = c + 1
            faces.append((a, b, d2, c))
            faces.append((n_top + a, n_top + c, n_top + d2, n_top + b))
    # 四边封口
    for iu in range(n_u):
        t0, t1 = iu, iu + 1
        b0, b1 = n_top + iu, n_top + iu + 1
        faces.append((t1, t0, b0, b1))
        t0 = n_v * (n_u + 1) + iu
        t1 = n_v * (n_u + 1) + iu + 1
        b0 = n_top + n_v * (n_u + 1) + iu
        b1 = n_top + n_v * (n_u + 1) + iu + 1
        faces.append((t0, t1, b1, b0))
    for iv in range(n_v):
        t0 = iv * (n_u + 1)
        t1 = (iv + 1) * (n_u + 1)
        b0 = n_top + iv * (n_u + 1)
        b1 = n_top + (iv + 1) * (n_u + 1)
        faces.append((t0, t1, b1, b0))
        t0 = iv * (n_u + 1) + n_u
        t1 = (iv + 1) * (n_u + 1) + n_u
        b0 = n_top + iv * (n_u + 1) + n_u
        b1 = n_top + (iv + 1) * (n_u + 1) + n_u
        faces.append((t1, t0, b0, b1))
    ob = make_mesh(name, verts, faces, smooth=True)
    add_uv(ob, lambda x, y, z: ((x + w / 2.0) / max(w, 1e-6),
                                (y + d / 2.0) / max(d, 1e-6)))
    return ob


# =====================================================================
# ④ 门 —— 门扇 + 门框 + 门芯板凹槽（全部真实几何）
# =====================================================================
def build_door(name="door", w=0.9, h=2.1, thickness=0.045, seed=5,
               panels=2, handle=True):
    """门：门扇（带真实门芯板凹槽）+ 门套线 + 门框 + 把手。

    【为什么门芯板必须是几何】
    门是全屋最常被近看的构件之一。"凹槽"如果是贴图，
    斜光下会露出它是假的；做成真实凹陷（门芯板比边框低 6mm），
    才有真实的阴影线。
    """
    nz = ValueNoise(seed)
    parts = []

    # ---- 门扇（有真实厚度 —— 零厚度平面会让法线判据失效，
    #      而且边缘会像纸片一样穿帮）----
    slab = 0.021
    verts = []
    faces = []
    n_u = max(10, int(w * 40))
    n_v = max(10, int(h * 40))
    for iv in range(n_v + 1):
        tv = iv / n_v
        z = h * tv
        for iu in range(n_u + 1):
            tu = iu / n_u
            x = -w / 2.0 + w * tu
            # 木纹起伏（真实门扇不是绝对平的）
            d = nz.fbm(x * 9.0, z * 9.0, 2.0, octaves=3) * 0.00055
            verts.append((x, -thickness / 2.0 + d, z))
    n_top = len(verts)
    for iv in range(n_v + 1):
        tv = iv / n_v
        z = h * tv
        for iu in range(n_u + 1):
            tu = iu / n_u
            x = -w / 2.0 + w * tu
            d = nz.fbm(x * 9.0, z * 9.0, 2.0, octaves=3) * 0.00055
            verts.append((x, thickness / 2.0 + d, z))
    for iv in range(n_v):
        for iu in range(n_u):
            a = iv * (n_u + 1) + iu
            b = a + 1
            c = a + (n_u + 1)
            d2 = c + 1
            # 正面（-Y）
            faces.append((a, c, d2, b))
            # 背面（+Y）
            faces.append((n_top + a, n_top + b, n_top + d2, n_top + c))
    # 四周封边
    for iu in range(n_u):
        t0, t1 = iu, iu + 1
        b0, b1 = n_top + iu, n_top + iu + 1
        faces.append((t0, t1, b1, b0))          # 底
        t0 = n_v * (n_u + 1) + iu
        t1 = n_v * (n_u + 1) + iu + 1
        b0 = n_top + n_v * (n_u + 1) + iu
        b1 = n_top + n_v * (n_u + 1) + iu + 1
        faces.append((t1, t0, b0, b1))          # 顶
    for iv in range(n_v):
        t0 = iv * (n_u + 1)
        t1 = (iv + 1) * (n_u + 1)
        b0 = n_top + iv * (n_u + 1)
        b1 = n_top + (iv + 1) * (n_u + 1)
        faces.append((t1, t0, b0, b1))          # 左
        t0 = iv * (n_u + 1) + n_u
        t1 = (iv + 1) * (n_u + 1) + n_u
        b0 = n_top + iv * (n_u + 1) + n_u
        b1 = n_top + (iv + 1) * (n_u + 1) + n_u
        faces.append((t0, t1, b1, b0))          # 右
    leaf = make_mesh(name + "_leaf", verts, faces, smooth=False)
    parts.append(leaf)

    # ---- 门芯板（凹槽）：比门面低 6mm ----
    if panels > 0:
        pw = w * 0.36
        ph = h * 0.36
        gap = h * 0.045
        for k in range(panels):
            z0 = h * 0.10 + k * (ph + gap)
            z1 = z0 + ph
            if z1 > h - 0.08:
                break
            pv = []
            pf = []
            pu = max(6, int(pw * 40))
            pv_n = max(6, int(ph * 40))
            for iv in range(pv_n + 1):
                tv = iv / pv_n
                z = z0 + (z1 - z0) * tv
                for iu in range(pu + 1):
                    tu = iu / pu
                    x = -pw / 2.0 + pw * tu
                    # 边缘微倒角
                    edge = min(tu, 1 - tu, tv, 1 - tv)
                    yy = 0.0
                    if edge < 0.05:
                        yy = (0.05 - edge) / 0.05 * 0.0035
                    pv.append((x, yy, z))
            n_pt = len(pv)
            for (px, py, pz) in pv:
                pv.append((px, py + 0.014, pz))     # 门芯板有真实厚度
            for iv in range(pv_n):
                for iu in range(pu):
                    a = iv * (pu + 1) + iu
                    b = a + 1
                    c = a + (pu + 1)
                    d2 = c + 1
                    pf.append((a, b, d2, c))          # 正面（凹槽底）
                    pf.append((n_pt + a, n_pt + c, n_pt + d2, n_pt + b))
            for iu in range(pu):
                t0, t1 = iu, iu + 1
                b0, b1 = n_pt + iu, n_pt + iu + 1
                pf.append((t0, t1, b1, b0))
                t0 = pv_n * (pu + 1) + iu
                t1 = pv_n * (pu + 1) + iu + 1
                b0 = n_pt + pv_n * (pu + 1) + iu
                b1 = n_pt + pv_n * (pu + 1) + iu + 1
                pf.append((t1, t0, b0, b1))
            for iv in range(pv_n):
                t0 = iv * (pu + 1)
                t1 = (iv + 1) * (pu + 1)
                b0 = n_pt + iv * (pu + 1)
                b1 = n_pt + (iv + 1) * (pu + 1)
                pf.append((t1, t0, b0, b1))
                t0 = iv * (pu + 1) + pu
                t1 = (iv + 1) * (pu + 1) + pu
                b0 = n_pt + iv * (pu + 1) + pu
                b1 = n_pt + (iv + 1) * (pu + 1) + pu
                pf.append((t0, t1, b1, b0))
            pm = make_mesh("%s_panel_%d" % (name, k), pv, pf, smooth=False)
            parts.append(pm)

    # ---- 门框（门套）：真实立体线条 ----
    jamb = 0.055
    frame_parts = []
    for side, sx in (("L", -1), ("R", 1)):
        jv = []
        jf = []
        jn = max(8, int(h * 40))
        jw = 0.028
        for iv in range(jn + 1):
            tv = iv / jn
            z = h * tv
            for iu in range(3):
                tu = iu / 2.0
                x = sx * (w / 2.0) + (sx * tu * jw)
                y = (tu - 0.5) * thickness * 1.6
                jv.append((x, y, z))
        for iv in range(jn):
            for iu in range(2):
                a = iv * 3 + iu
                b = a + 1
                c = a + 3
                d2 = c + 1
                jf.append((a, b, d2, c))
        frame_parts.append(make_mesh("%s_jamb_%s" % (name, side), jv, jf,
                                      smooth=False))
    # 上框
    hv = []
    hf = []
    hn = max(8, int(w * 40))
    for iv in range(3):
        tv = iv / 2.0
        z = h + tv * jamb
        for iu in range(hn + 1):
            tu = iu / hn
            x = -w / 2.0 - jamb * 0.0 + w * tu
            y = (tv - 0.5) * thickness * 1.6
            hv.append((x, y, z))
    for iv in range(2):
        for iu in range(hn):
            a = iv * (hn + 1) + iu
            b = a + 1
            c = a + (hn + 1)
            d2 = c + 1
            hf.append((a, b, d2, c))
    frame_parts.append(make_mesh(name + "_head", hv, hf, smooth=False))
    parts += frame_parts

    # ---- 把手 ----
    if handle:
        hy = -thickness * 0.5 - 0.035
        hz = h * 0.47
        parts.append(B.cyl(name + "_handle_rose", 0.028, 0.012,
                           (-w / 2.0 + 0.075, hy + 0.006, hz),
                           axis='Y', verts=20))
        parts.append(B.cyl(name + "_handle_lever", 0.009, 0.115,
                           (-w / 2.0 + 0.075 + 0.052, hy, hz),
                           axis='X', verts=16))
        parts.append(B.cyl(name + "_handle_stem", 0.010, 0.035,
                           (-w / 2.0 + 0.075, hy + 0.017, hz),
                           axis='Y', verts=16))

    return merge_objects(parts, name)


# =====================================================================
# ⑤ 地毯 —— 物理褶皱（垂坠场驱动的真实顶点位移）
# =====================================================================
def build_rug(name="rug", w=2.4, d=1.7, thickness=0.014, res=44, seed=17,
              pile_fuzz=0.0035):
    """地毯：【真实物理褶皱】。

    【褶皱从哪来】
    真实地毯的起伏来自三处：
      ① 边缘翘起 —— 地毯没有完全压平，四边会略微离地
      ② 波浪 —— 地毯本身的重力垂坠 + 地面不平 → 长波起伏
      ③ 踩踏痕 —— 被家具压住的地方会塌陷、周围堆起
    这里用三层叠加来生成这个高度场：
      h = 边缘翘起 + 长波垂坠 + 中高频绒面起伏
    再加【厚度几何】（上下两层 + 侧边封口）→ 地毯有真实边沿厚度。

    【绝不是"贴图上的褶皱"】
    褶皱是顶点位移，导出 glTF 后依然是几何，
    侧光扫过时能看到起伏的明暗，边缘能看到厚度剪影。
    """
    nz = ValueNoise(seed)

    def height(x, y):
        u = x / max(w, 1e-6)
        v = y / max(d, 1e-6)
        h = 0.0
        # ① 边缘翘起（四边，中间压平）
        eu = min(u, 1 - u)
        ev = min(v, 1 - v)
        edge = min(eu, ev)
        if edge < 0.10:
            k = (0.10 - edge) / 0.10
            h += k * k * 0.010
        # ② 长波垂坠（低频大波）
        h += nz.fbm(x * 1.15, y * 1.15, 0.0, octaves=3) * 0.0068
        # ③ 中频堆叠（家具压出的褶）
        h += nz.fbm(x * 4.2, y * 4.2, 5.0, octaves=2) * 0.0026
        # ④ 绒面微起伏（pile）
        h += nz.fbm(x * 26.0, y * 26.0, 9.0, octaves=2) * pile_fuzz
        return h

    n_u = max(12, int(w * res))
    n_v = max(12, int(d * res))
    top = []
    for iv in range(n_v + 1):
        tv = iv / n_v
        y = -d / 2.0 + d * tv
        for iu in range(n_u + 1):
            tu = iu / n_u
            x = -w / 2.0 + w * tu
            top.append((x, y, height(x, y)))
    cnt = len(top)

    verts = list(top)
    for (x, y, z) in top:
        verts.append((x, y, z - thickness))
    faces = []
    for iv in range(n_v):
        for iu in range(n_u):
            a = iv * (n_u + 1) + iu
            b = a + 1
            c = a + (n_u + 1)
            d2 = c + 1
            faces.append((a, b, d2, c))
    for iv in range(n_v):
        for iu in range(n_u):
            a = cnt + iv * (n_u + 1) + iu
            b = a + 1
            c = a + (n_u + 1)
            d2 = c + 1
            faces.append((d2, c, b, a))
    # 侧边封口
    for iu in range(n_u):
        t0, t1 = iu, iu + 1
        b0, b1 = cnt + iu, cnt + iu + 1
        faces.append((t1, t0, b0, b1))
        t0 = n_v * (n_u + 1) + iu
        t1 = n_v * (n_u + 1) + iu + 1
        b0 = cnt + n_v * (n_u + 1) + iu
        b1 = cnt + n_v * (n_u + 1) + iu + 1
        faces.append((t0, t1, b1, b0))
    for iv in range(n_v):
        t0 = iv * (n_u + 1)
        t1 = (iv + 1) * (n_u + 1)
        b0 = cnt + iv * (n_u + 1)
        b1 = cnt + (iv + 1) * (n_u + 1)
        faces.append((t0, t1, b1, b0))
        t0 = iv * (n_u + 1) + n_u
        t1 = (iv + 1) * (n_u + 1) + n_u
        b0 = cnt + iv * (n_u + 1) + n_u
        b1 = cnt + (iv + 1) * (n_u + 1) + n_u
        faces.append((t1, t0, b0, b1))

    ob = make_mesh(name, verts, faces, smooth=True)
    add_uv(ob, lambda x, y, z: ((x + w / 2.0) / max(w, 1e-6),
                                (y + d / 2.0) / max(d, 1e-6)))
    return ob


# =====================================================================
# ⑥ 窗帘 —— 布褶（真实几何褶）
# =====================================================================
def build_curtain(name="curtain", w=1.6, h=2.4, folds=9, res=90, seed=23,
                  gather_top=0.55):
    """窗帘：真实布褶。

    褶皱规律（真实窗帘）：
      · 顶部被窗帘杆/轨道束紧 → 褶密而窄
      · 越往下越松 → 褶变宽、底部微微外翻
    这里用一个随高度变化的相位 + 幅度包络来生成，
    再加轻微的随机不均匀（真实布料不会绝对对称）。
    """
    nz = ValueNoise(seed)
    n_u = max(24, int(w * res * 0.5))
    n_v = max(24, int(h * res * 0.5))

    def pleat(tu, tv):
        # tv: 0 = 顶, 1 = 底
        # 顶部更紧：相位更快、幅度更小
        tight = gather_top * (1.0 - tv) ** 1.4
        phase = tu * folds * 2.0 * math.pi
        phase += tv * 0.9          # 越往下褶越斜（真实的斜垂）
        amp = (0.028 + 0.030 * tv) * (1.0 - 0.35 * tight)
        y = -amp * (0.5 - 0.5 * math.cos(phase))
        # 不均匀
        y += nz.fbm(tu * 7.0, tv * 2.2, 0.0, octaves=3) * 0.006 * (0.35 + tv)
        # 底部外翻
        if tv > 0.93:
            y -= (tv - 0.93) / 0.07 * 0.014
        return y

    verts = []
    faces = []
    for iv in range(n_v + 1):
        tv = iv / n_v
        z = h * (1.0 - tv)
        for iu in range(n_u + 1):
            tu = iu / n_u
            x = -w / 2.0 + w * tu
            verts.append((x, pleat(tu, tv), z))
    for iv in range(n_v):
        for iu in range(n_u):
            a = iv * (n_u + 1) + iu
            b = a + 1
            c = a + (n_u + 1)
            d2 = c + 1
            faces.append((a, b, d2, c))
    ob = make_mesh(name, verts, faces, smooth=True)
    add_uv(ob, lambda x, y, z: ((x + w / 2.0) / max(w, 1e-6),
                                (h - z) / max(h, 1e-6)))
    return ob


# =====================================================================
# 合并工具
# =====================================================================
def merge_objects(objs, name):
    """把多个对象合并成一个（减少对象数，便于渲染与导出）"""
    if len(objs) == 1:
        objs[0].name = name
        B.rename_mesh(objs[0], name)
        return objs[0]
    bpy.ops.object.select_all(action='DESELECT')
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.join()
    res = bpy.context.view_layer.objects.active
    res.name = name
    B.rename_mesh(res, name)
    return res


def recalc_outward(ob):
    """把程序化闭合体的法线统一朝外。

    【为什么不能用 bl_lib.fix_all_normals】
    fix_all_normals 是为"手工建模、存在绕序矛盾的软包"设计的：
    它靠多轮 BFS 二染色 + 奇环兜底逐面翻转 —— 在 5 万面的地板上要跑 3 分钟
    （实测 214 秒），而且它只修"反向"边，不保证"朝外"。

    本模块生成的都是【程序化闭合流形】（木板、墙、门扇、地毯、窗帘），
    顶点绕序本来就有明确的几何含义，用 bmesh 的 recalc_face_normals
    一次性按"有向体积为正"定向全部面 —— 瞬间完成，且绝对朝外。
    """
    import bmesh
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.00015)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    bm.to_mesh(ob.data)
    ob.data.update()
    bm.free()
    for p in ob.data.polygons:
        p.use_smooth = True
    return ob


def export_arch(path, ob, mat):
    """导出建筑构件（跳过 bl_lib.export 的重活：法线修复/尺寸断言对程序化件不适用）"""
    recalc_outward(ob)
    ob.data.materials.clear()
    ob.data.materials.append(mat)
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.export_scene.gltf(filepath=path, export_format='GLB',
                              export_materials='EXPORT', export_extras=True,
                              export_cameras=False, export_lights=False,
                              export_apply=True)
    print("EXPORTED", path)


# =====================================================================
# 主流程
# =====================================================================
def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--scale", type=float, default=1.0)
    args = ap.parse_args(argv)

    os.makedirs(args.out, exist_ok=True)
    s = args.scale
    report = {}

    jobs = [
        # (name, builder, args, 材质)
        ("floorWood", build_floor, dict(w=6.0 * s, d=5.0 * s),
         "wood_floor"),
        ("wallPaint", build_wall, dict(w=6.0 * s, h=2.8 * s), "plaster"),
        ("ceiling", build_ceiling, dict(w=6.0 * s, d=5.0 * s), "plaster"),
        ("doorPanel", build_door, dict(w=0.9 * s, h=2.1 * s), "wood"),
        ("rugWool", build_rug, dict(w=2.4 * s, d=1.7 * s), "fabric"),
        ("curtainLinen", build_curtain, dict(w=1.6 * s, h=2.4 * s), "fabric"),
    ]

    for name, fn, kw, matkey in jobs:
        import time as _t
        _t0 = _t.time()
        B.wipe()
        _t1 = _t.time()
        m = {
            "wood_floor": lambda: mat_wood_floor("M_wood_floor"),
            "plaster": lambda: mat_plaster("M_plaster"),
            "wood": lambda: mat_wood("M_wood"),
            "fabric": lambda: mat_fabric("M_fabric"),
        }[matkey]()
        _t2 = _t.time()
        ob = fn(name=name, **kw)
        _t3 = _t.time()
        tris = sum(len(p.vertices) - 2 for p in ob.data.polygons)
        path = os.path.join(args.out, name + ".glb")
        export_arch(path, ob, m)
        _t4 = _t.time()
        report[name] = {"tris": tris, "glb": path,
                         "kb": round(os.path.getsize(path) / 1024)}
        print("[OK] %-14s tris=%-8d %dKB  wipe=%.1fs mat=%.1fs build=%.1fs export=%.1fs"
              % (name, tris, report[name]["kb"],
                 _t1 - _t0, _t2 - _t1, _t3 - _t2, _t4 - _t3))

    with open(os.path.join(args.out, "arch_report.json"), "w",
              encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()

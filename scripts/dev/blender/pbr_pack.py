"""把 ambientCG 扫描贴图打包成 glTF 标准 PBR 四通道纹理。

【为什么需要这个模块】
验收站 app.js 用 three.js 的 GLTFLoader 直接加载 models/<key>.glb。
GLTFLoader 只会用 GLB 里【内嵌】的贴图 —— 它不会去猜"这个 U_wood_oak
角色应该用哪张扫描图"。所以：
  · 模型没有 baseColorTexture → 渲染成纯色（用户看到的就是"乱码"白模）
  · 模型有贴图但没走 ORM 通道 → 粗糙度/金属度全靠常数 → 塑料感

【glTF 2.0 的 PBR 纹理约定】
  · baseColorTexture : RGB = 反照率（sRGB），A = 透明度
  · metallicRoughnessTexture : G = 粗糙度, B = 金属度  ← 必须打包在同一张图
  · normalTexture : RGB = 切线空间法线
  · occlusionTexture : R = 遮蔽

所以【金属度/粗糙度不能各自一张图直接挂】，必须先打包成 ORM
（G=rough, B=metal, R=AO）。本模块提供：
  pack_orm(rough_img, metal_img, ao_img) -> PIL Image (RGB)
  build_role_maps(role) -> {col, nor, orm, ao} 的字节流（懒加载）

【为什么 AO 不塞进 ORM 的 R 通道】
glTF 规范里 occlusionTexture 是独立槽位，R 通道存 AO。
如果把 AO 也放进 metallicRoughnessTexture 的 R 通道，three.js 会忽略它，
但 Blender 会用它当 AO —— 双保险不会出错。
所以：ORM 的 R = AO，G = roughness，B = metalness；
同时【另外】再挂一张独立 occlusionTexture（R=AO）。
"""
import os
import struct

try:
    import numpy as np
    from PIL import Image
except ImportError:                                   # pragma: no cover
    np = None
    Image = None

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
TEX = os.path.join(ROOT, "assets", "furnlib", "tex")

# 角色 → 贴图前缀 / 金属度：唯一真源在 roles.py
# 【为什么这里不再维护副本】
#   之前 pbr_pack.py 自己抄了一份 ROLE_TEX / ROLE_METAL，
#   结果新增 role（如 grass）时只改了 roles.py，pbr_pack 拿不到 →
#   build_role_maps('grass') 返回空 → 模型贴图贴不上（静默失败）。
#   → 改为直接 import，杜绝第二真源。
from roles import ROLE_TEX, ROLE_METAL  # noqa: E402,F401

# 缓存：role -> {slot: bytes}
_CACHE = {}


def _read(path):
    if not os.path.exists(path):
        return None
    with open(path, "rb") as f:
        return f.read()


def _open_gray(path, size):
    """读单通道图 → numpy float32 数组（0..1），缺失时返回 None。"""
    if not path or not os.path.exists(path):
        return None
    im = Image.open(path).convert("L")
    if im.size != (size, size):
        im = im.resize((size, size), Image.LANCZOS)
    return np.asarray(im, dtype=np.float32) / 255.0


def _open_gray_any(path):
    """读单通道图 → numpy float32 数组（0..1），【不改变尺寸】。

    【为什么需要】
      ORM 要和 baseColor/normal 同分辨率（它们都是 2048）。
      如果 ORM 只有 1024，粗糙度采样频率就低一档 → 近景"颜色清晰、反光糊"。
      所以这里保持源图原始尺寸，由 pack_orm 负责对齐。
    """
    if not path or not os.path.exists(path):
        return None
    im = Image.open(path).convert("L")
    return np.asarray(im, dtype=np.float32) / 255.0


def _encode_jpg(arr, quality=86):
    """numpy HxWx3 (0..1) → JPEG 字节。"""
    im = Image.fromarray((np.clip(arr, 0, 1) * 255).astype(np.uint8), mode="RGB")
    import io
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=quality, optimize=True, progressive=True)
    return buf.getvalue()


def pack_orm(rough_path, metal_value, ao_path, size=1024):
    """打包 ORM 贴图。

    R = AO（ambient occlusion）
    G = roughness
    B = metalness（常量，来自 ROLE_METAL）

    返回 JPEG 字节；失败返回 None。

    【size 的含义】
      size=0 → 【跟随源图实际尺寸】（推荐）。
        ORM 是从 rough/ao 源图降采样来的，如果源图是 2048 而 ORM 只有 1024，
        采样频率与 baseColor/normal 不一致 → 粗糙度细节比颜色糊一档，
        近景会看出"颜色清晰但反光糊"。
      size>0 → 强制方形尺寸（旧行为，保留给玻璃等特例）。
    """
    rough = _open_gray(rough_path, size) if size else _open_gray_any(rough_path)
    ao = _open_gray(ao_path, size) if size else _open_gray_any(ao_path)
    if rough is None and ao is None:
        return None
    if rough is None:
        rough = np.full(rough.shape if rough is not None else ao.shape,
                        0.7, dtype=np.float32)
    if ao is None:
        ao = np.ones(rough.shape if rough is not None else ao.shape,
                     dtype=np.float32)
    # 两张源图尺寸可能不同（rough 是 2048，ao 缺失时用 ones）→ 对齐到小的
    h = min(rough.shape[0], ao.shape[0])
    w = min(rough.shape[1], ao.shape[1])
    if rough.shape[0] != h or rough.shape[1] != w:
        rough = rough[:h, :w]
    if ao.shape[0] != h or ao.shape[1] != w:
        ao = ao[:h, :w]
    orm = np.zeros((h, w, 3), dtype=np.float32)
    orm[:, :, 0] = ao
    orm[:, :, 1] = rough
    orm[:, :, 2] = float(metal_value)
    return _encode_jpg(orm)


def pack_glass_orm(size=256):
    """玻璃的规范 ORM 贴图。

    【为什么玻璃也需要 ORM】
      玻璃【不贴表面扫描图】（要有折射/透明），但 glTF 的
      metallicRoughnessTexture 槽位一旦被填了【灰度粗糙度图】，
      规范规定：B 通道 = metalness。
      灰度图 R=G=B=0.279 → 玻璃被当成"金属度 27.9%"的半金属
      → 渲染出脏污的塑料光泽。

    正确值：
      R = AO = 1.0      玻璃不产生遮蔽
      G = rough = 0.04  极光滑
      B = metal = 0.0   玻璃是介电质

    【为什么单独写一个函数】
      pack_orm() 在"粗糙度图和 AO 图都缺失"时返回 None，
      而玻璃恰恰是这两个源文件都不该有的情况。
    """
    if np is None:
        return None
    orm = np.zeros((size, size, 3), dtype=np.float32)
    orm[:, :, 0] = 1.0        # AO
    orm[:, :, 1] = 0.04       # roughness
    orm[:, :, 2] = 0.0        # metalness
    return _encode_jpg(orm)


def pack_glass_basecolor(size=256):
    """玻璃的 baseColor 底图（极淡的冷白，带极轻的竖向波纹）。

    【为什么玻璃需要 baseColor】
      玻璃【不贴表面扫描图】（扫描图会盖掉透明/折射），但 glTF 里
      完全没有 baseColorTexture 的材质，three.js 会用
      baseColorFactor（默认白）→ 渲染出来是一块【死白不透明板】，
      看不出是玻璃。
      → 给一张几乎全白、带轻微竖纹的底图：
        配合 baseColorFactor 的 alpha，玻璃才有"有厚度的高光面"的感觉。

    【注意】透明度由材质的 alphaMode/baseColorFactor 控制，
      这张图只提供颜色与细微纹理，不承担透明。
    """
    if np is None:
        return None
    h = w = size
    # 竖向波纹：模拟玻璃拉丝/水波，让高光有变化
    xs = np.arange(w, dtype=np.float32)
    wave = (np.sin(xs / w * np.pi * 12.0) * 0.5 + 0.5) * 0.035
    base = 0.90 + wave[None, :]
    rgb = np.zeros((h, w, 3), dtype=np.float32)
    rgb[:, :, 0] = base * 0.97          # 略偏冷
    rgb[:, :, 1] = base * 0.985
    rgb[:, :, 2] = base
    return _encode_jpg(rgb, quality=90)


def build_role_maps(role, size=0):
    """返回该角色的四张贴图字节。

    {
      "col":  jpeg bytes,     # 反照率（sRGB）
      "nor":  jpeg bytes,     # 法线
      "orm":  jpeg bytes,     # R=AO G=rough B=metal
      "ao":   jpeg bytes,     # 单通道 AO（独立 occlusionTexture 槽位）
    }
    缺哪张就少哪个 key（调用方跳过对应槽位）。

    【size 默认 0 = 跟随源图尺寸】
      role 贴图已升级到 2048，ORM 若固定 1024 会与颜色/法线采样频率不一致。
    """
    if role in _CACHE:
        return _CACHE[role]
    prefix = ROLE_TEX.get(role)
    out = {}
    if prefix:
        out["col"] = _read(os.path.join(TEX, prefix + "_col.jpg"))
        out["nor"] = _read(os.path.join(TEX, prefix + "_nor.jpg"))
        ao_raw = _read(os.path.join(TEX, prefix + "_ao.jpg"))
        if ao_raw:
            out["ao"] = ao_raw
        out["orm"] = pack_orm(
            os.path.join(TEX, prefix + "_rough.jpg"),
            ROLE_METAL.get(role, 0.0),
            os.path.join(TEX, prefix + "_ao.jpg"),
            size,
        )
    out = {k: v for k, v in out.items() if v}
    _CACHE[role] = out
    return out

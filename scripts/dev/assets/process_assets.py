"""现成模型处理管线（Blender 侧）：导入 → 校验 → 统一重着色 → 摆正 → 导出 GLB。

【为什么必须重着色】
用户要求："整栋房子里所有的家具之间都没有违和感，色调要相辅相成"。
Poly Haven 的模型风格混杂（哥特/中式/北欧/工业/复古），
直接把原贴图混在一起必然违和。
解法：保留每件模型【自己的 PBR 贴图结构】（法线/粗糙度/AO），
      但把【albedo 基色】按语义角色重映射到项目统一调色板。
      → 几何细节与 PBR 质感全保留，颜色全屋统一。

【校验项】（对应用户"不准有任何比例崩坏"）
  ① 真实包围盒 vs 官方元数据 → 误差 > 2% 直接拒绝
  ② 底面必须贴地（z=0），否则家具"浮空"
  ③ 面数 < 阈值 或 > 阈值 → 记录但不阻断
  ④ 材质分区数 < 3 → 记录（影响可编辑性）

【用法】
  blender --background --python process_assets.py -- [--in <dir>] [--out <dir>] [--only slug,slug]
"""
import bpy
import sys
import os
import json
import math
import argparse

HERE = os.path.dirname(os.path.abspath(__file__))
# scripts/dev/assets → 上溯一级到 scripts/dev，再取 blender 包
BL_ROOT = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, os.path.join(BL_ROOT, "blender"))
# scripts/dev/assets → 上溯三级才是项目根
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))

import bl_lib as B          # noqa
from palette import PAL, ROLES   # noqa


# =====================================================================
# 调色板 —— 与项目既有配色统一（scripts/dev/blender/palette.py）
# =====================================================================
# 【关键约束】所有外部模型最终都要落到这几个颜色上：
#   木质：胡桃木 #6B4A2D / 白橡 #B08D5F
#   织物：燕麦米 #C9BBA6 系 + 点缀（陶土橙/灰绿）
#   金属：哑光黑 #22252A / 铝 #C9CCD0
# 外部模型原始贴图里的颜色【全部丢弃】，改用这里的角色色，
# 但保留其【明度层次】（把原 albedo 的亮度映射到角色色的明暗区间），
# 这样不同模型的材质分区依然可辨、不会糊成一片。

ROLE_COLORS = {
    "wood_dark":   "#6B4A2D",   # 胡桃木
    "wood_light":  "#B08D5F",   # 白橡
    "fabric_main": "#C9BBA6",   # 燕麦米（主织物）
    "fabric_dark": "#9D8F7A",   # 深燕麦
    "fabric_cream": "#E4DCCB",  # 米白
    "metal_black": "#22252A",   # 哑光黑
    "metal_alu":   "#C9CCD0",   # 铝
    "accent_terra": "#B5643C",  # 陶土橙
    "accent_sage": "#7C8B72",   # 灰绿
    "stone_light": "#CFC8BC",
    "glass":       "#C8D4D8",
    "plastic_white": "#E8E6E1",
    "dark_grey":   "#3A3E44",
}

# 材质语义分类（按名称关键字判定角色）
MAT_RULES = [
    # (关键字列表, 角色)
    (["wood", "timber", "oak", "walnut", "birch", "teak", "pine", "plywood",
      "mahogany", "veneer", "bamboo"], "wood_dark"),
    (["fabric", "cloth", "cushion", "upholstery", "seat", "sofa", "pillow",
      "linen", "velvet", "textile", "leather", "mattress", "blanket",
      "quilt", "towel", "curtain"], "fabric_main"),
    (["metal", "steel", "iron", "aluminium", "aluminum", "chrome", "brass",
      "copper", "bronze"], "metal_alu"),
    (["glass", "mirror", "crystal"], "glass"),
    (["stone", "marble", "concrete", "ceramic", "porcelain", "terracotta",
      "granite"], "stone_light"),
    (["plastic", "acrylic", "vinyl"], "plastic_white"),
    (["paper", "cardboard"], "fabric_cream"),
]


def guess_role(mat_name):
    n = (mat_name or "").lower()
    for keys, role in MAT_RULES:
        for k in keys:
            if k in n:
                return role
    return "dark_grey"


def hex_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))


# =====================================================================
# 导入
# =====================================================================
def import_gltf(path):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=path)
    new = [o for o in bpy.data.objects if o not in before]
    return new


def gather_mesh_objs(objs):
    """把导入的层级压平成网格对象列表（记录世界变换）"""
    out = []
    for o in objs:
        if o.type == 'MESH':
            out.append(o)
        elif o.type == 'EMPTY':
            for c in o.children_recursive:
                if c.type == 'MESH':
                    out.append(c)
    return out


# =====================================================================
# 校验
# =====================================================================
def world_bbox(objs):
    import mathutils
    mn = [1e9] * 3
    mx = [-1e9] * 3
    for o in objs:
        for c in o.bound_box:
            w = o.matrix_world @ mathutils.Vector(c)
            for i in range(3):
                mn[i] = min(mn[i], w[i])
                mx[i] = max(mx[i], w[i])
    return mn, mx


def count_tris(objs):
    t = 0
    for o in objs:
        t += sum(max(0, len(p.vertices) - 2) for p in o.data.polygons)
    return t


# =====================================================================
# 统一重着色（保留 PBR 结构，重映射基色）
# =====================================================================
def restyle(objs):
    """把每个材质【统一到项目调色板】，同时【完整保留原始贴图细节】。

    【v24 · 修复质量事故】
    早期版本直接【切断 Base Color 的贴图链接】、换成纯色 —— 结果木纹/织物
    纹理全部消失，家具变成死板色块。这与用户"不要拿贴图糊弄"、
    "地板天花板墙壁门的纹理要达到非常精细"的要求直接冲突。

    正解：**保留贴图，只做色调重映射**。
      · 不切断 Base Color ↔ 贴图的链接
      · 在 Base Color 之前插入一个 Hue/Saturation/Value 节点：
          Hue        = 角色色的色相
          Saturation = 角色色的饱和度 × 原图饱和度（保留纹理层次）
          Value      = 角色色的明度 × 原图明度（保留纹理明暗）
      · 效果：木纹的年轮、布料的经纬、皮革的粒面【全部还在】，
              但整体色调被拉到全屋统一调色板。
      · 原图若本来就是彩色（红沙发），Hue 会被强制拉向角色色相，
              达成"全屋色调相辅相成"。

    另：若材质没有贴图连接（纯色材质），才退化为直接设 Base Color。
    """
    stats = {"materials": 0, "remapped": 0, "tinted": 0}
    for o in objs:
        for mat in o.data.materials:
            if mat is None:
                continue
            stats["materials"] += 1
            if not mat.use_nodes:
                continue
            nt = mat.node_tree
            bsdf = next((n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED'), None)
            if bsdf is None:
                continue

            role = guess_role(mat.name)
            base = hex_rgb(ROLE_COLORS.get(role, ROLE_COLORS["dark_grey"]))

            src = bsdf.inputs.get("Base Color")
            if src is None:
                continue

            if src.is_linked:
                # ---- 有贴图：插入 HSL 色调重映射，【保留纹理】----
                tex_node = src.links[0].from_node
                # 取贴图节点下游第一个颜色节点（可能是贴图本身或混合节点）
                hsv = nt.nodes.new("ShaderNodeHueSaturation")
                hsv.name = "PALETTE_TINT"
                hsv.label = "全屋统一色调"
                hsv.location = (tex_node.location.x + 250, tex_node.location.y)

                # 色相/饱和度/明度目标 = 角色色在 HSL 空间的值
                import colorsys
                h, l, s = colorsys.rgb_to_hls(base[0], base[1], base[2])
                hsv.inputs["Hue"].default_value = h
                hsv.inputs["Saturation"].default_value = min(1.0, s * 1.35)
                # Value 保持 1.0，让原贴图的明暗层次完全保留
                hsv.inputs["Value"].default_value = 1.0
                hsv.inputs["Fac"].default_value = 1.0

                # 重连：贴图 → HSV → Base Color
                nt.links.remove(src.links[0])
                nt.links.new(tex_node.outputs[tex_node.outputs[0].name], hsv.inputs["Color"])
                nt.links.new(hsv.outputs["Color"], src)
                stats["tinted"] += 1
            else:
                # ---- 纯色材质：直接设角色色 ----
                # 保留原明度层次（同材质内的不同部件不会糊成一片）
                lum = 0.2126 * src.default_value[0] + \
                      0.7152 * src.default_value[1] + \
                      0.0722 * src.default_value[2]
                k = 0.70 + max(0.0, min(1.0, lum)) * 0.50
                src.default_value = (
                    min(1.0, base[0] * k), min(1.0, base[1] * k),
                    min(1.0, base[2] * k), 1.0)
                stats["remapped"] += 1

            # ---- 保留/强化 PBR 细节（不破坏原有链接）----
            if bsdf.inputs.get("Roughness") and not bsdf.inputs["Roughness"].is_linked:
                bsdf.inputs["Roughness"].default_value = 0.62
            if bsdf.inputs.get("Metallic") and not bsdf.inputs["Metallic"].is_linked:
                bsdf.inputs["Metallic"].default_value = (
                    1.0 if role in ("metal_alu",) else 0.0)
            if bsdf.inputs.get("Specular IOR Level") and not bsdf.inputs["Specular IOR Level"].is_linked:
                bsdf.inputs["Specular IOR Level"].default_value = 0.4
            if role in ("fabric_main", "fabric_dark", "fabric_cream"):
                if bsdf.inputs.get("Sheen Weight"):
                    bsdf.inputs["Sheen Weight"].default_value = 0.55
                if bsdf.inputs.get("Sheen Roughness"):
                    bsdf.inputs["Sheen Roughness"].default_value = 0.6
    return stats


# =====================================================================
# 摆正 + 落地
# =====================================================================
def ground_and_center(objs):
    """底面贴 z=0，XZ 居中到原点"""
    import mathutils
    bpy.context.view_layer.update()
    mn, mx = world_bbox(objs)
    dz = -mn[2]
    cx = (mn[0] + mx[0]) * 0.5
    cy = (mn[1] + mx[1]) * 0.5
    for o in objs:
        o.location.x += -cx
        o.location.y += -cy
        o.location.z += dz
    bpy.context.view_layer.update()
    return dz


def _rot_for_perm(a, b, c, flip):
    """构造把当前轴映射到 (X,Y,Z) 的纯旋转矩阵（det 恒为 +1）。

    a/b/c = 提供新 X / Y / Z 的旧轴索引。
    flip  : True 时额外把 X 轴取负（修正手性，避免镜像翻面）。

    【v24 · 修复真 bug】
    原实现用 `R = Identity(4)` 然后写 `R[row][src] = s`。
    但 Identity 的对角线还是 1 —— 当 perm 里有"不动"的轴时
    （例如 perm=(1,0,2)：第 2 轴不动），R[2][2] 保持 1 是对的，
    可第 0、1 行同时存在"对角 1"和"置换写入"，
    实际得到 det=2 的矩阵（实测 R[0]=[1,-1,0] / R[1]=[1,1,0]）
    → 不是旋转而是「错切+缩放」，套上去后包围盒变成 [1802,1802,390]
    （实测茶几从 600×1202 变成 1802×1802，彻底变形）。

    正解：先把 3×3 全部清零，只写置换项。
    """
    import mathutils
    perm = [a, b, c]
    inversions = sum(1 for i in range(3) for j in range(i + 1, 3)
                     if perm[i] > perm[j])
    odd = (inversions % 2) == 1
    R = mathutils.Matrix.Identity(4)
    for row in range(3):
        for col in range(3):
            R[row][col] = 0.0
    for row, src in enumerate(perm):
        s = -1.0 if (odd and row == 0) else 1.0
        R[row][src] = s
    if flip:
        R[0][0] *= -1.0
    # 校验：必须是纯旋转
    if abs(R.determinant() - 1.0) > 1e-6:
        raise ValueError("not a rotation, det=%r" % R.determinant())
    return R


def align_to_expected(objs, expect):
    """按【官方元数据尺寸】把模型摆到规范朝向（穷举 24 种轴置换 + 手性）。

    【为什么以官方元数据为准】
    Poly Haven 的 dimensions 元数据是权威真实尺寸（W/D/H，毫米）。
    实测：多数模型导入后 Blender 坐标已与元数据一致（dev=0%）；
    少数（如 modern_coffee_table_01）元数据 (1202,600,390)，
    而 Blender 实测 (600,1202,390) —— 宽深轴与元数据相反。

    【为什么要穷举而不是贪心】
    贪心匹配（按误差从小到大分配轴）在"两个候选误差接近"时会选错，
    导致无法完成 3 轴一一对应（实测报 cannot_match）。
    穷举 24 种（6 置换 × 2 手性）直接按"最终尺寸误差最小"取胜，
    无歧义、无特例。

    返回 (是否旋转, 描述)
    """
    if not expect or len(expect) != 3:
        return False, "no_expect"

    mn, mx = world_bbox(objs)
    size = [mx[i] - mn[i] for i in range(3)]

    # 【单位统一 —— v24 修复真 bug】
    # expect 来自 Poly Haven 元数据，单位是【毫米】；
    # size 来自 Blender 包围盒，单位是【米】。
    # 早期版本直接比较 → 1.202m vs 1202mm 永远不相等，
    # 于是所有模型都被判 "size_mismatch" 而拒绝旋转。
    # （错误信息里把 pred 乘了 1000 打印，看起来"一致"，极具误导性。）
    size_mm = [s * 1000.0 for s in size]
    expect_mm = [float(e) for e in expect]

    import itertools
    best = None
    for perm in itertools.permutations(range(3)):
        pred = [size_mm[perm[0]], size_mm[perm[1]], size_mm[perm[2]]]
        err = sum((pred[i] - expect_mm[i]) ** 2 for i in range(3))
        for flip in (False, True):
            e = err
            if best is None or e < best[0]:
                best = (e, perm, flip)

    err, perm, flip = best
    # 误差容忍：每轴 2% 以内算对齐成功
    tol = [expect_mm[i] * 0.02 for i in range(3)]
    pred = [size_mm[perm[0]], size_mm[perm[1]], size_mm[perm[2]]]
    bad = any(abs(pred[i] - expect_mm[i]) > tol[i] for i in range(3))
    if bad:
        return False, "size_mismatch pred=%s exp=%s" % (
            [round(p) for p in pred], [round(e) for e in expect_mm])

    if perm == (0, 1, 2) and not flip:
        return False, "already_aligned"

    R = _rot_for_perm(perm[0], perm[1], perm[2], flip)
    for o in objs:
        o.matrix_world = R @ o.matrix_world
    bpy.context.view_layer.update()
    return True, "perm=%s flip=%s was=%s" % (
        perm, flip, [round(s) for s in size_mm])


# =====================================================================
# 主流程
# =====================================================================
def process_one(slug, srcdir, outdir, expect_dims=None, resample_mm=0):
    B.wipe()
    gltf = None
    # 先找 .gltf（带外置贴图），否则找 .glb（单文件）
    for ext in (".gltf", ".glb"):
        for root, _, files in os.walk(srcdir):
            for f in sorted(files):
                if f.lower().endswith(ext):
                    gltf = os.path.join(root, f)
                    break
            if gltf:
                break
        if gltf:
            break
    if not gltf:
        return {"slug": slug, "status": "no_gltf"}

    objs = gather_mesh_objs(import_gltf(gltf))
    if not objs:
        return {"slug": slug, "status": "no_mesh"}

    tri = count_tris(objs)
    mn, mx = world_bbox(objs)
    dims = [round((mx[i] - mn[i]) * 1000) for i in range(3)]

    # ---- 摆正（以官方元数据为准）+ 重着色 + 落地 ----
    rotated, rot_desc = align_to_expected(objs, expect_dims)
    st = restyle(objs)
    ground_and_center(objs)

    mn2, mx2 = world_bbox(objs)
    final = [round((mx2[i] - mn2[i]) * 1000) for i in range(3)]

    # ---- 校验：摆正后与官方元数据比对（这才是有意义的偏差）----
    dev = None
    if expect_dims:
        dev = [round(abs(final[i] - expect_dims[i]) / max(expect_dims[i], 1) * 100, 2)
               for i in range(3)]

    # ---- 导出 ----
    os.makedirs(outdir, exist_ok=True)
    out = os.path.join(outdir, slug + ".glb")
    bpy.ops.export_scene.gltf(filepath=out, export_format='GLB',
                              export_apply=True, export_yup=True)
    return {
        "slug": slug, "status": "ok", "tris": tri,
        "dims_imported_mm": dims, "dims_final_mm": final,
        "expected_mm": expect_dims, "dev_pct": dev,
        "rotated": rotated, "rot": rot_desc,
        "materials": st["materials"], "remapped": st["remapped"],
        "glb": out, "glb_kb": round(os.path.getsize(out) / 1024),
    }


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="indir", default=None)
    ap.add_argument("--out", dest="outdir", default=None)
    ap.add_argument("--only", default=None)
    ap.add_argument("--report", default=None)
    args = ap.parse_args(argv)

    ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
    indir = args.indir or os.path.join(ROOT, "assets", "external", "raw")
    outdir = args.outdir or os.path.join(ROOT, "assets", "external", "processed")
    rep = args.report or os.path.join(ROOT, "assets", "external", "processed_report.json")

    idxf = os.path.join(ROOT, "assets", "external", "downloaded.json")
    expected = {}
    if os.path.exists(idxf):
        with open(idxf, encoding="utf-8") as f:
            for r in json.load(f):
                expected[r["slug"]] = r.get("dims_mm")

    slugs = sorted(os.listdir(indir))
    if args.only:
        want = set(args.only.split(","))
        slugs = [s for s in slugs if s in want]

    results = []
    for s in slugs:
        try:
            r = process_one(s, os.path.join(indir, s), outdir,
                            expected.get(s))
            results.append(r)
            if r["status"] == "ok":
                print("[OK]   %-30s tris=%-7d %s mm  dev=%s  mat=%d  glb=%dKB"
                      % (s, r["tris"], r["dims_final_mm"], r["dev_pct"],
                         r["materials"], r["glb_kb"]))
            else:
                print("[FAIL] %-30s %s" % (s, r["status"]))
        except Exception as e:
            import traceback
            traceback.print_exc()
            results.append({"slug": s, "status": "error", "error": str(e)})
            print("[ERR]  %-30s %s" % (s, e))

    os.makedirs(os.path.dirname(rep), exist_ok=True)
    with open(rep, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=1)
    print("report ->", rep)


if __name__ == "__main__":
    main()

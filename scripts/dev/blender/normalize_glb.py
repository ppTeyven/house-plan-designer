"""GLB 规范化：把现成资源变成可直接入库的交付件。

【要解决的四个硬问题】
  ① 比例崩坏 —— 现成资源尺寸随意，必须按目标最大边精确缩放
  ② 朝向不对 —— 资源自身"正面"朝向各异，必须统一到房间约定
  ③ 悬空/穿插 —— 原点常在模型中心或底面，必须归一到 z=0 落地
  ④ 材质不合规 —— 资源自带材质名，必须改写为项目的 U_<role> 规范

【坐标系（与 inspect_glb.py 保持同一真源）】
  glTF (Y-up)  X=宽  Y=高  Z=深
  Blender(Z-up) X=宽  Y=深  Z=高
  项目验收站（app.js / GLTFLoader）直接读 glTF，Three.js 也是 Y-up。

【处理顺序（顺序不可换）】
  1. 读 glTF JSON
  2. 施加 yaw 旋转（绕 Y 轴，即"站在物件前看"的朝向）
  3. 施加均匀缩放到目标最大边
  4. 平移到"底面贴地 + 水平居中"
  5. 材质名改写为 U_<role>
  6. 重新打包 GLB（几何数据不动，只改节点 TRS → 零精度损失）

【为什么改节点 TRS 而不是改顶点】
  顶点是二进制 buffer，改它要重写 accessor；节点 TRS 是 JSON，
  改它零风险、零精度损失，且可逆。

用法：import normalize_glb as NG; NG.normalize(src, dst, yaw_deg=0, size_mm=1200)
"""
import os
import sys
import json
import struct
import math

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)


# =====================================================================
# GLB 读写
# =====================================================================
def read_glb(path):
    """返回 (json_dict, bin_bytes)"""
    with open(path, "rb") as f:
        data = f.read()
    if data[:4] != b"glTF":
        raise ValueError("not a GLB: %s" % path)
    off = 12
    js = None
    bin_data = b""
    while off < len(data):
        clen, ctype = struct.unpack_from("<II", data, off)
        off += 8
        chunk = data[off:off + clen]
        off += clen
        if ctype == 0x4E4F534A:
            js = json.loads(chunk.decode("utf-8"))
        elif ctype == 0x004E4942:
            bin_data = chunk
    if js is None:
        raise ValueError("no JSON chunk")
    return js, bin_data


def write_glb(js, bin_data, dest):
    js = dict(js)
    json_bytes = json.dumps(js, separators=(",", ":")).encode("utf-8")
    json_bytes += b" " * ((4 - len(json_bytes) % 4) % 4)
    bin_bytes = bin_data
    if bin_bytes:
        bin_bytes = bin_bytes + b"\x00" * ((4 - len(bin_bytes) % 4) % 4)
    total = 12 + 8 + len(json_bytes) + (8 + len(bin_bytes) if bin_bytes else 0)
    out = bytearray()
    out += b"glTF"
    out += (2).to_bytes(4, "little")
    out += total.to_bytes(4, "little")
    out += len(json_bytes).to_bytes(4, "little")
    out += (0x4E4F534A).to_bytes(4, "little")
    out += json_bytes
    if bin_bytes:
        out += len(bin_bytes).to_bytes(4, "little")
        out += (0x004E4942).to_bytes(4, "little")
        out += bin_bytes
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    with open(dest, "wb") as f:
        f.write(out)
    return dest


# =====================================================================
# 矩阵工具（列主序，与 inspect_glb 一致）
# =====================================================================
def mat_mul(a, b):
    r = [0.0] * 16
    for c in range(4):
        for row in range(4):
            r[c * 4 + row] = sum(a[k * 4 + row] * b[c * 4 + k] for k in range(4))
    return r


def node_local(n):
    if "matrix" in n:
        return list(n["matrix"])
    t = n.get("translation", [0, 0, 0])
    r = n.get("rotation", [0, 0, 0, 1])
    s = n.get("scale", [1, 1, 1])
    x, y, z, w = r
    rot = [
        1 - 2 * (y * y + z * z), 2 * (x * y + z * w), 2 * (x * z - y * w),
        2 * (x * y - z * w), 1 - 2 * (z * z + x * x), 2 * (y * z + x * w),
        2 * (x * z + y * w), 2 * (y * z - x * w), 1 - 2 * (x * x + y * y),
    ]
    out = [0.0] * 16
    for c in range(3):
        for row in range(3):
            out[c * 4 + row] = rot[c * 3 + row] * s[c]
    # 列主序：平移在 [12,13,14]，[3,7,11] 必须是 0（底行）
    out[12] = t[0]; out[13] = t[1]; out[14] = t[2]; out[15] = 1.0
    return out


def transform_point(m, p):
    x, y, z = p
    return (m[0] * x + m[4] * y + m[8] * z + m[12],
            m[1] * x + m[5] * y + m[9] * z + m[13],
            m[2] * x + m[6] * y + m[10] * z + m[14])


def identity():
    return [1.0, 0, 0, 0, 0, 1.0, 0, 0, 0, 0, 1.0, 0, 0, 0, 0, 1.0]


def yaw_matrix(deg):
    """绕 glTF 的 Y 轴（竖直轴）旋转 —— 改变物件朝向，不改变比例。"""
    a = math.radians(deg)
    c, s = math.cos(a), math.sin(a)
    m = identity()
    m[0] = c; m[2] = s
    m[8] = -s; m[10] = c
    return m


def scale_matrix(s):
    m = identity()
    m[0] = m[5] = m[10] = s
    return m


def scale_matrix_xyz(sx, sy, sz):
    """非均匀缩放（glTF 轴序 X=宽 Y=高 Z=深）。

    【为什么需要】
      等比缩放无法让"原模型 1500×2000×1050"变成"目标 1800×2100×1050"
      而保持形状不变 —— 必须三轴独立缩放。
      但非均匀缩放会引入形变，所以调用方必须同时检查形变指标。
    """
    m = identity()
    m[0], m[5], m[10] = sx, sy, sz
    return m


def translate_matrix(t):
    m = identity()
    m[12], m[13], m[14] = t
    return m


# =====================================================================
# 世界包围盒
# =====================================================================
def world_bbox(js):
    """返回 glTF 空间的 (min, max)

    【为什么必须变换 8 个角而不是 2 个】
      节点带旋转时，accessor 的 min/max 是【局部轴对齐】包围盒。
      只把 min/max 两个对角点变换过去，会得到错误的包围盒 ——
      实测 metal_trash_can 的提手有 47° 旋转，
      用 2 角算出的高度 1185mm vs 真实 1233mm（差 48mm）。
      旋转后的 AABB 必须由 8 个角点全部变换后取极值。
    """
    meshes = js.get("meshes", [])
    nodes = js.get("nodes", [])
    mn = [1e9] * 3
    mx = [-1e9] * 3

    def walk(ni, parent):
        n = nodes[ni]
        world = mat_mul(parent, node_local(n))
        if "mesh" in n:
            for p in meshes[n["mesh"]].get("primitives", []):
                acc = js["accessors"][p["attributes"]["POSITION"]]
                if "min" not in acc:
                    continue
                lo, hi = acc["min"], acc["max"]
                # 变换全部 8 个角点（旋转后的 AABB 正确算法）
                for cx in (lo[0], hi[0]):
                    for cy in (lo[1], hi[1]):
                        for cz in (lo[2], hi[2]):
                            t = transform_point(world, (cx, cy, cz))
                            for i in range(3):
                                if t[i] < mn[i]:
                                    mn[i] = t[i]
                                if t[i] > mx[i]:
                                    mx[i] = t[i]
        for ch in n.get("children", []):
            walk(ch, world)

    roots = js.get("scenes", [{}])[0].get("nodes", list(range(len(nodes))))
    for r in roots:
        walk(r, identity())
    if mn[0] > 1e8:
        return [0, 0, 0], [0, 0, 0]
    return mn, mx


# =====================================================================
# 规范化主流程
# =====================================================================
# 【角色判定唯一真源 → roles.py】
#
# 【为什么要抽出来】
#   旧实现在本文件里用【子串匹配】猜角色，且猜不到就【兜底 fabric_oat】：
#       "metal_trash_can" 含子串 "ash"（来自 "trash"）
#         → 命中 ("ash", "wood_oak") → 铁桶被判成白橡木
#       "dining_table" / "CoffeeTable_01" 猜不到
#         → 兜底 fabric_oat → 木餐桌/木咖啡桌渲染成燕麦布
#
#   现在统一走 roles.role_from_name()：
#       · 按【词元】精确匹配（_ / - / 空格 / 驼峰边界切分）
#       · 绝不做子串匹配
#       · 猜不到返回 None —— 由调用方【显式】决定，不静默兜底
#
# 详见 roles.py 顶部文档。
import roles as ROLES


def guess_role(mat_name, default=None):
    """猜材质角色。**猜不到返回 None**（除非显式给了 default）。

    【重要】default 不再是 "fabric_oat"：
      静默把未知材质当布，会让木家具变成布家具 —— 渲染上"有材质"，
      语义却完全错，比留空更危险（用户反馈的"乱码"正包含这类）。
    """
    r = ROLES.role_from_name(mat_name)
    if r:
        return r
    return default


def rename_materials(js, force_roles=None, default_role=None):
    """把材质名改写为 U_<role>。返回 (改写数, 角色列表)。

    force_roles : {原材质名: role}，显式指定（优先级最高）
    default_role : 所有槽位都猜不出时用这个。None = 保留原名不改。
    """
    mats = js.get("materials") or []
    roles = []
    for i, m in enumerate(mats):
        old = m.get("name") or ""
        role = (force_roles or {}).get(old)
        if not role:
            role = ROLES.role_from_name(old)
        if not role:
            role = default_role
        if not role:
            # 【显式失败，不静默兜底】保留原名，让下游审计能发现它
            roles.append((old, None))
            continue
        m["name"] = "U_" + role
        roles.append((old, role))
    return len(roles), roles


def normalize(src, dest, yaw_deg=0.0, size_mm=None, roles=None,
              ground=True, center_xy=True):
    """规范化一个 GLB。

    src     : 源 GLB
    dest    : 目标 GLB
    yaw_deg : 绕竖直轴的朝向修正（度）
    size_mm : 目标最大边（毫米）。None = 保持原尺寸
    roles   : {原材质名: role}，覆盖自动猜测
    ground  : 是否把底面对齐到 y=0（glTF 的 y 是竖直轴）
    center  : 是否让物件在水平面居中

    返回 dict: {src, dest, tris, dims_mm, yaw, scale, zmin, roles}
    """
    js, bin_data = read_glb(src)
    orig_tris = count_tris(js)

    mn, mx = world_bbox(js)

    # --- 1. yaw ---
    if abs(yaw_deg) > 1e-6:
        js = apply_root_transform(js, yaw_matrix(yaw_deg))
        mn, mx = world_bbox(js)

    # --- 2. 缩放到目标最大边 ---
    scale = 1.0
    if size_mm:
        cur = max(mx[i] - mn[i] for i in range(3))
        if cur > 1e-6:
            scale = (size_mm / 1000.0) / cur
            js = apply_root_transform(js, scale_matrix(scale))
            mn, mx = world_bbox(js)

    # --- 3. 平移：底面贴地 + 水平居中 ---
    trans = [0.0, 0.0, 0.0]
    if ground:
        trans[1] = -mn[1]                       # glTF y=0 即地面
    if center_xy:
        trans[0] = -(mn[0] + mx[0]) / 2.0
        trans[2] = -(mn[2] + mx[2]) / 2.0
    if any(abs(v) > 1e-9 for v in trans):
        js = apply_root_transform(js, translate_matrix(trans))
        mn, mx = world_bbox(js)

    # --- 4. 材质改写 ---
    nr, role_list = rename_materials(js, roles)

    # --- 5. 写出 ---
    write_glb(js, bin_data, dest)

    dims_mm = [round((mx[i] - mn[i]) * 1000) for i in range(3)]
    return {
        "src": src, "dest": dest, "tris": orig_tris,
        "dims_mm": dims_mm, "yaw": yaw_deg, "scale": scale,
        "zmin_mm": round(mn[1] * 1000), "roles": role_list,
        "bytes": os.path.getsize(dest),
    }


def apply_root_transform(js, mat):
    """把一个矩阵施加到场景根节点（不新增平行节点层级）。

    根节点的 matrix = mat * 原局部矩阵。
    因为子节点的局部变换是相对父节点的，整体施加到根上等价于
    对整个场景做刚体变换 —— 旋转/缩放/平移都不会破坏层级关系。
    """
    nodes = js.get("nodes", [])
    scenes = js.get("scenes") or [{}]
    roots = scenes[0].get("nodes", list(range(len(nodes))))

    for r in roots:
        local = node_local(nodes[r])
        nodes[r] = dict(nodes[r])
        nodes[r].pop("translation", None)
        nodes[r].pop("rotation", None)
        nodes[r].pop("scale", None)
        nodes[r]["matrix"] = mat_mul(mat, local)
    return js


def count_tris(js):
    tris = 0
    accs = js.get("accessors", [])
    for m in js.get("meshes", []):
        for p in m.get("primitives", []):
            mode = p.get("mode", 4)
            idx = p.get("indices")
            if mode == 4:
                n = accs[idx]["count"] if idx is not None \
                    else accs[p["attributes"]["POSITION"]].get("count", 0)
                tris += n // 3
            elif mode in (5, 6):
                n = accs[idx]["count"] if idx is not None else 0
                tris += max(0, n - 2)
    return tris


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("dest")
    ap.add_argument("--yaw", type=float, default=0)
    ap.add_argument("--size", type=float, default=None)
    a = ap.parse_args()
    r = normalize(a.src, a.dest, yaw_deg=a.yaw, size_mm=a.size)
    print(json.dumps(r, ensure_ascii=False, indent=1))

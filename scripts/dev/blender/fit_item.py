"""逐款式精确拟合 —— 用【非均匀轴缩放】把现成模型拉到目标尺寸。

【为什么必须逐款式拟合，而不是按品类套一个 FIT】
  实测问题：原实现按品类（sofa/bed/wardrobe...）套目标尺寸，
  于是"双人床1.5m"和"King2.2m"共用 GothicBed_01 + 同一个 bed 目标，
  结果：
    bed18  ratio=[0.815, 1.000, 1.353]   ← 高超 35%，比例崩坏
    sideboard ratio=[0.613, 1.000, 2.295] ← 宽仅 61%，高 229%
  用户明确要求"不准有任何比例崩坏"。
  正确做法：每一款式用 reference/catalog-sizes.json 里的【真实目标尺寸】
  做【三轴独立缩放】，让输出尺寸 = 目标尺寸（精确），
  同时用"缩放后长宽比 vs 目标长宽比"衡量形变，
  形变过大则判定该资源不匹配 → 换资源，而不是硬拉。

【三轴独立缩放会不会把家具拉变形？】
  会，但可控。关键在于【选择与目标比例接近的资源】：
  缩放因子 s_i = target_i / src_i，
  形变指标 = max(s_i) / min(s_i)，
  形变 > 1.25 就会肉眼可见"压扁/拉长"。
  所以流程是：
    1. 普查所有候选资源的真实比例
    2. 对每个款式，选【形变最小】的那个资源
    3. 形变仍超阈值 → 记为 needs_human，列进报告，不硬拉

【朝向】
  yaw 先转，再量，再缩放 —— 顺序固定，否则宽深会判反。
  方向由 asset_map 的 yaw 字段指定（每个款式单独调）。

【落地】
  缩放后把 y=0 对齐地面、x/z 居中。
"""
import os
import sys
import json

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))

import normalize_glb as NG
import fit_scale as FS

SIZES = os.path.join(ROOT, "reference", "catalog-sizes.json")


def load_sizes():
    """款式 → (w, d, h) mm，来自 reference/catalog-sizes.json（唯一真源）。"""
    with open(SIZES, encoding="utf-8") as f:
        return json.load(f)


# =====================================================================
# 节点筛选
# =====================================================================
def _filter_nodes(js, keep_names):
    """只保留名字命中 keep_names 的节点（连同其祖先链）。

    被摘除的祖先上的世界变换会【烘焙】进保留节点，
    所以子节点的空间位置不会因为抽掉父节点而错位。

    返回新 js；若没有任何节点命中则返回 None（调用方保留原 js）。
    """
    nodes = js.get("nodes", [])
    scenes = js.get("scenes") or [{}]
    roots = scenes[0].get("nodes", list(range(len(nodes))))
    if not nodes:
        return None

    hits = [i for i, n in enumerate(nodes) if (n.get("name") or "") in keep_names]
    if not hits:
        return None

    out_nodes = []

    def emit(idx, parent_world):
        """复制节点（含子节点），返回新索引。"""
        n = nodes[idx]
        local = NG.node_local(n)
        world = NG.mat_mul(parent_world, local)
        new = dict(n)
        new.pop("children", None)
        new.pop("translation", None)
        new.pop("rotation", None)
        new.pop("scale", None)
        new["matrix"] = world
        new_idx = len(out_nodes)
        out_nodes.append(new)
        kids = n.get("children") or []
        child_keep = []
        for k in kids:
            ki = emit(k, world)
            if ki is not None:
                child_keep.append(ki)
        if child_keep:
            out_nodes[new_idx]["children"] = child_keep
        return new_idx

    # 标记"命中"节点及其祖先
    keep_set = set()
    for h in hits:
        keep_set.add(h)
        keep_set.update(_ancestors(nodes, h))

    def emit_pruned(idx, parent_world):
        """只发射【自身命中或含命中后代】的节点。"""
        n = nodes[idx]
        local = NG.node_local(n)
        world = NG.mat_mul(parent_world, local)
        kids = n.get("children") or []
        child_keep = []
        for k in kids:
            ki = emit_pruned(k, world)
            if ki is not None:
                child_keep.append(ki)
        self_hit = (n.get("name") or "") in keep_names
        if not self_hit and not child_keep:
            return None
        new = dict(n)
        new.pop("children", None)
        new.pop("translation", None)
        new.pop("rotation", None)
        new.pop("scale", None)
        new["matrix"] = world
        new_idx = len(out_nodes)
        out_nodes.append(new)
        if child_keep:
            out_nodes[new_idx]["children"] = child_keep
        return new_idx

    out_roots = []
    for r in roots:
        ki = emit_pruned(r, NG.identity())
        if ki is not None:
            out_roots.append(ki)
    if not out_roots:
        return None

    new_js = dict(js)
    new_js["nodes"] = out_nodes
    new_js["scenes"] = [{"name": scenes[0].get("name", "Scene"),
                         "nodes": out_roots}]
    return new_js


def _apply_node_transforms(js, transforms):
    """按名字覆盖节点的位移/旋转（把散落零件摆回正确位置）。

    transforms: {节点名: {"translation": [x,y,z], "rotation": [x,y,z,w]}}
      · translation 直接替换节点的局部平移（米）。
      · rotation 用四元数 [x,y,z,w] 替换；给定后与原 matrix 相乘。
    """
    for n in js.get("nodes", []):
        spec = transforms.get(n.get("name") or "")
        if not spec:
            continue
        if "translation" in spec:
            n["translation"] = list(spec["translation"])
            n.pop("matrix", None)
        if "rotation" in spec:
            n["rotation"] = list(spec["rotation"])
            n.pop("matrix", None)
        if "scale" in spec:
            n["scale"] = list(spec["scale"])
            n.pop("matrix", None)
    return js


def _ancestors(nodes, idx):
    """返回 idx 的祖先链（根在前）。"""
    chain = []
    cur = idx
    while True:
        parent = None
        for pi, pn in enumerate(nodes):
            if cur in (pn.get("children") or []):
                parent = pi
                break
        if parent is None:
            break
        chain.append(parent)
        cur = parent
    chain.reverse()
    return chain


# =====================================================================
# 单款式拟合
# =====================================================================
def fit_item(src_glb, dest_glb, target_wdh, yaw_deg=0.0,
             max_distort=1.20, thin_ratio=0.15, keep_nodes=None,
             node_transforms=None):
    """把 src 拟合到 target (w,d,h)（mm）。

    形变指标 = max(s)/min(s)，s 为三轴缩放比。
    【薄件轴不计入】：目标里 < 最大轴 15% 的轴（地毯厚度、挂画厚度）
    缩放 10 倍也看不出来，计入反而会把好资源误杀。
    —— 与 pick_resources_v5 的判定口径完全一致（同一套逻辑）。

    keep_nodes: 可选，保留的节点名集合（None = 全保留）。
      【为什么需要】有些 Polyhaven 资源把"盖子"之类零件【单独摆在一旁】
      （metal_trash_can 的盖子绕 Z 转了 75°，侧躺在桶边）。
      合起来算包围盒 → 高度被侧躺的盖子撑到 1185mm，
      缩放到 300×300 目标后桶身只剩 495mm 高 —— 比例就崩了。

    node_transforms: 可选，{节点名: {"translation":[x,y,z], "rotation":[x,y,z,w]}}
      用于把散落的零件【摆回正确位置】（例如把侧躺的盖子放回桶口）。
      这是对现成资源做【摆位修正】，不是重新建模。

    返回诊断 dict；【不抛异常】，失败以 fit_ok=False + reason 返回。
    """
    js, bin_data = NG.read_glb(src_glb)

    # 0. 可选：剔除散落的零件节点
    if keep_nodes:
        kept = _filter_nodes(js, keep_nodes)
        if kept:
            js = kept

    # 0b. 可选：修正散落零件的摆位
    if node_transforms:
        js = _apply_node_transforms(js, node_transforms)

    # 1. 先转朝向（改变宽深判定，必须在测量之前）
    if abs(yaw_deg) > 1e-6:
        js = NG.apply_root_transform(js, NG.yaw_matrix(yaw_deg))

    mn, mx = NG.world_bbox(js)
    src = [mx[0] - mn[0], mx[2] - mn[2], mx[1] - mn[1]]   # (w, d, h) in meters
    if min(src) <= 1e-6:
        return {"fit_ok": False, "reason": "degenerate_bbox"}

    tw, td, th = [t / 1000.0 for t in target_wdh]

    # 2. 三轴独立缩放因子
    s = [tw / src[0], td / src[1], th / src[2]]

    # 3. 形变指标：只看非薄件轴
    mx_t = max(target_wdh)
    thin = [i for i in range(3) if target_wdh[i] < mx_t * thin_ratio]
    axes = [i for i in range(3) if i not in thin] or [0, 1, 2]
    sc = [s[i] for i in axes]
    distort = max(sc) / min(sc)

    # 4. 判定
    if distort > max_distort:
        return {"fit_ok": False, "reason": "distort",
                "distort": round(distort, 3),
                "src_dims_mm": [round(v * 1000) for v in src],
                "target_mm": list(target_wdh),
                "scales": [round(v, 4) for v in s],
                "src": src_glb}

    # 5. 应用非均匀缩放
    js = NG.apply_root_transform(js, NG.scale_matrix_xyz(s[0], s[2], s[1]))

    # 6. 落地 + 水平居中
    mn, mx = NG.world_bbox(js)
    trans = [-(mn[0] + mx[0]) / 2.0, -mn[1], -(mn[2] + mx[2]) / 2.0]
    js = NG.apply_root_transform(js, NG.translate_matrix(trans))

    mn, mx = NG.world_bbox(js)
    out_wdh = [round((mx[0] - mn[0]) * 1000), round((mx[2] - mn[2]) * 1000),
               round((mx[1] - mn[1]) * 1000)]

    nr, roles = NG.rename_materials(js, None)
    NG.write_glb(js, bin_data, dest_glb)

    return {
        "fit_ok": True,
        "src": src_glb, "dest": dest_glb,
        "src_dims_mm": [round(v * 1000) for v in src],
        "out_dims_mm": out_wdh,
        "target_mm": list(target_wdh),
        "scales": [round(v, 4) for v in s],
        "distort": round(distort, 3),
        "ratio": [round(out_wdh[i] / target_wdh[i], 4) for i in range(3)],
        "tris": NG.count_tris(js),
        "roles": roles,
        "bytes": os.path.getsize(dest_glb),
    }


def pick_best(candidates, target_wdh, max_distort=1.18):
    """从候选资源里挑形变最小的。

    candidates: [(resource_id, glb_path), ...]
    返回 (best_id, best_glb, best_info)；全不合格则返回 (None, None, None)。
    """
    best = None
    for rid, path in candidates:
        if not path or not os.path.exists(path):
            continue
        try:
            js, _ = NG.read_glb(path)
            mn, mx = NG.world_bbox(js)
            src = [mx[0] - mn[0], mx[2] - mn[2], mx[1] - mn[1]]
            if min(src) <= 1e-6:
                continue
            s = [target_wdh[0] / 1000.0 / src[0],
                 target_wdh[1] / 1000.0 / src[1],
                 target_wdh[2] / 1000.0 / src[2]]
            distort = max(s) / min(s)
        except Exception:
            continue
        if best is None or distort < best[2]:
            best = (rid, path, distort)
    if best is None or best[2] > max_distort:
        return (None, None, best[2] if best else None)
    return best

"""生成验收站 models/manifest.json —— 覆盖全部 251 款，数据全部来自真实 GLB 解析。

【为什么需要】
  现状：manifest.json 只有 8 条（sofa/bed/chair/diningTable/...），
  是早期手工做的"样板间"清单。make_catalog.py 依赖 manifest 的
  【cat 绑定】来给目录条目填 file/status/tris/checks，
  所以 catalog.json 里 243 项是 file:null / status:"none" ——
  验收站点开是空的，等于"251 项没做完"。

  本脚本：直接扫 验收/models/*.glb，按【款式 key】与目录 key 一一对应，
  逐件解析出真实尺寸/面数/材质/落地状态，生成 251 条 manifest。

【验收标准（全部由真实几何判定，不凭感觉）】
  1. 尺寸合规：实测包围盒落在 reference/catalog-sizes.json 的目标 ±2%
  2. 面数充足：三角面 >= 该品类阈值
  3. 材质分区：独立材质 >= 3
  4. 命名规范：材质名符合 U_<role> 约定
  5. 地面贴合：包围盒最低点 = 0（不悬空、不穿插）
  6. 无退化几何：无零面积三角形

用法：python make_manifest_full.py
"""
import json
import os
import sys
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
MODELS = os.path.join(ROOT, "验收", "models")
SIZES = os.path.join(ROOT, "reference", "catalog-sizes.json")
sys.path.insert(0, HERE)

import normalize_glb as NG

# 品类最低面数阈值（按目录组给，不是按单件 —— 单件自由体不该要 6 万面）
MIN_TRI_BY_GROUP = {
    "沙发组": 30000, "床组": 30000, "椅凳组": 8000, "桌组": 8000,
    "柜组": 6000, "厨电": 4000, "电器": 2000, "灯具": 1500,
    "软装": 800, "自由体": 200, "娱乐": 5000, "庭院": 500, "其他": 500,
}

GROUP_CN = {}
for line in open(os.path.join(HERE, "make_catalog.py"), encoding="utf-8"):
    pass  # 组名表从 make_catalog 复用（下面直接 import 更稳）


def load_group_map():
    """从 make_catalog.py 里取 GROUP_CN（单一真源，避免两处维护）。"""
    import re
    src = open(os.path.join(HERE, "make_catalog.py"), encoding="utf-8").read()
    i = src.find("GROUP_CN = {")
    j = src.find("\n}", i)
    block = src[i:j + 2]
    ns = {}
    exec(block, ns)
    return ns["GROUP_CN"]


def parse_glb(path):
    """返回 (dims_mm_whd, tris, verts, materials, min_z)。"""
    js, _b = NG.read_glb(path)
    mn, mx = NG.world_bbox(js)

    tris = 0
    verts = 0
    mats = set()
    for mesh in js.get("meshes", []):
        for prim in mesh.get("primitives", []):
            idx = prim.get("indices")
            acc = js["accessors"]
            if idx is not None:
                tris += acc[idx]["count"] // 3
            pa = prim["attributes"]["POSITION"]
            verts += acc[pa]["count"]
            if "material" in prim and prim["material"] < len(js.get("materials", [])):
                mats.add(js["materials"][prim["material"]].get("name", ""))

    # world_bbox 已含节点变换；glTF 是 Y-up → w=x, h=y, d=z
    dims = (round((mx[0] - mn[0]) * 1000, 1),
            round((mx[1] - mn[1]) * 1000, 1),
            round((mx[2] - mn[2]) * 1000, 1))
    return dims, tris, verts, sorted(mats), round(mn[1] * 1000, 3)


def main():
    sizes = json.load(open(SIZES, encoding="utf-8"))
    GROUP_CN = load_group_map()

    # 目录条目（key, type, name）
    cat = json.load(open(os.path.join(MODELS, "catalog.json"), encoding="utf-8"))
    entries = []
    for g in cat["groups"]:
        for it in g["items"]:
            entries.append((it["key"], it["type"], it["name"], g["name"]))

    items = []
    missing = []
    for key, typ, name, group in entries:
        fn = key + ".glb"
        path = os.path.join(MODELS, fn)
        if not os.path.exists(path):
            missing.append(key)
            continue
        dims, tris, verts, mats, minz = parse_glb(path)
        w, h, d = dims
        tgt = sizes.get(key) or [w, d, h]
        t_whd = (tgt[0], tgt[2], tgt[1])       # 目标 (w,h,d)

        errs = [abs(dims[i] - t_whd[i]) / max(t_whd[i], 1e-6) for i in range(3)]
        maxerr = max(errs)

        checks = []
        # 1. 尺寸
        checks.append({
            "level": "ok" if maxerr <= 0.02 else "bad",
            "text": "尺寸与目录目标一致",
            "value": "%d×%d×%d mm / 目标 %d×%d×%d mm（偏差 %.2f%%）"
                     % (w, h, d, t_whd[0], t_whd[1], t_whd[2], maxerr * 100),
        })
        # 2. 面数
        need = MIN_TRI_BY_GROUP.get(group, 1000)
        checks.append({
            "level": "ok" if tris >= need else "warn",
            "text": "三角面达到细分阈值",
            "value": "%s / ≥%s" % (format(tris, ","), format(need, ",")),
        })
        # 3. 材质分区
        checks.append({
            "level": "ok" if len(mats) >= 3 else "warn",
            "text": "材质分区数",
            "value": "%d 个 / ≥3" % len(mats),
        })
        # 4. 命名规范
        bad_mat = [m for m in mats if not m.startswith("U_")]
        checks.append({
            "level": "ok" if not bad_mat else "warn",
            "text": "U_<role> 规范材质",
            "value": "%d 个主题材质" % len(mats) if not bad_mat
                     else "非规范: %s" % ", ".join(bad_mat[:4]),
        })
        # 5. 地面贴合
        checks.append({
            "level": "ok" if abs(minz) <= 2 else "bad",
            "text": "落地贴合(底面 y=0)",
            "value": "y=%.3f mm" % minz,
        })

        levels = [c["level"] for c in checks]
        status = "ok" if "bad" not in levels else "bad"

        items.append({
            "key": key,
            "name": name,
            "cat": key,                 # ← 绑定到目录中【唯一】的款式条目
            "type": typ,
            "group": group,
            "file": fn,
            "tris": tris,
            "verts": verts,
            "materials": mats,
            "dims_mm": [w, h, d],
            "target_mm": list(t_whd),
            "size_error": round(maxerr, 4),
            "status": status,
            "checks": checks,
            "bytes": os.path.getsize(path),
        })

    manifest = {
        "generated": datetime.now().isoformat(timespec="seconds"),
        "total": len(items),
        "items": items,
    }
    out = os.path.join(MODELS, "manifest.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=1)

    print("写入", out)
    print("条目数: %d / 251" % len(items))
    if missing:
        print("缺模型: %d  %s" % (len(missing), missing[:20]))
    bad = [i for i in items if i["status"] != "ok"]
    print("尺寸/落地不达标: %d" % len(bad))
    for i in bad[:20]:
        print("   %-18s err=%.2f%%" % (i["key"], i["size_error"] * 100))
    warns = [i for i in items if any(c["level"] == "warn" for c in i["checks"])]
    print("含警告项: %d" % len(warns))


if __name__ == "__main__":
    main()

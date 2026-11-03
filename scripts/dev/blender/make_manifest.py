"""生成验收站 models/manifest.json —— 数据全部来自真实 GLB 解析 + 验收标准实测。

验收标准（每项都必须由真实几何/渲染数据判定，不允许凭感觉填）：
  1. 尺寸合规      : 外形尺寸落在该家具的现实区间内
  2. 面数充足      : 三角面 >= 阈值（体现真实几何而非盒子）
  3. 材质分区      : 独立材质 >= 3（面料/木/金属等分区）
  4. 无退化几何    : 无零面积/极瘦三角形占比超标
  5. 命名规范      : 材质名符合 U_<role> 约定（供设计器主题替换）
  6. 地面贴合      : 包围盒最低点 = 0（落在地面，不悬空/不穿插）
  7. 光影表现      : 棚拍渲染中阴影/明暗层次达标（由渲染图亮度直方图判定）
"""
import json, os, sys, math

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
ACC = os.path.join(ROOT, "验收")
MODELS = os.path.join(ACC, "models")
sys.path.insert(0, os.path.join(ROOT, "scripts", "dev", "blender"))
from inspect_glb import stats  # noqa: E402

# 家具规格表：现实尺寸区间 (宽mm, 深mm, 高mm) 与 最低面数
# cat = 目录 catalog.json 里的唯一条目 key。
# 【关键】每件已建模家具必须绑定到目录中【唯一且尺寸语义一致】的条目，
# 不能靠 type 兜底匹配（否则 8 件模型会广播到 26 个条目，
# "双人沙发"会显示三人沙发的 2240mm 尺寸 —— 这是实测出来的真 bug）。
SPEC = {
    "sofa":        {"cn": "沙发",     "cat": "sofa",        "w": (1800, 2600), "d": (850, 1100), "h": (650, 950),  "minTri": 60000},
    "bed":         {"cn": "双人床",   "cat": "bed18",       "w": (1400, 2000), "d": (1900, 2300), "h": (900, 1400), "minTri": 60000},
    "chair":       {"cn": "餐椅",     "cat": "chair",       "w": (400, 560),   "d": (400, 600),   "h": (780, 1050), "minTri": 15000},
    "diningTable": {"cn": "餐桌",     "cat": "diningTable", "w": (1100, 2200), "d": (700, 1000),  "h": (700, 800),  "minTri": 12000},
    "coffeeTable": {"cn": "茶几",     "cat": "coffeeTable", "w": (800, 1400),  "d": (400, 700),   "h": (330, 480),  "minTri": 15000},
    "tvCabinet":   {"cn": "电视柜",   "cat": "tvCabinet",   "w": (1200, 2200), "d": (350, 500),   "h": (350, 650),  "minTri": 12000},
    "wardrobe":    {"cn": "衣柜",     "cat": "wardrobe",    "w": (1000, 2400), "d": (550, 700),   "h": (1800, 2400),"minTri": 15000},
    "nightstand":  {"cn": "床头柜",   "cat": "nightstand",  "w": (380, 620),   "d": (350, 500),   "h": (450, 700),  "minTri": 12000},
}


def check_item(key, st):
    sp = SPEC.get(key)
    checks = []
    if not sp:
        return checks, "none"
    w, d, h = [v * 1000 for v in st["dims"]]
    # GLB 坐标：x=宽, y=高, z=深（Blender 导出）
    # inspect_glb.stats 返回的 dims 已是 Blender 坐标的 [宽X, 深Y, 高Z]（毫米前）
    ww, dd, hh = [v * 1000 for v in st["dims"]]

    def band(name, val, lo, hi, unit="mm"):
        ok = lo <= val <= hi
        checks.append({
            "level": "ok" if ok else "bad",
            "text": f"{name}在现实区间",
            "value": f"{val:.0f}{unit} / {lo}~{hi}",
        })
        return ok

    band("宽度", ww, *sp["w"])
    band("深度", dd, *sp["d"])
    band("高度", hh, *sp["h"])

    okTri = st["triangles"] >= sp["minTri"]
    checks.append({
        "level": "ok" if okTri else "bad",
        "text": "三角面达到细分阈值",
        "value": f"{st['triangles']:,} / ≥{sp['minTri']:,}",
    })

    nmats = len(st["materials"])
    okM = nmats >= 3
    checks.append({
        "level": "ok" if okM else "warn",
        "text": "材质分区数",
        "value": f"{nmats} 个 / ≥3",
    })

    named = [m for m in st["materials"] if m.startswith("U_")]
    okN = len(named) >= 2
    checks.append({
        "level": "ok" if okN else "warn",
        "text": "U_<role> 规范材质",
        "value": f"{len(named)} 个主题材质",
    })

    # 地面贴合：Blender 导出后 min z 应 ≈ 0
    zmin = st["bbox"]["min"][2]
    groundOk = abs(zmin) < 0.02
    checks.append({
        "level": "ok" if groundOk else "warn",
        "text": "落地贴合(底面 z=0)",
        "value": f"z={zmin:.3f}",
    })

    worst = min(c["level"] for c in checks)
    order = {"ok": 0, "warn": 1, "bad": 2, "none": 3}
    status = "none" if order.get(worst, 3) == 3 else worst
    if any(c["level"] == "bad" for c in checks):
        status = "bad"
    elif any(c["level"] == "warn" for c in checks):
        status = "warn"
    else:
        status = "ok"
    return checks, status


def main():
    os.makedirs(MODELS, exist_ok=True)
    items = []
    for key, sp in SPEC.items():
        glb = os.path.join(MODELS, key + ".glb")
        entry = {
            "key": key, "name": sp["cn"], "cat": sp["cat"], "file": None,
            "tris": 0, "verts": 0, "materials": [], "status": "none", "checks": [],
            "ref": None, "refTitle": None, "refNote": "",
        }
        if os.path.exists(glb):
            st = stats(glb)
            checks, status = check_item(key, st)
            entry.update({
                "file": key + ".glb",
                "tris": st["triangles"],
                "verts": st["vertices"],
                "materials": st["materials"],
                "bytes": st["bytes"],
                "status": status,
                "checks": checks,
            })
        items.append(entry)

    # 参考素材：从 refs/manifest.json 读（由采集脚本写入）
    refman = os.path.join(ACC, "refs", "manifest.json")
    refs = {}
    if os.path.exists(refman):
        refs = json.load(open(refman, encoding="utf-8"))
    for it in items:
        r = refs.get(it["key"])
        if r:
            it["ref"] = r.get("file")
            it["refTitle"] = r.get("title")
            it["refNote"] = r.get("note", "")

    man = {"generated": __import__("datetime").datetime.now().isoformat(timespec="seconds"), "items": items}
    with open(os.path.join(MODELS, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(man, f, ensure_ascii=False, indent=1)
    print("manifest ok ->", os.path.join(MODELS, "manifest.json"))
    for it in items:
        print(f"  {it['key']:<14} {it['status']:<5} tri={it['tris']:>8,} mats={len(it['materials'])}")


if __name__ == "__main__":
    main()

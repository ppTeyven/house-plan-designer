"""在 Blender 内跑穿模检测，把结果写进 manifest.json 的第 8 项自检。

【为什么单独一个脚本】
make_manifest.py 是普通 python 跑的（只解析 GLB 二进制），
而穿模检测需要 Blender 的网格/BVH 能力。
所以拆成两步：
  1. python make_manifest.py           → 尺寸/面数/材质/落地 等 7 项
  2. blender --background --python check_penetration_manifest.py  → 追加穿模项

用法：
  blender --background --python scripts/dev/blender/check_penetration_manifest.py
"""
import bpy
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
MODELS = os.path.join(ROOT, "验收", "models")
sys.path.insert(0, HERE)

from interpenetration import scan_objects  # noqa: E402

MAN = os.path.join(MODELS, "manifest.json")
if not os.path.exists(MAN):
    raise SystemExit("run make_manifest.py first")

man = json.load(open(MAN, encoding="utf-8"))
TOL = 0.002

for it in man["items"]:
    if not it.get("file"):
        continue
    glb = os.path.join(MODELS, it["file"])
    if not os.path.exists(glb):
        continue
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    bpy.ops.import_scene.gltf(filepath=glb)
    issues = scan_objects(list(bpy.context.scene.objects), tol=TOL)

    # 去掉旧的本项
    it["checks"] = [c for c in it["checks"] if c["text"] != "部件无互相穿模"]
    if issues:
        worst = max(issues, key=lambda x: x[2])
        it["checks"].append({
            "level": "bad",
            "text": "部件无互相穿模",
            "value": "%d 对互侵，最深 %.1fmm（%s↔%s）" % (
                len(issues), worst[3], worst[0], worst[1]),
        })
        it["status"] = "bad"
    else:
        it["checks"].append({
            "level": "ok",
            "text": "部件无互相穿模",
            "value": "0 处互侵",
        })
    print("  %-14s %s" % (it["key"], "✗ %d 对互侵" % len(issues) if issues else "✓ 无穿模"))

with open(MAN, "w", encoding="utf-8") as f:
    json.dump(man, f, ensure_ascii=False, indent=1)
print("penetration checks ->", MAN)

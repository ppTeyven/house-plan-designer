"""核对 assets/furnlib/sofa.glb 是否已经是 v22（含点缀抱枕配色）。

【为什么要查】
  sync_furnlib.py 会把 assets/furnlib/*.glb 重新导出（Y-up）到 assets/furnlib/。
  之前有个后台任务在 16:36 跑过一次 sync + 开 GUI，
  那个时间点 sofa.glb 还是 v20（w=2.257 h=0.823），
  所以它同步过去的、GUI 打开的都是旧模型。
  v22 建于 17:22，必须确认 furnlib 已同步到新版。

检查方法：查材质列表 —— v22 才会有 U_accent1 / U_accent2（陶土橙 / 灰绿抱枕）。
"""
import bpy
import os
import sys
import mathutils

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import glb_clean

args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
GLB = args[0]

bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
model = glb_clean.import_clean(GLB)
bpy.context.view_layer.update()

mats = sorted({m.name for o in model if o.type == 'MESH' and o.data.materials
                for m in o.data.materials})

mn = [1e9] * 3
mx = [-1e9] * 3
for o in model:
    if o.type != 'MESH':
        continue
    for c in o.bound_box:
        w = o.matrix_world @ mathutils.Vector(c)
        for i in range(3):
            mn[i] = min(mn[i], w[i])
            mx[i] = max(mx[i], w[i])

names = {o.name for o in model}
print("FILE: %s" % GLB)
print("SIZE: %.1f x %.1f x %.1f mm" % ((mx[0] - mn[0]) * 1000,
                                        (mx[2] - mn[2]) * 1000,
                                        (mx[1] - mn[1]) * 1000))
print("OBJECTS: %d" % len(model))
print("MATERIALS: %s" % ", ".join(mats))

has_acc = "U_accent1" in mats and "U_accent2" in mats
has_pil = any(n.startswith("pillow") for n in names)
print("HAS_ACCENT_MATS: %s" % ("YES  -> v22" if has_acc else "NO   -> 旧版"))
print("HAS_PILLOWS  : %s" % ("YES  -> v22" if has_pil else "NO   -> 旧版"))
print("VERDICT      : %s" % ("v22 ✓" if (has_acc and has_pil) else "旧版 ✗"))

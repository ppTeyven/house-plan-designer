"""验证 fix_inconsistent_normals 的效果 —— 修复前后硬棱对比。

用法：blender --background --python test_fix_normals.py -- <glb>
"""
import bpy
import sys
import os
import math
import bmesh

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bl_lib as B

args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
GLB = args[0]

bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
bpy.ops.import_scene.gltf(filepath=GLB)
bpy.context.view_layer.update()


def stats(ob):
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bm.normal_update()
    rev = 0
    for e in bm.edges:
        if len(e.link_faces) == 2:
            if e.link_faces[0].normal.dot(e.link_faces[1].normal) < -0.985:
                rev += 1
    bm.free()
    return rev


print("=" * 92)
print("%-26s %10s %10s" % ("对象", "修复前", "修复后"))
print("-" * 92)

before = {}
after = {}
objs = [o for o in bpy.context.scene.objects if o.type == 'MESH' and o.data.polygons]
for o in objs:
    before[o.name] = stats(o)

B.fix_all_normals(objs)

for o in objs:
    after[o.name] = stats(o)

names = sorted(before.keys(), key=lambda n: -before[n])
for n in names:
    if before[n] == 0 and after[n] == 0:
        continue
    mark = "  FIXED" if after[n] < before[n] else ""
    print("%-26s %10d %10d%s" % (n, before[n], after[n], mark))

tb = sum(before.values())
ta = sum(after.values())
print("-" * 92)
print("%-26s %10d %10d" % ("合计", tb, ta))
print()
if ta == 0:
    print("✅ 全部硬棱（法线反向）已清除")
elif ta < tb:
    print("⚠️  改善 %d 处，仍剩 %d 处" % (tb - ta, ta))
else:
    print("❌ 无改善")

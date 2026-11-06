"""射线体检 —— 从指定方向打射线，看第一个命中的面/法线，定位"镂空"根因。

【用途】
  沙发渲染出来中间镂空（能看到背景），说明从正面看过去，
  外壳靠背那层面被背面剔除掉了。
  但仅看包围盒/法线统计无法定位是哪一面出问题
  —— 外表面本来就该朝外，被剔除是"正确"的；
  真正该被看到的是【靠背朝向座位的那一面】。

  这里从 +Y（沙发正面）沿 -Y 打射线，打到 seat_deck 高度，
  报告每次命中的：物体名 / 命中点 / 法线 / 法线是否朝向射线来源。
"""
import bpy
import sys
import mathutils
from mathutils.bvhtree import BVHTree

args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
GLB = args[0] if args else r"assets/furnlib/sofa.glb"
Z = float(args[1]) if len(args) > 1 else 0.60
X0 = float(args[2]) if len(args) > 2 else -1.0
X1 = float(args[3]) if len(args) > 3 else 1.0
N = int(args[4]) if len(args) > 4 else 21

bpy.ops.import_scene.gltf(filepath=GLB)
bpy.context.view_layer.update()

# 只看主体大件（忽略针脚/滚边等细件，避免干扰）
SKIP = ('stitch', 'tuft', 'pipe', 'leg', 'cup')


def build_bvh(ob):
    dg = bpy.context.evaluated_depsgraph_get()
    me = ob.evaluated_get(dg).to_mesh()
    bm = __import__('bmesh').new()
    bm.from_mesh(me)
    tree = BVHTree.FromBMesh(bm)
    bm.free()
    ob.evaluated_get(dg).to_mesh_clear()
    return tree


trees = []
for o in bpy.context.scene.objects:
    if o.type != 'MESH':
        continue
    if any(s in o.name for s in SKIP):
        continue
    try:
        trees.append((o, build_bvh(o)))
    except Exception:
        pass

print("=== 射线体检: 沿 -Y 从 +Y 打入, z=%.2f, x %.2f..%.2f (%d 条) ==="
      % (Z, X0, X1, N))
print("  期望顺序: [外壳外表面(剔除)] -> [靠背内表面(可见)] -> ...")
for i in range(N):
    x = X0 + (X1 - X0) * i / (N - 1)
    org = mathutils.Vector((x, 2.0, Z))
    d = mathutils.Vector((0, -1, 0))
    hits = []
    for o, tree in trees:
        loc, nor, idx, dist = tree.ray_cast(org, d)
        if loc is not None:
            hits.append((dist, o.name, tuple(round(v, 3) for v in nor),
                         round(loc.y, 3)))
    hits.sort()
    if not hits:
        print("  x=%+.3f  <无命中>" % x)
        continue
    parts = []
    for dist, nm, nor, ly in hits[:3]:
        facing = "朝+Y" if nor[1] > 0 else ("朝-Y" if nor[1] < 0 else "侧向")
        parts.append("%s@%.3f %s" % (nm, ly, facing))
    print("  x=%+.3f  %s" % (x, "  |  ".join(parts)))

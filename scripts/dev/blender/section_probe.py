"""截面定量测量 —— 用射线测量各部位的实际截面，代替目视判断。

【为什么需要】
  沙发外壳的"扶手看不见 / 靠背成细条"这类问题，
  靠渲染图目视判断极易误读（阴影、视角、背景都可能骗人）。
  这里用【定量射线测量】：
    · 沿 +X 打射线 → 测左扶手在某个高度上的实际 x 跨度
    · 沿 +Y 打射线 → 测靠背在某个高度上的实际 y 跨度
    · 沿 -Y 打射线 → 测座深
  每个测量点报告：命中物体 / 命中坐标 / 法线朝向。
  有了数字，扶手到底"太窄/太短/不存在"就没有争议了。

用法：
  blender --background --python section_probe.py -- <glb>
"""
import bpy
import sys
import mathutils
from mathutils.bvhtree import BVHTree
import bmesh

args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
GLB = args[0] if args else r"assets/furnlib/sofa.glb"

bpy.ops.import_scene.gltf(filepath=GLB)
bpy.context.view_layer.update()

SKIP = ('stitch', 'tuft', 'pipe', 'leg', 'cup')


def build_bvh(ob):
    dg = bpy.context.evaluated_depsgraph_get()
    me = ob.evaluated_get(dg).to_mesh()
    bm = bmesh.new()
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


def shoot(org, d, max_hits=8):
    """沿方向连续打射线，返回【所有】命中（逐层穿透）。

    【重要】BVHTree.ray_cast 只返回【最近的一个】命中，
    被外表面遮住的内表面完全测不到 —— 会误判成"内表面不存在"
    （实测 v18：扶手内立面明明有几何，却测不出来）。
    这里每次命中后把起点推进到命中点前方一点点，继续打，
    才能拿到真正的截面层次。
    """
    hits = []
    p = org.copy()
    for _ in range(max_hits):
        best = None
        for o, tree in trees:
            loc, nor, idx, dist = tree.ray_cast(p, d)
            if loc is None:
                continue
            if best is None or dist < best[0]:
                best = (dist, o, nor, loc)
        if best is None:
            break
        dist, o, nor, loc = best
        hits.append((dist, o.name, tuple(nor), tuple(loc)))
        p = loc + d * 0.0008          # 推进到表面之后，继续穿透
    return hits


print("=== 截面测量 ===")
print()
print("[A] 沿 +X 打射线（从左外侧向中心），z=0.25 -> 左扶手截面")
for z in (0.22, 0.25, 0.30, 0.38):
    hits = shoot(mathutils.Vector((-2.0, 0.05, z)), mathutils.Vector((1, 0, 0)))
    desc = "  ".join("%s@x=%.3f(%s)" % (h[1], h[3][0],
                                        "朝+X" if h[2][0] > 0 else "朝-X")
                      for h in hits[:3])
    print("  z=%.2f  %s" % (z, desc or "<无命中>"))

print()
print("[B] 沿 +Y 打射线（从后方向前），x=0.0 -> 靠背截面")
for z in (0.25, 0.45, 0.60, 0.80):
    hits = shoot(mathutils.Vector((0.0, -2.0, z)), mathutils.Vector((0, 1, 0)))
    desc = "  ".join("%s@y=%.3f(%s)" % (h[1], h[3][1],
                                        "朝+Y" if h[2][1] > 0 else "朝-Y")
                      for h in hits[:3])
    print("  z=%.2f  %s" % (z, desc or "<无命中>"))

print()
print("[C] 沿 +Y 打射线，x=±1.0 -> 扶手纵向截面")
for x in (-1.0, 1.0):
    for z in (0.25, 0.45):
        hits = shoot(mathutils.Vector((x, -2.0, z)), mathutils.Vector((0, 1, 0)))
        desc = "  ".join("%s@y=%.3f" % (h[1], h[3][1]) for h in hits[:2])
        print("  x=%+.2f z=%.2f  %s" % (x, z, desc or "<无命中>"))

print()
print("[D] 沿 -Y 打射线（从正面向后），z=0.30 -> 座深")
for x in (-0.8, -0.3, 0.3, 0.8):
    hits = shoot(mathutils.Vector((x, 2.0, 0.30)), mathutils.Vector((0, -1, 0)))
    desc = "  ".join("%s@y=%.3f" % (h[1], h[3][1]) for h in hits[:2])
    print("  x=%+.2f  %s" % (x, desc or "<无命中>"))

print()
print("[E] 整体包围盒")
allpts = []
for o in bpy.context.scene.objects:
    if o.type != 'MESH':
        continue
    if any(s in o.name for s in SKIP):
        continue
    allpts += [o.matrix_world @ v.co for v in o.data.vertices]
if allpts:
    print("  x[%.3f,%.3f]  y[%.3f,%.3f]  z[%.3f,%.3f]"
          % (min(p.x for p in allpts), max(p.x for p in allpts),
             min(p.y for p in allpts), max(p.y for p in allpts),
             min(p.z for p in allpts), max(p.z for p in allpts)))
    print("  尺寸 W=%.3f D=%.3f H=%.3f"
          % (max(p.x for p in allpts) - min(p.x for p in allpts),
             max(p.y for p in allpts) - min(p.y for p in allpts),
             max(p.z for p in allpts) - min(p.z for p in allpts)))
